"""Executable single-GPU protected-prefill prototype and bounded comparison.

Run with the existing vLLM Python, HF_HUB_OFFLINE=1 and
VLLM_ENABLE_V1_MULTIPROCESSING=0. Uses the real synchronous EngineCore;
timings are from this in-process serving harness, not HTTP measurements.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
from vllm import LLM, SamplingParams
from vllm.sampling_params import RequestOutputKind

from tenant_kv_partition import TenantKVPartition
from protected_prefill_scheduler import tenant_of

ROOT = Path(__file__).resolve().parents[1]
MODEL = "/home/rock/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28"


def gpu_canonical_copy(worker, plan):
    """Snapshot -> clear private pools -> canonical scatter -> device drain.

    Only supports the checked FlashAttention 5-D layout. Copies are real
    GPU tensor operations; request tables are committed by the caller.
    """
    runner = worker.model_runner
    torch.cuda.synchronize()
    copy_start=torch.cuda.Event(enable_timing=True)
    copy_end=torch.cuda.Event(enable_timing=True)
    copy_start.record()
    pairs = plan["copy_pairs"]
    source = torch.tensor([p[0] for p in pairs], device="cuda", dtype=torch.long)
    target = torch.tensor([p[1] for p in pairs], device="cuda", dtype=torch.long)
    clear = torch.tensor(plan["clear_block_ids"], device="cuda", dtype=torch.long)
    shapes = []
    seen = set()
    # Snapshot all sources before any writes: canonical ranges can overlap them.
    saved = []
    for tensor in runner.kv_caches:
        if tensor.data_ptr() in seen:
            continue
        seen.add(tensor.data_ptr())
        if tensor.ndim != 5 or tensor.shape[0] != 2 or tensor.shape[2] != plan["block_size"]:
            raise RuntimeError(f"Unsupported KV layout {tuple(tensor.shape)}; expected FlashAttention")
        shapes.append(list(tensor.shape))
        saved.append((tensor, tensor.index_select(1, source)))
    for tensor, snapshot in saved:
        tensor.index_fill_(1, clear, 0)
        tensor.index_copy_(1, target, snapshot)
        for rid, info in plan["requests"].items():
            valid = info["num_computed_tokens"] % plan["block_size"]
            if valid:
                last = plan["block_tables"][rid][0][info["num_computed_tokens"] // plan["block_size"]]
                tensor[:, last, valid:].zero_()
    copy_end.record()
    torch.cuda.synchronize()
    payload_digest=None
    if plan.get("audit_kv_bytes"):
        # Functional audit only: fixed public extra normalization allowance.
        digest=hashlib.sha256()
        canonical_ids=sorted(bid for table in plan["block_tables"].values() for bid in table[0])
        index=torch.tensor(canonical_ids,device="cuda",dtype=torch.long)
        for tensor,_ in saved:
            data=tensor.index_select(1,index).contiguous().view(torch.uint8).cpu().numpy().tobytes()
            digest.update(data)
        payload_digest=digest.hexdigest()
    return dict(layers=len(saved), tensor_shapes=shapes, blocks_copied=len(pairs),
                blocks_cleared=len(plan["clear_block_ids"]), cuda_drained=True,
                cuda_copy_interval_ms=copy_start.elapsed_time(copy_end),
                canonical_kv_sha256=payload_digest)


class Pilot:
    def __init__(self, output, profile=False, audit_kv_bytes=False, block_prefill=False,
                 matched_scheduler=False):
        if matched_scheduler and not block_prefill:
            raise ValueError("Matched 512/2048 scheduling requires the larger worker buffers")
        self.output = output
        self.audit_kv_bytes=audit_kv_bytes
        self.llm = LLM(model=MODEL, max_model_len=2048,
            gpu_memory_utilization=.8, enforce_eager=True,
            enable_prefix_caching=True, num_gpu_blocks_override=512,
            max_num_seqs=8, max_num_batched_tokens=2048 if block_prefill else 256,
            long_prefill_token_threshold=512 if matched_scheduler else 64, async_scheduling=False,
            scheduler_cls="protected_prefill_scheduler.ProtectedPrefillScheduler",
            disable_log_stats=True, seed=0)
        self.engine = self.llm.llm_engine
        self.core = self.engine.engine_core.engine_core
        self.scheduler = self.core.scheduler
        # Default retains the previous comparison; the gate matches every
        # policy at 512/2048, including shared decode and cache preparation.
        self.scheduler.max_num_scheduled_tokens = 2048 if matched_scheduler else 256
        self.matched_scheduler = matched_scheduler
        self.scheduler.kv_cache_manager = TenantKVPartition(
            self.scheduler.kv_cache_manager, tenant_of, quotas={"A":128, "B":256})
        self.pool = self.scheduler.kv_cache_manager
        self.prompts = json.loads((ROOT/"data/document-workload-20261103/prompts.json").read_text())
        self.serial = 0
        self.step_trace = []
        self.prefix_steps = []
        self.gpu_events = []
        self.prefix_gpu_events = []
        worker=self.core.model_executor.driver_worker.worker
        for method in (("execute_model","sample_tokens") if profile else ()):
            original=getattr(worker,method)
            def timed(*args,_method=method,_original=original,**kwargs):
                start=torch.cuda.Event(enable_timing=True)
                end=torch.cuda.Event(enable_timing=True)
                start.record()
                result=_original(*args,**kwargs)
                end.record()
                self.gpu_events.append((_method,start,end))
                return result
            setattr(worker,method,timed)
        native_schedule = self.scheduler.schedule
        def observe_schedule():
            out = native_schedule()
            self.step_trace.append(dict(phase=self.scheduler._phase,
                tokens=dict(out.num_scheduled_tokens),
                scheduled_tokens=sum(out.num_scheduled_tokens.values())))
            return out
        self.scheduler.schedule = observe_schedule

    def add(self, tenant, label, salt, tokens=16, ignore=False):
        rid = f"{tenant}:{self.serial}:{label}"
        self.serial += 1
        params = SamplingParams(temperature=0, max_tokens=tokens,
            min_tokens=tokens, ignore_eos=True, seed=0,
            output_kind=RequestOutputKind.FINAL_ONLY,
            skip_reading_prefix_cache=ignore)
        sent = time.perf_counter_ns()
        internal = self.engine.add_request(rid,
            {"prompt":self.prompts[label], "cache_salt":salt}, params)
        return dict(external_id=rid, internal_id=internal, tenant=tenant,
                    label=label, sent_ns=sent)

    def drain(self, submitted, release_delay_ms=0, on_release=None):
        result = {}
        by_external = {r["external_id"]:r for r in submitted}
        by_internal = {r["internal_id"]:r for r in submitted}
        def release(record):
            delay=release_delay_ms if record["tenant"]=="B" else 0
            due=record["sent_ns"]+int(delay*1e6)
            time.sleep(max(0,(due-time.perf_counter_ns())/1e9))
            record["released_ns"]=time.perf_counter_ns()
            record["late"]=bool(delay and record["completed_ns"]>due)
            if on_release is not None:
                on_release(record)
        with ThreadPoolExecutor(max_workers=max(1,len(submitted))) as pool:
            releases=[]
            while self.engine.has_unfinished_requests():
                for response in self.engine.step():
                    if not response.finished:
                        continue
                    t = time.perf_counter_ns()
                    request = by_external.get(response.request_id, by_internal.get(response.request_id))
                    if request is None:
                        raise RuntimeError(f"Unknown output {response.request_id}")
                    tokens = list(response.outputs[0].token_ids)
                    record = dict(**request, completed_ns=t, released_ns=t,
                        prompt_tokens=len(response.prompt_token_ids),
                        cached_tokens=response.num_cached_tokens,
                        token_ids=tokens, text=response.outputs[0].text,
                        finish_reason=response.outputs[0].finish_reason)
                    result[request["external_id"]]=record
                    if (release_delay_ms and record["tenant"]=="B") or on_release is not None:
                        releases.append(pool.submit(release,record))
            for future in releases:
                future.result()
        assert len(result)==len(submitted)
        return result

    def normalize(self, scheduler):
        ids = scheduler._cohort["ids"]
        requests = scheduler.requests
        start = time.perf_counter_ns()
        plan = self.pool.plan_canonical(requests, ids)
        plan["audit_kv_bytes"]=self.audit_kv_bytes
        copied = self.engine.collective_rpc(gpu_canonical_copy, args=(plan,))[0]
        self.pool.commit_canonical(plan, requests)
        # Public frontier resets logging/profiling list capacity before shared decode.
        self.prefix_steps,self.step_trace=self.step_trace,[]
        self.prefix_gpu_events,self.gpu_events=self.gpu_events,[]
        return dict(**copied, elapsed_ms=(time.perf_counter_ns()-start)/1e6,
                    block_tables=plan["block_tables"],
                    pool_state=self.pool.snapshot())

    def prepare(self, submitted, chunk_tokens=64, on_release=None):
        """Cache provenance uses exactly the selected cold prefill recipe."""
        previous = self.scheduler.scheduler_config.long_prefill_token_threshold
        previous_budget = self.scheduler.max_num_scheduled_tokens
        self.scheduler.scheduler_config.long_prefill_token_threshold = chunk_tokens
        self.scheduler.max_num_scheduled_tokens = max(previous_budget, chunk_tokens)
        try:
            return self.drain(submitted, on_release=on_release)
        finally:
            self.scheduler.scheduler_config.long_prefill_token_threshold = previous
            self.scheduler.max_num_scheduled_tokens = previous_budget

    def case(self, name, condition, windows=None, join=None):
        assert not self.engine.has_unfinished_requests()
        self.pool.reset()
        a_salt, b_salt = "protected-pilot-fixed-A", "protected-pilot-fixed-B"
        prep = self.add("A", "A" if condition=="warm" else "D", a_salt, tokens=1)
        chunk = 512 if name=="protected_block512" or self.matched_scheduler else 64
        preparation = self.prepare([prep], chunk)
        self.step_trace = []
        self.prefix_steps = []
        self.gpu_events = []
        self.prefix_gpu_events = []
        submitted = [self.add("A","A",a_salt,ignore=name=="ignore_hits")]
        submitted += [self.add("B",label,b_salt) for label in "ABCD"]
        epoch = min(r["sent_ns"] for r in submitted)
        is_protected = name in ("protected", "protected_block512")
        if name=="protected_block512":
            windows, join = {"A":[0,200], "B":[200,700]}, 700
            if self.audit_kv_bytes:
                windows, join = {"A":[0,200], "B":[200,1200]}, 1200
        if is_protected:
            self.scheduler.configure_cohort(epoch,windows,join,
                [r["internal_id"] for r in submitted],normalizer=self.normalize,
                prefill_chunk_tokens=chunk,
                fuse_final_normalization=name=="protected_block512")
        try:
            result = self.drain(submitted,1240 if name=="release1240" else 0)
        except Exception as error:
            # Preserve an exact failed contract, including the actual GPU step.
            # Never enlarge its public windows in response to this sample.
            failure=dict(mode=name,condition=condition,error=repr(error),
                epoch_ns=epoch,submitted=submitted,observed_failure_ns=time.perf_counter_ns(),
                trace=self.scheduler._protected_trace+self.scheduler.trace,
                state=self.scheduler.state_snapshot() if is_protected else None,
                steps=self.prefix_steps+self.step_trace)
            with (self.output/"failed-contract.json").open("x") as fp:
                json.dump(failure,fp,indent=2);fp.write("\n")
            raise
        torch.cuda.synchronize()
        trace = self.scheduler.end_cohort() if is_protected else None
        record=dict(mode=name,condition=condition,epoch_ns=epoch,
                    requests=list(result.values()),preparation=list(preparation.values()),
                    protected=trace,pools=self.pool.snapshot(),steps=self.prefix_steps+self.step_trace,
                    model_tokens_scheduled=sum(s["scheduled_tokens"] for s in self.prefix_steps+self.step_trace),
                    inference_cuda_intervals_ms=sum(start.elapsed_time(end)
                        for _,start,end in self.prefix_gpu_events+self.gpu_events))
        record["scheduler_settings"]=dict(
            chunk_tokens=self.scheduler.scheduler_config.long_prefill_token_threshold,
            token_budget=self.scheduler.max_num_scheduled_tokens,
            worker_buffer_tokens=self.scheduler.scheduler_config.max_num_batched_tokens,
            preparation_chunk_tokens=chunk)
        for r in record["requests"]:
            r["e2e_ms"]=(r["released_ns"]-r["sent_ns"])/1e6
            r["post_completion_wait_ms"]=(r["released_ns"]-r["completed_ns"])/1e6
            assert len(r["token_ids"])==16
        return record


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    parser.add_argument("--pairs",type=int,default=2)
    parser.add_argument("--smoke-only",action="store_true")
    parser.add_argument("--calibration",type=Path,
                        help="completed generous smoke trials, used only to freeze one public schedule")
    parser.add_argument("--verify-kv-bytes",action="store_true")
    parser.add_argument("--block-prefill",action="store_true",
                        help="compare one fixed 512-token structural recipe against the three requested baselines")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    pilot=Pilot(args.output,profile=True,audit_kv_bytes=args.verify_kv_bytes,
                block_prefill=args.block_prefill)
    # Public generous smoke contract; costs are not success claims.
    windows={"A":[0,400],"B":[400,1700]};join=1900
    calibration=None
    if args.calibration:
        calibration=[]
        for line in args.calibration.read_text().splitlines():
            row=json.loads(line);tr=row["protected"]["trace"];measurement={}
            for owner in "AB":
                schedules=[e for e in tr if e["event"]=="schedule" and e.get("owner")==owner]
                ids={i for e in schedules for i in e["scheduled_tokens"]}
                drained=[e for e in tr if e["event"]=="gpu_output_drained" and e.get("phase")=="prefill" and set(e["request_ids"])&ids]
                measurement[owner]=drained[-1]["elapsed_ms"]-schedules[0]["elapsed_ms"]
            calibration.append(measurement)
        # One rule, fixed before comparison: 10ms grid plus public margins.
        pa=10*math.ceil(max(m["A"] for m in calibration)/10)+30
        pb=10*math.ceil(max(m["B"] for m in calibration)/10)+20
        windows={"A":[0,pa],"B":[pa,pa+pb]};join=pa+pb+50
    if args.verify_kv_bytes:
        join=max(v[1] for v in windows.values())+500
    if args.block_prefill and not args.calibration:
        # The OLD protected policy remains frozen at its existing 940ms.
        windows={"A":[0,230],"B":[230,890]};join=940
        if args.verify_kv_bytes:
            join=1390
    protocol=dict(status="functional development pilot, not confirmation or hardware security proof",
        public_windows_ms=windows,join_ms=join,pairs=args.pairs,
        policies=["protected","release1240","ignore_hits","direct"],
        attacker="no new classifier; existing first/full-completion timing diagnostic only",
        observations="in-process serving harness full response availability, no HTTP/network",
        model=MODEL,kv_quotas={"A":128,"B":256},block_size=16,
        calibration_source=str(args.calibration),calibration_phase_durations=calibration,
        protected_A_prefix_alignment_tokens=64,expected_protected_warm_hits=512,
        audit_kv_bytes=args.verify_kv_bytes)
    if args.block_prefill:
        protocol.update(policies=["protected_block512","protected","release1240","ignore_hits"],
            structural_policy=dict(chunk_tokens=512,worker_buffer_tokens=2048,
                public_windows_ms={"A":[0,200],"B":[200,700]},join_ms=700,
                final_window_includes_normalization=True,
                rationale="nine to two cold model invocations per tenant group; fixed before any new GPU execution; no post-result refit",
                cache_provenance="standalone A preparation uses 512+36, same as cold protected A; warm reuses first 512",
                runtime_bound="engineering contract checked per step and after normalization, not a proven hardware bound",
                development_failure="separate B deadline at650ms failed in kv01/kv02; fused final phase removes that internal barrier; public J700 unchanged"))
    (args.output/"protocol.json").write_text(json.dumps(protocol,indent=2)+"\n")
    smoke_mode="protected_block512" if args.block_prefill else "protected"
    cases=[(smoke_mode,"cold"),(smoke_mode,"warm")]
    if not args.smoke_only:
        # Single frozen plan, no parameter sweep or new attack training.
        cases=[]
        rng=random.Random(202611033701)
        for pair in range(args.pairs):
            modes=list(protocol["policies"]);rng.shuffle(modes)
            for mode in modes:
                conditions=["cold","warm"];rng.shuffle(conditions)
                cases.extend((mode,c) for c in conditions)
    with (args.output/"trials.jsonl").open("x") as fp:
        for index,(mode,condition) in enumerate(cases):
            row=pilot.case(mode,condition,windows,join)
            row["trial"]=index
            fp.write(json.dumps(row)+"\n");fp.flush()
            b=[r["e2e_ms"] for r in row["requests"] if r["tenant"]=="B"]
            print(index,mode,condition,"B first/full ms",round(min(b),2),round(max(b),2),flush=True)
    print("COMPLETE",args.output,flush=True)


if __name__=="__main__":
    main()
