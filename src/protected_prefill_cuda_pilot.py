"""One fixed eager CUDA concurrency decision test using real vLLM forwards.

Snapshots four actual protected-prefill inputs, then bypasses mutable runner
bookkeeping. A single host thread enqueues the unchanged model/attention
operations into one or two streams. No graph, second scheduler or model copy.
"""

import argparse
import copy
from dataclasses import fields, is_dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import time

from protected_prefill_pilot import Pilot, torch
from vllm.forward_context import get_forward_context, override_forward_context
from vllm.utils.torch_utils import current_stream

ROOT=Path(__file__).resolve().parents[1]


def clone_inputs(value, memo):
    if id(value) in memo:return memo[id(value)]
    if isinstance(value,torch.Tensor):
        result=value.detach().clone();memo[id(value)]=result;return result
    if isinstance(value,dict):
        result={};memo[id(value)]=result
        result.update({k:clone_inputs(v,memo) for k,v in value.items()});return result
    if isinstance(value,(list,tuple)):
        result=[clone_inputs(v,memo) for v in value]
        result=tuple(result) if isinstance(value,tuple) else result
        memo[id(value)]=result;return result
    if is_dataclass(value):
        result=copy.copy(value);memo[id(value)]=result
        for field in fields(value):object.__setattr__(result,field.name,clone_inputs(getattr(value,field.name),memo))
        return result
    return value


def digest_tensors(tensors):
    h=hashlib.sha256()
    for tensor in tensors:h.update(tensor.contiguous().view(torch.uint8).cpu().numpy().tobytes())
    return h.hexdigest()


class Replay:
    def __init__(self, pilot):
        self.pilot=pilot;self.runner=pilot.core.model_executor.driver_worker.worker.model_runner
        self.forward=self.runner._model_forward
        self.calls={};self.prefix=None;self.streams={t:torch.cuda.Stream() for t in "AB"}
        self.kv=list(self.runner.kv_caches)
        assert len(self.kv)==28 and all(t.ndim==5 and t.shape[0]==2 and t.shape[2]==16 for t in self.kv)
        self.kv_pointers=[t.data_ptr() for t in self.kv]

    def capture(self, **kwargs):
        scheduler=self.pilot.scheduler
        if scheduler._cohort is None or scheduler._phase!="prefill":return self.forward(**kwargs)
        ctx=get_forward_context();owner=scheduler.trace[-1]["owner"]
        n=kwargs["input_ids"].numel();name=f"{owner}{n}"
        assert name in ("A512","A36","B2048","B144") and name not in self.calls
        memo={}
        frozen=replace(ctx,attn_metadata=clone_inputs(ctx.attn_metadata,memo),
            slot_mapping=clone_inputs(ctx.slot_mapping,memo),
            additional_kwargs=clone_inputs(ctx.additional_kwargs,memo))
        inputs=clone_inputs(kwargs,memo)
        md=next(iter(frozen.attn_metadata.values()))
        assert "FlashAttentionMetadata"==type(md).__name__,type(md).__name__
        starts=md.query_start_loc.cpu().tolist();seq=md.seq_lens.cpu().tolist()
        expected_q=512 if name in ("A512","B2048") else 36
        assert starts==[i*expected_q for i in range((1 if owner=="A" else 4)+1)]
        assert seq==[512 if expected_q==512 else 548]*(1 if owner=="A" else 4)
        positions=inputs["positions"].cpu().tolist()
        assert positions==list(range(0 if expected_q==512 else 512,512 if expected_q==512 else 548))*(1 if owner=="A" else 4)
        blocks=[]
        table=md.block_table.cpu().tolist()
        for i,length in enumerate(seq):blocks.extend(table[i][:(length+15)//16])
        lo,hi=(1,128) if owner=="A" else (129,384)
        assert all(lo<=bid<=hi for bid in blocks) and len(blocks)==len(set(blocks))
        for mapping in frozen.slot_mapping.values():
            actual=mapping[:n].div(16,rounding_mode="floor").cpu().tolist()
            assert all(lo<=bid<=hi for bid in actual)
        self.calls[name]=dict(context=frozen,inputs=inputs,
            indices=torch.tensor([x-1 for x in starts[1:]],device="cuda",dtype=torch.long),
            info=dict(owner=owner,tokens=n,query_start_loc=starts,seq_lens=seq,block_ids=blocks,
                      input_sha256=digest_tensors([inputs["input_ids"],inputs["positions"]])))
        result=self.forward(**kwargs)
        if name=="A512":
            torch.cuda.synchronize()
            self.prefix_ids=torch.tensor(blocks,device="cuda",dtype=torch.long)
            self.prefix=[tensor.index_select(1,self.prefix_ids).clone() for tensor in self.kv]
        return result

    def finish_setup(self):
        assert set(self.calls)=={"A512","A36","B2048","B144"} and self.prefix is not None
        self.active_ids=torch.tensor(self.calls["A36"]["info"]["block_ids"]+
            self.calls["B144"]["info"]["block_ids"],device="cuda",dtype=torch.long)
        assert self.active_ids.numel()==175 and len(set(self.active_ids.cpu().tolist()))==175
        self.clear_ids=torch.arange(1,385,device="cuda",dtype=torch.long)
        attentions=[m for m in self.runner.model.modules() if hasattr(m,"calculate_kv_scales")]
        assert len(attentions)==28 and all(not m.calculate_kv_scales for m in attentions)
        self.parameter_pointers={n:p.data_ptr() for n,p in self.runner.model.named_parameters()}
        self.rotary_pointers={n:m.cos_sin_cache.data_ptr() for n,m in self.runner.model.named_modules() if hasattr(m,"cos_sin_cache")}
        assert self.rotary_pointers
        assert all(m.cos_sin_cache.is_cuda for m in self.runner.model.modules() if hasattr(m,"cos_sin_cache"))
        torch.cuda.synchronize()

    def restore(self, condition):
        for tensor in self.kv:tensor.index_fill_(1,self.clear_ids,0)
        if condition=="warm":
            for tensor,prefix in zip(self.kv,self.prefix):tensor.index_copy_(1,self.prefix_ids,prefix)
        torch.cuda.synchronize()

    @torch.inference_mode()
    def enqueue(self, name, root, stages, outputs):
        c=self.calls[name];stream=self.streams[name[0]]
        with torch.cuda.stream(stream):
            assert current_stream().cuda_stream==torch.cuda.current_stream().cuda_stream==stream.cuda_stream
            start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
            start.record();host=time.perf_counter_ns()
            with override_forward_context(c["context"]):
                hidden=self.forward(**c["inputs"])
                logits=self.runner.model.compute_logits(hidden.index_select(0,c["indices"]))
                tokens=logits.argmax(dim=-1)
            enqueue_ms=(time.perf_counter_ns()-host)/1e6;end.record()
        outputs[name]=(hidden,logits,tokens)
        stages.append((name,start,end,enqueue_ms))
        return end

    def run(self, condition, mode):
        self.restore(condition);time.sleep(.05)
        sequences={"A":["A512","A36"] if condition=="cold" else ["A36"],"B":["B2048","B144"]}
        root=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
        stages=[];outputs={};t0=time.perf_counter_ns();root.record()
        for stream in self.streams.values():stream.wait_event(root)
        if mode=="serial":
            for tenant in "AB":
                for name in sequences[tenant]:self.enqueue(name,root,stages,outputs).synchronize()
        else:
            # Fixed initial B-before-A host order; no concurrent Python contexts.
            pending={tenant:(0,self.enqueue(sequences[tenant][0],root,stages,outputs)) for tenant in "BA"}
            while pending:
                progress=False
                for tenant in "BA":
                    if tenant not in pending:continue
                    index,event=pending[tenant]
                    if not event.query():continue
                    progress=True;index+=1
                    if index<len(sequences[tenant]):
                        pending[tenant]=(index,self.enqueue(sequences[tenant][index],root,stages,outputs))
                    else:del pending[tenant]
                if not progress:time.sleep(.0001)
        for _,_,event,_ in stages:torch.cuda.current_stream().wait_event(event)
        end.record();torch.cuda.synchronize();wall_ms=(time.perf_counter_ns()-t0)/1e6
        timeline=[dict(name=name,start_ms=root.elapsed_time(start),end_ms=root.elapsed_time(stop),
                       host_enqueue_ms=host) for name,start,stop,host in stages]
        # Verification is deliberately outside the timed region.
        kv_hash=digest_tensors([t.index_select(1,self.active_ids) for t in self.kv])
        logits_hash=digest_tensors([outputs[n][1] for n in ("A36","B144")])
        tokens={n:outputs[n][2].cpu().tolist() for n in ("A36","B144")}
        assert self.kv_pointers==[t.data_ptr() for t in self.kv]
        assert self.parameter_pointers=={n:p.data_ptr() for n,p in self.runner.model.named_parameters()}
        assert self.rotary_pointers=={n:m.cos_sin_cache.data_ptr() for n,m in self.runner.model.named_modules() if hasattr(m,"cos_sin_cache")}
        return dict(condition=condition,mode=mode,wall_ms=wall_ms,cuda_timeline_ms=root.elapsed_time(end),
            stages=timeline,KV_sha256=kv_hash,frontier_logits_sha256=logits_hash,frontier_tokens=tokens)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("output",type=Path);args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    rng=random.Random(202611038041)
    pairs=[("cold",i) for i in range(12)]+[("warm",i) for i in range(6)];rng.shuffle(pairs)
    cases=[]
    for condition,pair in pairs:
        modes=["serial","parallel"];rng.shuffle(modes)
        cases.extend(dict(condition=condition,pair=pair,mode=mode) for mode in modes)
    previous=ROOT/"results/protected-prefill-critical-path-20261103/analysis.json"
    target=json.loads(previous.read_text())["target"]["required_public_join_ms"]
    protocol=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),seed=202611038041,cases=cases,cold_pairs=12,warm_pairs=6,
        primary="eager real model forward+logits+argmax; shared weights, cloned metadata; one host thread; no CUDA graphs",
        excluded="full scheduler, CPU input preparation, full sampler/postprocessing, canonical normalization; restore/hash outside timing",
        measured="first event/enqueue to complete device synchronization; eager host enqueue and inter-stage waits included",
        cold_success=dict(minimum_gain_ms=66,reserve_ms=20,required_lower95_gain_ms=86,
            required_public_join_ms=target,host_and_sampler_allowance_ms=20,normalizer_allowance_ms=7,
            max_parallel_wall_ms=target-20-7-20),
        warmup="two fixed serial/parallel pairs per condition, excluded; no tuning",
        paired_bootstrap=dict(replicates=5000,statistic="mean serial wall minus parallel wall",lower_quantile=.05),
        inference="positive gate is hardware feasibility only; full runner integration remains separate",
        source_sha256={n:hashlib.sha256((ROOT/"src"/n).read_bytes()).hexdigest() for n in
            [Path(__file__).name,"protected_prefill_pilot.py","protected_prefill_scheduler.py","tenant_kv_partition.py"]},
        previous_analysis_sha256=hashlib.sha256(previous.read_bytes()).hexdigest())
    with (out/"protocol.json").open("x") as fp:json.dump(protocol,fp,indent=2);fp.write("\n")
    pilot=Pilot(out,block_prefill=True,matched_scheduler=True)
    replay=Replay(pilot);replay.runner._model_forward=replay.capture
    try:
        setup=pilot.case("protected","cold",{"A":[0,2000],"B":[2000,6000]},6500)
    finally:replay.runner._model_forward=replay.forward
    replay.finish_setup()
    with (out/"setup.json").open("x") as fp:json.dump(dict(calls={n:c["info"] for n,c in replay.calls.items()},
        setup=setup,shared_parameter_tensors=len(replay.parameter_pointers),layers=len(replay.kv),
        torch_version=torch.__version__,GPU=torch.cuda.get_device_name()),fp);fp.write("\n")
    for condition in ("cold","warm"):
        for _ in range(2):
            for mode in ("serial","parallel"):replay.run(condition,mode)
    rows=[]
    with (out/"trials.jsonl").open("x") as fp:
        for case in cases:
            row=replay.run(case["condition"],case["mode"]);row.update(pair=case["pair"],trial=len(rows))
            fp.write(json.dumps(row)+"\n");fp.flush();rows.append(row)
            print("CASE",len(rows),row["condition"],row["mode"],round(row["wall_ms"],3),flush=True)
    import numpy as np
    result=dict(conditions={},correctness=True,gate_pass=False)
    for condition,count in (("cold",12),("warm",6)):
        selected=[r for r in rows if r["condition"]==condition]
        serial=[next(r for r in selected if r["pair"]==i and r["mode"]=="serial") for i in range(count)]
        parallel=[next(r for r in selected if r["pair"]==i and r["mode"]=="parallel") for i in range(count)]
        gain=np.array([a["wall_ms"]-b["wall_ms"] for a,b in zip(serial,parallel)])
        boot=np.random.default_rng(202611038041).choice(gain,(5000,count),replace=True).mean(1)
        correct=len({r["KV_sha256"] for r in selected})==len({r["frontier_logits_sha256"] for r in selected})==1
        result["correctness"] &= correct
        result["conditions"][condition]=dict(pairs=count,serial_median_ms=float(np.median([r["wall_ms"] for r in serial])),
            parallel_median_ms=float(np.median([r["wall_ms"] for r in parallel])),
            mean_gain_ms=float(gain.mean()),median_gain_ms=float(np.median(gain)),minimum_gain_ms=float(gain.min()),
            gain_mean_one_sided95_lower_ms=float(np.quantile(boot,.05)),
            max_parallel_ms=max(r["wall_ms"] for r in parallel),correctness=correct)
    cold=result["conditions"]["cold"];gate=protocol["cold_success"]
    result["cold_warm_frontiers_equal"]=len({r["KV_sha256"] for r in rows})==len({r["frontier_logits_sha256"] for r in rows})==1
    result["correctness"] &= result["cold_warm_frontiers_equal"]
    result["gate_pass"]=bool(result["correctness"] and cold["gain_mean_one_sided95_lower_ms"]>=86
        and cold["max_parallel_ms"]<=gate["max_parallel_wall_ms"])
    result["decision"]="hardware gate passed; runner integration may proceed" if result["gate_pass"] else "hardware gate not passed; do not implement the two-runner scheduler"
    with (out/"analysis.json").open("x") as fp:json.dump(result,fp,indent=2);fp.write("\n")
    print(json.dumps(result,indent=2),flush=True)


if __name__=="__main__":main()
