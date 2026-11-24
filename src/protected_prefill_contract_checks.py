"""CPU witnesses for the source-bound logical contract, not a GPU proof.

Real KV managers, real canonical tensor operations, real stop/deadline guards.
CUDA device/event plumbing is replaced only for the tensor-copy CPU test.
These checks support the algebraic proof; they do not prove backend semantics,
wall-clock noninterference, or correctness for every possible Python state.
"""

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch

from protected_prefill_checks import check_world
from protected_prefill_pilot import gpu_canonical_copy
from protected_prefill_scheduler import ProtectedPrefillError, ProtectedPrefillScheduler
from vllm.v1.core.sched.scheduler import Scheduler
from vllm.v1.core.sched.utils import check_stop


class CPUEvent:
    def __init__(self, **kwargs):pass
    def record(self):pass
    def elapsed_time(self, other):return 0


def copied_world(warm, corrupt_B=False):
    hits,plan,metadata=check_world(warm,64)
    layers=[torch.full((2,512,16,1,1),91 if warm else 73,dtype=torch.int64) for _ in range(28)]
    for layer,tensor in enumerate(layers):
        tensor[:,0].fill_(-1)
        for rid,info in plan["requests"].items():
            # A's private payload is intentionally NOT assumed equal.
            base=(100000 if warm else 200000) if rid.startswith("A:") else 300000+10000*int(rid.split(":")[1])
            for block,src in enumerate(info["source_block_ids"]):
                values=torch.arange(16,dtype=torch.int64)+base+layer*100+block*16
                tensor[:,src,:,0,0]=values
            if corrupt_B and rid=="B:0":tensor[:,info["source_block_ids"][0],0,0,0]+=1
    real_tensor=torch.tensor
    def cpu_tensor(*args,**kwargs):
        if kwargs.get("device")=="cuda":kwargs["device"]="cpu"
        return real_tensor(*args,**kwargs)
    worker=SimpleNamespace(model_runner=SimpleNamespace(kv_caches=layers))
    with patch.object(torch,"tensor",cpu_tensor),patch.object(torch.cuda,"synchronize",lambda:None),patch.object(torch.cuda,"Event",CPUEvent):
        result=gpu_canonical_copy(worker,plan)
    by_tenant={}
    for tenant in "AB":
        ids=[bid for rid,table in plan["block_tables"].items() if rid.startswith(tenant+":") for bid in table[0]]
        by_tenant[tenant]=torch.stack([t[:,ids].clone() for t in layers])
    active={bid for table in plan["block_tables"].values() for bid in table[0]}
    unused=sorted(set(range(1,385))-active)
    for tensor in layers:
        assert not tensor[:,unused].any()
        for rid,table in plan["block_tables"].items():
            assert not tensor[:,table[0][34],4:].any()
            assert not tensor[:,table[0][35]].any()
        assert torch.all(tensor[:,0]==-1)
    assert result["layers"]==28 and result["blocks_copied"]==175
    return hits,plan,metadata,by_tenant


def deadline_guard(elapsed_ms):
    scheduler=ProtectedPrefillScheduler.__new__(ProtectedPrefillScheduler)
    scheduler._cohort=dict(epoch_ns=0,ids=["A:test"])
    scheduler.trace=[];scheduler._inflight_ids={"A:test"}
    scheduler._phase="prefill";scheduler._joined=False
    scheduler._step_deadline_ns=200000000
    scheduler.requests={"A:test":SimpleNamespace(num_output_tokens=1)}
    with patch.object(Scheduler,"update_from_output",return_value={}),patch("protected_prefill_scheduler.time.perf_counter_ns",return_value=int(elapsed_ms*1e6)):
        try:scheduler.update_from_output(None,None)
        except ProtectedPrefillError:return "contract_failure"
    return "continue"


def main():
    parser=argparse.ArgumentParser();parser.add_argument("output",type=Path);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    warm=copied_world(True);cold=copied_world(False);changed_B=copied_world(False,True)
    assert warm[0]["A:target"]==512 and cold[0]["A:target"]==0
    assert warm[2]==cold[2]
    assert warm[1]["requests"]["A:target"]["source_block_ids"]!=cold[1]["requests"]["A:target"]["source_block_ids"]
    assert torch.equal(warm[3]["B"],cold[3]["B"])
    assert not torch.equal(warm[3]["A"],cold[3]["A"])
    assert not torch.equal(cold[3]["B"],changed_B[3]["B"])
    for token in (9,41):
        for length in range(1,17):
            request=SimpleNamespace(pooling_params=None,
                sampling_params=SimpleNamespace(min_tokens=16,eos_token_id=9,stop_token_ids=[],repetition_detection=None),
                num_output_tokens=length,output_token_ids=[token]*length,
                num_tokens=548+length,max_tokens=16)
            assert check_stop(request,2048)==(length==16)
    assert deadline_guard(100)=="continue" and deadline_guard(210)=="contract_failure"
    root=Path(__file__).resolve().parents[1]
    sources=["src/protected_prefill_scheduler.py","src/tenant_kv_partition.py","src/protected_prefill_pilot.py",
             "src/protected_prefill_server.py","src/protected_prefill_contract_checks.py"]
    result=dict(status="CPU contract witnesses; analytical proof and explicit trusted-kernel contract required",
        real_KV_managers=True,real_tensor_copy_body_on_CPU=True,CUDA_plumbing_mocked=True,GPU_execution=False,
        different_A_payload_and_source_addresses=True,B_canonical_payload_equal=True,A_payload_stays_different=True,
        copied_28_layers=True,canonical_manager_metadata_equal=True,unused_tenant_blocks_and_tail_zero=True,
        source_B_difference_is_preserved_not_repaired=True,fixed_16_token_stop_independent_of_A_values=True,
        real_deadline_guard_can_distinguish_two_runtimes=True,
        source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources},
        vllm_sources_sha256={str(Path(__import__('vllm').__file__).parent/s):hashlib.sha256((Path(__import__('vllm').__file__).parent/s).read_bytes()).hexdigest()
            for s in ['v1/core/sched/scheduler.py','v1/core/sched/utils.py','v1/worker/gpu_model_runner.py','v1/worker/gpu_input_batch.py']})
    with (args.output/"checks.json").open("x") as fp:json.dump(result,fp,indent=2);fp.write("\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
