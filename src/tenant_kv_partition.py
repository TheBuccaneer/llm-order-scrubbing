"""Fixed physical KV pools and canonical join for the two-tenant prototype.

This is deliberately limited to one full-attention cache group, one GPU,
no KV connector, no speculative decoding and no CPU offload. Actual GPU
copies are performed by the synchronous engine driver before commit_canonical.
The installed vLLM package is never modified.
"""

import hashlib
from dataclasses import fields, replace
from math import ceil

from vllm.v1.core.kv_cache_manager import KVCacheManager
from vllm.v1.kv_cache_interface import FullAttentionSpec
from vllm.v1.metrics.stats import PrefixCacheStats


class TenantKVPartition:
    """Scheduler-compatible router into genuinely independent KV managers.

    Each real vLLM manager enforces its own quota before allocating slots.
    Its physical block IDs are shifted into a disjoint, fixed region of the
    engine's existing GPU cache. Null block 0 is the sole shared metadata ID.
    """

    def __init__(self, template, tenant_of, quotas=None):
        self.tenant_of = tenant_of
        self.quotas = dict(quotas or {"A": 128, "B": 256})
        if set(self.quotas) != {"A", "B"} or min(self.quotas.values()) <= 0:
            raise ValueError("The prototype requires positive A and B quotas")
        config = template.kv_cache_config
        if (len(config.kv_cache_groups) != 1
                or type(config.kv_cache_groups[0].kv_cache_spec) is not FullAttentionSpec):
            raise ValueError("Only one ordinary FullAttentionSpec group is supported")
        if config.num_blocks < 1 + sum(self.quotas.values()):
            raise ValueError("GPU backing cache is smaller than fixed tenant quotas")
        if template.use_eagle:
            raise ValueError("Speculative/EAGLE allocation is outside this prototype")
        self.kv_cache_config = config
        self.max_model_len = template.max_model_len
        self.enable_caching = template.enable_caching
        self.log_stats = template.log_stats
        self.num_kv_cache_groups = 1
        self.block_size = config.kv_cache_groups[0].kv_cache_spec.block_size
        self.hash_block_size = template.block_pool.hash_block_size
        self.starts = {"A": 1, "B": 1 + self.quotas["A"]}
        self.managers = {tenant: self._new_manager(tenant) for tenant in ("A", "B")}
        self.empty_kv_cache_blocks = self.managers["A"].empty_kv_cache_blocks
        self.canonical_generation = 0
        self.protected_alignment_tokens = 0

    def _new_manager(self, tenant):
        manager = KVCacheManager(
            kv_cache_config=replace(self.kv_cache_config, num_blocks=self.quotas[tenant]+1),
            max_model_len=self.max_model_len,
            hash_block_size=self.hash_block_size,
            enable_caching=self.enable_caching,
            use_eagle=False,
            log_stats=self.log_stats,
            enable_kv_cache_events=False,
        )
        # Every linked-list/cache reference points to these same block objects.
        # IDs are consumed as physical GPU indexes only after this initialization.
        shift = self.starts[tenant] - 1
        for block in manager.block_pool.blocks[1:]:
            block.block_id += shift
        return manager

    def _manager(self, request_or_id):
        rid = (request_or_id if isinstance(request_or_id, str)
               else request_or_id.request_id)
        tenant = self.tenant_of(rid)
        if tenant not in self.managers:
            raise ValueError(f"Unregistered tenant for request {rid!r}")
        return self.managers[tenant]

    def get_computed_blocks(self, request):
        manager = self._manager(request)
        cached, hits = manager.get_computed_blocks(request)
        alignment = self.protected_alignment_tokens
        if not alignment or self.tenant_of(request.request_id) != "A":
            return cached, hits
        aligned_hits = hits // alignment * alignment
        if aligned_hits == hits:
            return cached, hits
        # Lookup has not touched/ref-counted the returned blocks yet. Dropping
        # suffix blocks here leaves them in A's own eviction queue; allocation
        # will touch only retained blocks and recompute the identical public
        # final prefill chunk used by a cold request (548 => final36, not4).
        keep = aligned_hits // self.block_size
        clipped = manager.create_kv_cache_blocks(tuple(group[:keep] for group in cached.blocks))
        if manager.prefix_cache_stats is not None:
            field = "preempted_hits" if request.num_preemptions else "hits"
            stats = manager.prefix_cache_stats
            setattr(stats, field, getattr(stats, field) - (hits-aligned_hits))
        return clipped, aligned_hits

    def set_protected_alignment(self, tokens):
        """Public A-only cache-frontier alignment; zero restores native hits.

        The scheduler enables this only for protected cohorts. Aligning to
        the fixed prefill chunk size makes the final prefill kernel shape
        independent of whether the private prefix was warm.
        """
        if not isinstance(tokens, int) or tokens < 0 or tokens % self.block_size:
            raise ValueError("Alignment must be zero or a positive multiple of block_size")
        self.protected_alignment_tokens = tokens

    def allocate_slots(self, request, *args, **kwargs):
        return self._manager(request).allocate_slots(request, *args, **kwargs)

    def free(self, request):
        return self._manager(request).free(request)

    def get_blocks(self, request_id):
        return self._manager(request_id).get_blocks(request_id)

    def get_block_ids(self, request_id):
        return self._manager(request_id).get_block_ids(request_id)

    def cache_blocks(self, request, num_computed_tokens):
        return self._manager(request).cache_blocks(request, num_computed_tokens)

    def remove_skipped_blocks(self, request_id, total_computed_tokens):
        return self._manager(request_id).remove_skipped_blocks(request_id, total_computed_tokens)

    def get_num_common_prefix_blocks(self, running_request_id):
        # A manager-local common-prefix count is not a cohort-wide count.
        # Disable this optional cross-request attention optimization explicitly.
        return [0]

    def new_step_starts(self):
        for manager in self.managers.values():
            manager.new_step_starts()

    def take_new_block_ids(self):
        return [bid for manager in self.managers.values()
                for bid in manager.take_new_block_ids()]

    def take_events(self):
        return []

    def evict_blocks(self, block_ids):
        # Original BlockPool.evict_blocks indexes its local list by block_id;
        # translate explicitly because B uses shifted physical IDs.
        for bid in block_ids:
            for tenant, start in self.starts.items():
                if start <= bid < start + self.quotas[tenant]:
                    pool = self.managers[tenant].block_pool
                    pool._maybe_evict_cached_block(pool.blocks[bid-start+1])
                    break
            else:
                raise ValueError(f"Physical block {bid} is outside fixed tenant pools")

    def reset_prefix_cache(self):
        if any(block.ref_cnt for manager in self.managers.values()
               for block in manager.block_pool.blocks[1:]):
            return False
        return all(manager.reset_prefix_cache() for manager in self.managers.values())

    def reset_all(self):
        """Restore canonical empty metadata between cases, after all requests end.

        The driver separately zeroes clear_block_ids on the GPU; clearing
        metadata alone is not presented as clearing KV bytes.
        """
        if any(block.ref_cnt for manager in self.managers.values()
               for block in manager.block_pool.blocks[1:]):
            raise ValueError("Cannot reset tenant pools while requests are active")
        self.managers = {tenant: self._new_manager(tenant) for tenant in ("A", "B")}
        self.empty_kv_cache_blocks = self.managers["A"].empty_kv_cache_blocks
        self.canonical_generation += 1
        self.protected_alignment_tokens = 0
        return {"clear_block_ids": self.all_physical_block_ids(),
                "snapshot": self.snapshot()}

    reset = reset_all

    def all_physical_block_ids(self):
        return [bid for tenant, start in self.starts.items()
                for bid in range(start, start+self.quotas[tenant])]

    def make_prefix_cache_stats(self):
        if not self.log_stats:
            return None
        combined = PrefixCacheStats()
        for manager in self.managers.values():
            stats = manager.make_prefix_cache_stats()
            for field in fields(combined):
                value = getattr(stats, field.name)
                if isinstance(value, bool):
                    setattr(combined, field.name, getattr(combined, field.name) or value)
                else:
                    setattr(combined, field.name, getattr(combined, field.name) + value)
        return combined

    @property
    def usage(self):
        used = sum(self.quotas[t] - m.block_pool.get_num_free_blocks()
                   for t, m in self.managers.items())
        return used / sum(self.quotas.values())

    def plan_canonical(self, requests, ordered_request_ids):
        """Plan a real KV copy and complete metadata reconstruction.

        Every admitted request gets a fixed physical range large enough for
        its entire public max_tokens budget, independent of cache hits. Old
        inactive prefix history is discarded at this boundary. The driver
        must clone all sources before zeroing/scattering any destination.
        """
        if len(set(ordered_request_ids)) != len(ordered_request_ids):
            raise ValueError("Duplicate request IDs at canonical join")
        active_ids = {rid for manager in self.managers.values()
                      for single in manager.coordinator.single_type_managers
                      for rid, blocks in single.req_to_blocks.items() if blocks}
        if active_ids != set(ordered_request_ids):
            raise ValueError(f"Join active-set mismatch: {active_ids} != {set(ordered_request_ids)}")
        next_id = dict(self.starts)
        plan = dict(copy_pairs=[], clear_block_ids=[], block_tables={}, requests={},
                    block_size=self.block_size,
                    previous_generation=self.canonical_generation)
        for tenant, start in self.starts.items():
            plan["clear_block_ids"].extend(range(start, start+self.quotas[tenant]))
        for rid in ordered_request_ids:
            request = requests[rid]
            if request.num_computed_tokens != request.num_prompt_tokens or len(request.output_token_ids) != 1:
                raise ValueError(f"Request {rid} is not at the full-prompt/one-output frontier")
            max_tokens = request.sampling_params.max_tokens
            if max_tokens is None or max_tokens < 1:
                raise ValueError("Join requires an explicit positive public max_tokens")
            capacity = ceil((request.num_prompt_tokens + max_tokens) / self.block_size)
            tenant = self.tenant_of(rid)
            first = next_id[tenant]
            last = first + capacity
            if last > self.starts[tenant] + self.quotas[tenant]:
                raise ValueError(f"Public cohort exceeds {tenant}'s reserved KV capacity")
            old_ids = self.get_block_ids(rid)[0]
            if len(old_ids) > capacity:
                raise ValueError("Speculative/lookahead allocation is outside the join contract")
            new_ids = list(range(first, last))
            plan["block_tables"][rid] = [new_ids]
            plan["copy_pairs"].extend([src, dst] for src, dst in zip(old_ids, new_ids))
            plan["requests"][rid] = dict(tenant=tenant,
                num_computed_tokens=request.num_computed_tokens,
                num_prompt_tokens=request.num_prompt_tokens,
                num_output_tokens=len(request.output_token_ids),
                capacity_blocks=capacity, source_block_ids=list(old_ids))
            next_id[tenant] = last
        return plan

    def commit_canonical(self, plan, requests):
        """Commit metadata only AFTER the driver has completed GPU copies.

        Worker persistent request tables must be replaced by plan.block_tables
        on its first shared-decode step (resumed request/full-table path).
        """
        if plan["previous_generation"] != self.canonical_generation:
            raise ValueError("Stale canonical plan")
        rebuilt = {tenant: self._new_manager(tenant) for tenant in ("A", "B")}
        for rid, shape in plan["requests"].items():
            request = requests[rid]
            if request.num_computed_tokens != shape["num_computed_tokens"] or len(request.output_token_ids) != 1:
                raise ValueError("Request progressed while canonical GPU copy was in flight")
            tenant = shape["tenant"]
            manager = rebuilt[tenant]
            pool = manager.block_pool
            physical_to_block = {block.block_id: block for block in pool.blocks[1:]}
            blocks = [physical_to_block[bid] for bid in plan["block_tables"][rid][0]]
            pool.touch(blocks)
            single = manager.coordinator.single_type_managers[0]
            single.req_to_blocks[rid] = blocks
            single.num_cached_block[rid] = 0
            manager.cache_blocks(request, request.num_computed_tokens)
            # Do not mark these as newly allocated: the driver already copied
            # valid KV bytes, and a later zero-new-blocks path must not erase them.
            single.new_block_ids.clear()
        self.managers = rebuilt
        self.empty_kv_cache_blocks = rebuilt["A"].empty_kv_cache_blocks
        self.canonical_generation += 1
        return self.snapshot()

    def snapshot(self):
        result = {"canonical_generation": self.canonical_generation,
                  "protected_alignment_tokens": self.protected_alignment_tokens,
                  "tenants": {}}
        for tenant, manager in self.managers.items():
            pool = manager.block_pool
            single = manager.coordinator.single_type_managers[0]
            blocks = pool.blocks[1:]
            hash_state = hashlib.sha256()
            for block in blocks:
                if block.block_hash is not None:
                    hash_state.update(block.block_id.to_bytes(8, "big"))
                    hash_state.update(bytes(block.block_hash))
            result["tenants"][tenant] = dict(
                quota_blocks=self.quotas[tenant],
                physical_start=self.starts[tenant],
                physical_end=self.starts[tenant]+self.quotas[tenant]-1,
                free_blocks=pool.get_num_free_blocks(),
                referenced_blocks=sum(b.ref_cnt > 0 for b in blocks),
                cached_blocks=sum(b.block_hash is not None for b in blocks),
                cache_hash_entries=len(pool.cached_block_hash_to_block),
                physical_block_hash_digest=hash_state.hexdigest(),
                request_blocks={rid: [b.block_id for b in active]
                                for rid, active in single.req_to_blocks.items() if active},
                request_cached_blocks=dict(single.num_cached_block),
                references={str(b.block_id): b.ref_cnt for b in blocks if b.ref_cnt},
                free_queue_ids=self._free_ids(pool))
        return result

    @staticmethod
    def _free_ids(pool):
        queue = pool.free_block_queue
        result = []
        block = queue.fake_free_list_head.next_free_block
        while block is not queue.fake_free_list_tail:
            result.append(block.block_id)
            block = block.next_free_block
        return result
