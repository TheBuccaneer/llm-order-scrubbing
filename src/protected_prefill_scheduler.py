"""Bounded two-tenant protected-prefill scheduler for installed vLLM 0.17.1.

This subclasses the real v1 scheduler. It changes which *running* and
waiting requests may execute, parks exactly at the first sampled token,
and transports canonical KV tables to the worker on the first shared step.
The in-process synchronous driver supplies the public windows and performs
the actual GPU copy/drain through ``normalizer``. No installed vLLM files
are patched. The prototype does not claim hardware timing noninterference.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from vllm.v1.core.sched.request_queue import SchedulingPolicy, create_request_queue
from vllm.v1.core.sched.scheduler import Scheduler


def tenant_of(request_id: str) -> str:
    if request_id.startswith("A:"):
        return "A"
    if request_id.startswith("B:"):
        return "B"
    raise ValueError(f"Request has no authenticated prototype tenant prefix: {request_id}")


class ProtectedPrefillError(RuntimeError):
    """The bounded phase contract failed; never join a ready subset."""


class ProtectedPrefillScheduler(Scheduler):
    """Default operation is native scheduling, allowing ordinary warmup."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._cohort: dict[str, Any] | None = None
        self.trace: list[dict[str, Any]] = []
        self._protected_trace: list[dict[str, Any]] = []
        self._inflight_ids: set[str] = set()
        self._step_deadline_ns: int | None = None
        self._phase = "native"
        self._joined = False
        self._normalizer_ran = False
        self._remap_first_shared = False
        self.join_snapshot: dict[str, Any] | None = None
        self.normalization_result: Any = None

    def configure_cohort(
        self,
        epoch_ns: int,
        windows_ms: Mapping[str, Sequence[float]],
        join_ms: float,
        request_ids: Sequence[str],
        normalizer: Callable[["ProtectedPrefillScheduler"], Any] | None = None,
        prefill_chunk_tokens: int = 64,
        fuse_final_normalization: bool = False,
    ) -> None:
        """Freeze a public cohort; call before its first engine step.

        Request IDs are exact core IDs in public canonical order. All must
        already be queued by the first schedule(). ``normalizer(self)`` runs
        once in the public normalization interval after the final tenant
        window and must copy/drain GPU work and commit the canonical manager
        tables before returning. Root must install TenantKVPartition before
        any warmup if partitioned cache capacity is required.
        """
        if self._cohort is not None or self._inflight_ids:
            raise ProtectedPrefillError("Previous cohort/step has not been drained")
        if self.scheduler_config.async_scheduling:
            raise ProtectedPrefillError("Prototype requires async_scheduling=False")
        if self.vllm_config.speculative_config is not None:
            raise ProtectedPrefillError("Speculative execution is unsupported")
        if getattr(self.vllm_config.model_config, "logits_processors", None):
            raise ProtectedPrefillError("Custom model logits processors are unsupported")
        if self.connector is not None or self.ec_connector is not None or self.use_pp:
            raise ProtectedPrefillError("External transfers and pipeline parallelism are unsupported")
        if self.policy != SchedulingPolicy.FCFS:
            raise ProtectedPrefillError("Prototype requires FCFS and explicit public order")
        if self.scheduler_config.long_prefill_token_threshold not in (64, prefill_chunk_tokens):
            raise ProtectedPrefillError("Public scheduler chunk limit must match a supported cached-prefix recipe")
        if prefill_chunk_tokens not in (64, 512):
            raise ValueError("Only the original 64-token and structural 512-token recipes are supported")
        if self.scheduler_config.max_num_batched_tokens < 4*prefill_chunk_tokens:
            raise ValueError("Worker input buffers must fit all four tenant-B chunks")
        if not callable(normalizer):
            raise ProtectedPrefillError("Protected join requires the real GPU/metadata normalizer")
        if not callable(getattr(self.kv_cache_manager, "set_protected_alignment", None)):
            raise ProtectedPrefillError("Protected join requires the fixed tenant KV facade")
        ids = list(request_ids)
        if not ids or len(ids) != len(set(ids)) or len(ids) > self.max_num_running_reqs:
            raise ValueError("Cohort IDs must be unique and fit max_num_seqs")
        if self.max_num_scheduled_tokens < len(ids):
            raise ValueError("Token budget must fit one shared decode token per request")
        owners = {tenant_of(rid) for rid in ids}
        if (owners != {"A", "B"} or set(windows_ms) != owners
            or sum(tenant_of(rid)=="A" for rid in ids) != 1
            or sum(tenant_of(rid)=="B" for rid in ids) != 4):
            raise ValueError("Prototype requires exactly one A request and four B requests")
        windows = sorted((float(v[0]), float(v[1]), owner)
                         for owner, v in windows_ms.items())
        previous_end = 0.0
        for start, end, _ in windows:
            if start < previous_end or end <= start:
                raise ValueError("Tenant windows must be public, ordered, non-overlapping")
            previous_end = end
        if join_ms < previous_end or (join_ms == previous_end and not fuse_final_normalization):
            raise ValueError("A positive normalization/drain interval is required before join")
        self._cohort = dict(epoch_ns=int(epoch_ns), windows=windows,
                            join_ms=float(join_ms), ids=ids,
                            order={rid: i for i, rid in enumerate(ids)},
                            prefill_chunk_tokens=prefill_chunk_tokens,
                            fuse_final_normalization=fuse_final_normalization,
                            normalizer=normalizer, validated=False)
        self.trace = []
        self._protected_trace = []
        self.kv_cache_manager.set_protected_alignment(64)
        self._joined = self._normalizer_ran = self._remap_first_shared = False
        self.join_snapshot = None
        self.normalization_result = None
        self._phase = "intake"
        self._record("configure", windows_ms=windows, join_ms=join_ms, request_ids=ids,
                     prefill_chunk_tokens=prefill_chunk_tokens)

    begin_cohort = configure_cohort

    def _record(self, event: str, **fields: Any) -> None:
        assert self._cohort is not None
        self.trace.append(dict(event=event,
                               elapsed_ms=(time.perf_counter_ns()-self._cohort["epoch_ns"])/1e6,
                               **fields))

    def _fail(self, message: str) -> None:
        self._record("contract_failure", message=message)
        raise ProtectedPrefillError(message)

    def _frontier(self, request: Any) -> bool:
        return (request.num_computed_tokens == request.num_prompt_tokens
                and request.num_output_tokens == 1
                and request.num_output_placeholders == 0
                and not request.spec_token_ids)

    def _require_frontier(self, owner: str | None = None) -> None:
        assert self._cohort is not None
        for rid in self._cohort["ids"]:
            if owner is not None and tenant_of(rid) != owner:
                continue
            request = self.requests.get(rid)
            if request is None or not self._frontier(request):
                self._fail(f"{rid}: public phase deadline reached without exact first-token frontier")
            if request.num_preemptions:
                self._fail(f"{rid}: preemption violates reserved-cohort contract")

    def state_snapshot(self) -> dict[str, Any]:
        assert self._cohort is not None
        states = []
        for rid in self._cohort["ids"]:
            r = self.requests.get(rid)
            if r is None:
                states.append(dict(request_id=rid, finished_or_absent=True))
                continue
            states.append(dict(request_id=rid, tenant=tenant_of(rid),
                               prompt_tokens=r.num_prompt_tokens,
                               computed_tokens=r.num_computed_tokens,
                               total_logical_tokens=r.num_tokens,
                               output_tokens=r.num_output_tokens,
                               first_output_token_ids=list(r.output_token_ids),
                               cached_tokens=r.num_cached_tokens,
                               output_placeholders=r.num_output_placeholders,
                               is_prefill_chunk=r.is_prefill_chunk,
                               external_computed_tokens=r.num_external_computed_tokens,
                               speculative_tokens=list(r.spec_token_ids),
                               preemptions=r.num_preemptions,
                               status=str(r.status),
                               block_ids=self.kv_cache_manager.get_block_ids(rid)))
        return dict(requests=states, running=[r.request_id for r in self.running],
                    waiting=[r.request_id for r in self.waiting],
                    inflight=sorted(self._inflight_ids),
                    scheduled_token_budget=self.max_num_scheduled_tokens,
                    prefill_chunk_threshold=self.scheduler_config.long_prefill_token_threshold,
                    prev_step=sorted(self.prev_step_scheduled_req_ids))

    def _sleep_until(self, deadline_ns: int) -> None:
        remaining = deadline_ns-time.perf_counter_ns()
        if remaining > 0:
            time.sleep(remaining/1e9)

    def _select_phase(self) -> tuple[str, str | None, int | None]:
        """Return phase/owner/kernel deadline, waiting only on public times."""
        c = self._cohort
        assert c is not None
        if self._inflight_ids:
            self._fail("schedule() called before previous GPU output was drained")
        while True:
            now = time.perf_counter_ns()
            elapsed = (now-c["epoch_ns"])/1e6
            for start, end, owner in c["windows"]:
                if elapsed >= end:
                    self._require_frontier(owner)
            for index, (start, end, owner) in enumerate(c["windows"]):
                if elapsed < start:
                    self._sleep_until(c["epoch_ns"]+int(start*1e6))
                    break
                if elapsed < end:
                    pending = [self.requests[rid] for rid in c["ids"]
                               if tenant_of(rid) == owner and not self._frontier(self.requests[rid])]
                    if pending:
                        return "prefill", owner, c["epoch_ns"]+int(end*1e6)
                    if c["fuse_final_normalization"] and index == len(c["windows"])-1:
                        # Both operations remain isolated until the SAME public J.
                        # Normalization may start when the final tenant is ready;
                        # its completion never advances the shared release time.
                        continue
                    # A warm hit cannot lend its saved window to another tenant.
                    self._sleep_until(c["epoch_ns"]+int(end*1e6))
                    break
            else:
                if not self._normalizer_ran:
                    self._require_frontier()
                    self._record("normalization_begin", state=self.state_snapshot())
                    normalizer = c["normalizer"]
                    if normalizer is not None:
                        self.normalization_result = normalizer(self)
                    self._normalizer_ran = True
                    self._require_frontier()
                    self._record("normalization_end", applied=normalizer is not None,
                                 state=self.state_snapshot())
                    if time.perf_counter_ns() > c["epoch_ns"]+int(c["join_ms"]*1e6):
                        self._fail("Normalization/drain exceeded the public join time")
                self._sleep_until(c["epoch_ns"]+int(c["join_ms"]*1e6))
                self._require_frontier()
                self.running.sort(key=lambda r:c["order"][r.request_id])
                if self.waiting or len(self.running) != len(c["ids"]):
                    self._fail("Join requires the entire running cohort and no waiting requests")
                self.prev_step_scheduled_req_ids.clear()
                self._joined = True
                self._remap_first_shared = c["normalizer"] is not None
                # Private prefill step counts must not change list growth on
                # the shared execution path. Retain them only for post-run QA.
                self._protected_trace = self.trace
                self.trace = []
                self.join_snapshot = self.state_snapshot()
                self._record("join", state=self.join_snapshot,
                             join_lateness_ms=(time.perf_counter_ns()-c["epoch_ns"])/1e6-c["join_ms"])
                return "shared_decode", None, None

    def schedule(self):
        if self._cohort is None:
            return super().schedule()
        c = self._cohort
        if self._inflight_ids:
            self._fail("schedule() called before previous GPU output was drained")
        expected = set(c["ids"])
        if not self._joined and not expected <= self.requests.keys():
            self._fail("All public cohort IDs must be submitted before the first protected step")
        extra = set(self.requests)-expected
        if extra:
            self._fail(f"Requests outside the closed cohort are forbidden: {sorted(extra)}")
        if not c["validated"]:
            budgets = set()
            for rid in c["ids"]:
                request = self.requests[rid]
                p = request.sampling_params
                if (p is None or p.max_tokens is None or not 2 <= p.max_tokens <= 16
                    or p.min_tokens != p.max_tokens or not p.ignore_eos
                    or p.temperature != 0 or p.stop or p.stop_token_ids
                    or request.use_structured_output
                    or request.mm_features or request.lora_request is not None):
                    self._fail(f"{rid}: protected cohort requires fixed 2..16-token greedy text output without stop/LoRA/MM/grammar")
                budgets.add(p.max_tokens)
            if len(budgets) != 1:
                self._fail("Protected cohort must have one identical public output-token budget")
            c["validated"] = True
        if self._joined:
            phase, owner, deadline = "shared_decode", None, None
        else:
            phase, owner, deadline = self._select_phase()
        self._phase = phase
        order = c["order"]
        if phase == "prefill":
            eligible = lambda r: tenant_of(r.request_id) == owner and not self._frontier(r)
            held_running = [r for r in self.running if not eligible(r)]
            held_waiting = [r for r in self.waiting if not eligible(r)]
            self.running = [r for r in self.running if eligible(r)]
            native_waiting = create_request_queue(self.policy)
            for request in self.waiting:
                if eligible(request):
                    native_waiting.add_request(request)
            self.waiting = native_waiting
        else:
            held_running, held_waiting = [], []
        previous_budget = self.max_num_scheduled_tokens
        previous_chunk = self.scheduler_config.long_prefill_token_threshold
        if phase == "prefill":
            # Fixed by the public policy, never by hit count or readiness.
            self.max_num_scheduled_tokens = 4*c["prefill_chunk_tokens"]
            self.scheduler_config.long_prefill_token_threshold = c["prefill_chunk_tokens"]
        try:
            output = super().schedule()
        finally:
            self.max_num_scheduled_tokens = previous_budget
            self.scheduler_config.long_prefill_token_threshold = previous_chunk
            self.running.extend(held_running)
            self.running.sort(key=lambda r:order[r.request_id])
            restored = list(self.waiting)+held_waiting
            self.waiting = create_request_queue(self.policy)
            for request in sorted(restored,key=lambda r:order[r.request_id]):
                self.waiting.add_request(request)
        if output.preempted_req_ids:
            self._fail(f"Reserved cohort was preempted: {sorted(output.preempted_req_ids)}")
        ids = set(output.num_scheduled_tokens)
        if phase == "prefill" and any(tenant_of(rid) != owner for rid in ids):
            self._fail("Foreign tenant escaped protected prefill gate")
        if not ids and self.requests:
            self._fail("Eligible cohort made no progress; inspect quota or unsupported request state")
        if self._remap_first_shared:
            if ids != expected:
                self._fail("First shared decode must schedule the complete canonical cohort")
            data = output.scheduled_cached_reqs
            for i,rid in enumerate(data.req_ids):
                data.resumed_req_ids.add(rid)
                data.new_block_ids[i] = self.kv_cache_manager.get_block_ids(rid)
                data.all_token_ids[rid] = self.requests[rid].all_token_ids.copy()
            if set(data.req_ids) != expected or output.scheduled_new_reqs:
                self._fail("Canonical table transport requires existing worker request states")
            self._remap_first_shared = False
        self._inflight_ids = ids
        self._step_deadline_ns = deadline
        self._record("schedule", phase=phase, owner=owner,
                     scheduled_tokens=dict(output.num_scheduled_tokens),
                     remapped_ids=sorted(output.scheduled_cached_reqs.resumed_req_ids),
                     running=[r.request_id for r in self.running])
        return output

    def update_from_output(self, scheduler_output, model_runner_output):
        result = super().update_from_output(scheduler_output, model_runner_output)
        if self._cohort is None:
            return result
        completed_ids = sorted(self._inflight_ids)
        self._inflight_ids.clear()
        self._record("gpu_output_drained", phase=self._phase, request_ids=completed_ids)
        if self._step_deadline_ns is not None and time.perf_counter_ns() > self._step_deadline_ns:
            self._fail("GPU step finished after its public protected-window boundary")
        if not self._joined:
            for rid in completed_ids:
                r = self.requests.get(rid)
                if r is None or r.num_output_tokens > 1:
                    self._fail(f"{rid}: protected request finished or advanced beyond first token")
        return result

    def end_cohort(self) -> dict[str, Any]:
        if self._cohort is None:
            raise ProtectedPrefillError("No active cohort")
        if self._inflight_ids or self.requests:
            self._fail("Cannot end cohort with unfinished or in-flight requests")
        result = dict(joined=self._joined, physical_normalizer_applied=self._cohort["normalizer"] is not None,
                      join_snapshot=self.join_snapshot,
                      normalization_result=self.normalization_result,
                      trace=self._protected_trace+self.trace)
        self.kv_cache_manager.set_protected_alignment(0)
        self._cohort = None
        self._phase = "native"
        return result
