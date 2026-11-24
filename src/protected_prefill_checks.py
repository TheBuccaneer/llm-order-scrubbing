"""Targeted CPU checks against real vLLM KV managers; no GPU/model execution.

Synthetic request metadata exercises allocation/caching, not tensor contents.
Run with the existing vLLM Python environment from the repository root.
"""

import json
from types import SimpleNamespace

import torch

from tenant_kv_partition import TenantKVPartition
from vllm.v1.core.kv_cache_manager import KVCacheManager
from vllm.v1.kv_cache_interface import (
    FullAttentionSpec, KVCacheConfig, KVCacheGroupSpec,
)


def request(rid, hash_prefix, tokens=548, max_tokens=16):
    return SimpleNamespace(
        request_id=rid, num_tokens=tokens, num_prompt_tokens=tokens,
        num_computed_tokens=0, num_preemptions=0, output_token_ids=[],
        skip_reading_prefix_cache=False,
        sampling_params=SimpleNamespace(max_tokens=max_tokens),
        block_hashes=[f"{hash_prefix}:{i}".encode() for i in range(tokens//16)],
    )


def check_world(warm, alignment=0):
    spec = FullAttentionSpec(block_size=16, num_kv_heads=4,
                             head_size=128, dtype=torch.float16)
    config = KVCacheConfig(num_blocks=600, kv_cache_tensors=[],
        kv_cache_groups=[KVCacheGroupSpec(layer_names=["test"], kv_cache_spec=spec)])
    template = KVCacheManager(config, 2048, 16, log_stats=True)
    kv = TenantKVPartition(template, lambda rid: rid.split(":")[0])
    prep = request("A:prep", "a" if warm else "d", max_tokens=1)
    assert kv.allocate_slots(prep, 548) is not None
    kv.free(prep)
    kv.set_protected_alignment(alignment)
    requests = {"A:target": request("A:target", "a")}
    requests.update({f"B:{i}": request(f"B:{i}", f"b{i}") for i in range(4)})
    hits = {}
    for rid, req in requests.items():
        before_refs = kv.snapshot()["tenants"][rid.split(":")[0]]["references"]
        cached, hits[rid] = kv.get_computed_blocks(req)
        assert kv.snapshot()["tenants"][rid.split(":")[0]]["references"] == before_refs
        assert kv.allocate_slots(req, 548-hits[rid], hits[rid], cached) is not None
        req.num_computed_tokens, req.num_tokens, req.output_token_ids = 548, 549, [42]
    assert kv.managers["A"].prefix_cache_stats.hits == hits["A:target"]
    before_b = kv.snapshot()["tenants"]["B"]
    assert kv.allocate_slots(request("A:overflow", "x", 2048), 2048) is None
    assert kv.snapshot()["tenants"]["B"] == before_b
    plan = kv.plan_canonical(requests, list(requests))
    canonical = kv.commit_canonical(plan, requests)
    assert len(plan["copy_pairs"]) == 175
    assert len(plan["clear_block_ids"]) == 384
    assert all(len(table[0]) == 36 for table in plan["block_tables"].values())
    for req in requests.values():
        old_ids = kv.get_block_ids(req.request_id)
        assert kv.allocate_slots(req, 1) is not None
        assert kv.get_block_ids(req.request_id) == old_ids
    for req in requests.values():
        kv.free(req)
    kv.reset_all()
    assert kv.snapshot()["tenants"]["A"]["free_blocks"] == 128
    assert kv.snapshot()["tenants"]["B"]["free_blocks"] == 256
    assert kv.protected_alignment_tokens == 0
    return hits, plan, canonical


def main():
    warm, warm_plan, warm_state = check_world(True)
    cold, cold_plan, cold_state = check_world(False)
    assert warm["A:target"] == 544 and cold["A:target"] == 0
    assert all(warm[f"B:{i}"] == cold[f"B:{i}"] == 0 for i in range(4))
    assert warm_state == cold_state
    assert (warm_plan["requests"]["A:target"]["source_block_ids"] !=
            cold_plan["requests"]["A:target"]["source_block_ids"])
    aligned_warm, _, aligned_warm_state = check_world(True, 64)
    aligned_cold, _, aligned_cold_state = check_world(False, 64)
    assert aligned_warm["A:target"] == 512 and aligned_cold["A:target"] == 0
    assert aligned_warm_state == aligned_cold_state
    assert all(aligned_warm[f"B:{i}"] == aligned_cold[f"B:{i}"] == 0 for i in range(4))
    print(json.dumps(dict(
        real_vllm_metadata_checks=True, GPU_execution=False,
        warm_hits=warm, cold_hits=cold, canonical_metadata_equal=True,
        protected_aligned_warm_hits=aligned_warm,
        protected_aligned_cold_hits=aligned_cold,
        protected_aligned_canonical_metadata_equal=True,
        cache_lookup_refcounts_preserved=True,
        prefix_hit_statistics_match_reuse=True,
        quota_overflow_denied=True, B_metadata_independent_of_A_overflow=True,
        canonical_copy_blocks=175, fixed_pool_blocks=384,
        free_after_join={t: s["free_blocks"] for t, s in warm_state["tenants"].items()},
        decode_keeps_reserved_tables=True, reset_verified=True,
    ), indent=2))


if __name__ == "__main__":
    main()
