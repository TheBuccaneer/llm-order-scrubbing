"""One frozen direct positive control for the existing C3 gate.

The original pilot, scheduler, KV managers and gate remain unchanged.
Only direct is measured; the old three policy results are read, never refit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, distribution
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "results/protected-prefill-gate-20261103-01"
SEED = 2026110401
SOURCES = ["protected_prefill_direct_control.py", "protected_prefill_direct_analysis.py",
           "protected_prefill_gate.py", "protected_prefill_gate_analysis.py",
           "protected_prefill_analysis.py", "protected_prefill_pilot.py",
           "protected_prefill_scheduler.py", "tenant_kv_partition.py"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, obj):
    with path.open("x") as fp:
        json.dump(obj, fp, indent=2); fp.write("\n")


def append(path, obj):
    with path.open("a") as fp:
        fp.write(json.dumps(obj)+"\n"); fp.flush()


def check_sources(plan):
    for name, expected in plan["source_sha256"].items():
        assert digest(ROOT/"src"/name) == expected, name


def freeze(folder):
    folder.mkdir(parents=True, exist_ok=False)
    previous = json.loads((OLD/"protocol.json").read_text())
    assert previous["versions"] == {name:version(name) for name in previous["versions"]}
    for name, expected in previous["source_sha256"].items():
        assert digest(ROOT/"src"/name) == expected, f"Old C3 source changed: {name}"
    # All pre-existing results, not just selected successful raw cohorts.
    prior = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/"results").rglob("*"))
             if p.is_file() and folder not in p.parents}
    rng = random.Random(SEED); cases = []
    for split, count in (("train", 12), ("test", 24)):
        for pair in range(count):
            conditions = ["cold", "warm"]; rng.shuffle(conditions)
            for condition in conditions:
                cases.append(dict(trial=len(cases), split=split, pair=pair,
                                  mode="direct", condition=condition))
    observer_rules = dict(previous["observers"],primary_policy="direct")
    installed = ["vllm/v1/core/sched/scheduler.py", "vllm/v1/core/kv_cache_manager.py",
                 "vllm/v1/core/block_pool.py", "vllm/v1/worker/gpu_model_runner.py"]
    plan = dict(frozen_utc=datetime.now(timezone.utc).isoformat(), seed=SEED,
        purpose="single final unprotected positive control; no defense development",
        modes=["direct"], train_pairs=12, test_pairs=24, cases=cases,
        reference_protocol_sha256=digest(OLD/"protocol.json"),
        reference_analysis_sha256=digest(OLD/"analysis.json"),
        scheduler=previous["scheduler"], fixed_case_gap_ms=50, fixed_profile=True,
        model="Qwen2.5-7B-Instruct local snapshot a09a35458c702b33eeacc393d103063234e8bc28",
        hardware=subprocess.check_output(["nvidia-smi", "-q"], text=True),
        engine="unchanged Pilot(profile=True,block_prefill=True,matched_scheduler=True,audit_kv_bytes=False)",
        cache=dict(quotas={"A":128,"B":256}, block_size=16,
                   salts=["protected-pilot-fixed-A","protected-pilot-fixed-B"],
                   preparation="reset real managers; standalone A/A warm or A/D cold, one output token, chunks512",
                   expected_A_hits_warm=544, expected_A_hits_cold=0, expected_B_hits=0),
        requests="same four 548-token documents; one A/A and four B/A-B-C-D; sixteen greedy output tokens each",
        policy="Pilot.case('direct'): native shared schedule, no cohort configuration, no normalization, no release delay, no skip_reading_prefix_cache",
        observations=previous["observations"], observers=observer_rules,
        prompt_sha256=digest(ROOT/"data/document-workload-20261103/prompts.json"),
        installed_vllm_sha256={str(distribution("vllm").locate_file(name)):
                              digest(distribution("vllm").locate_file(name)) for name in installed},
        split="24 train cohorts before 48 new test cohorts; numeric models and StandardScaler checkpoint before first test submission",
        differences=["new acquisition on 2026-11-04, one policy instead of interleaved three policies",
                     "new seed; warm/cold randomized within each pair; fixed ascending pair order",
                     "no protected functional warm/cold audit pair; only ordinary vLLM initialization warmup and per-case preparation",
                     "direct natively reuses544 A tokens, like release-only, versus protected512 and ignore0",
                     "same subclass/native scheduler branch and fixed real KV partitions; no public join or output deadline",
                     "no contemporaneous rerun of old policies; cross-session observer comparison is descriptive"],
        bootstrap_replicates=5000,
        statistics="reuse unchanged _observer_report: whole-pair percentile bootstrap BA/AUC; 5000 pair-label swaps with max absolute BA/AUC distance across both observers, +1 correction; no test score flips",
        paired_differences="cold minus warm, all24 test pairs; first-full-B, within-cohort medianB, and A; descriptive plus5000 whole-pair bootstrap of mean, nominal two-sided95%; no energy claim",
        positive_control_rule="configuration verified, no test failures/missing responses, joint paired-swap p<.05 AND at least one frozen observer has both BA and AUC pair-bootstrap95% lower bounds>.5; otherwise no convincing positive control, or technical caseC if configuration invalid",
        errors="preserve failing case with all submitted IDs and observed error time; fresh worker continues next preplanned case, never retry. Fatal initialization/preparation errors stop and are recorded as technical failure; no quiet replacement",
        overruns="not applicable to direct: no join/deadline; report errors and missing responses, never pretend zero-overrun is a direct security result",
        source_sha256={name:digest(ROOT/"src"/name) for name in SOURCES},
        versions={name:version(name) for name in ("vllm","torch","numpy","scipy","scikit-learn")},
        prior_results_sha256=prior)
    write_new(folder/"protocol.json",plan)
    snapshot=folder/"source"; snapshot.mkdir()
    for name in SOURCES:
        with (snapshot/name).open("xb") as fp: fp.write((ROOT/"src"/name).read_bytes())


def worker(folder):
    plan=json.loads((folder/"protocol.json").read_text()); check_sources(plan)
    from protected_prefill_pilot import Pilot
    from protected_prefill_direct_analysis import fit_direct
    rows=[json.loads(s) for s in (folder/"trials.jsonl").read_text().splitlines()] if (folder/"trials.jsonl").exists() else []
    assert [r["trial"] for r in rows] == list(range(len(rows)))
    if len(rows)==72: return 0
    engines=folder/"engines"; engines.mkdir(exist_ok=True)
    generation=len(list(engines.iterdir())); segment=engines/f"engine-{generation:03d}"; segment.mkdir()
    write_new(segment/"start.json",dict(utc=datetime.now(timezone.utc).isoformat(),
        perf_counter_ns=time.perf_counter_ns(),protocol_sha256=digest(folder/"protocol.json")))
    pilot=Pilot(segment,profile=True,block_prefill=True,matched_scheduler=True,audit_kv_bytes=False)
    for case in plan["cases"][len(rows):]:
        if case["split"]=="test":
            path=folder/"observers.json"
            if not path.exists(): write_new(path,fit_direct(rows))
            model_hash=digest(path); fence=folder/"test-start.json"
            if not fence.exists():
                write_new(fence,dict(utc=datetime.now(timezone.utc).isoformat(),
                    perf_counter_ns=time.perf_counter_ns(),training_cohorts=24,
                    test_cohorts_already_measured=0,observers_sha256=model_hash))
            assert json.loads(fence.read_text())["observers_sha256"]==model_hash
        try:
            row=pilot.case("direct",case["condition"])
            row.update(case,status="ok",engine_generation=generation)
        except Exception as error:
            failure_path=segment/"failed-contract.json"
            if not failure_path.exists():
                write_new(segment/"fatal-case.json",dict(case=case,error=repr(error)))
                raise
            row=dict(**case,status="contract_failure",failure=json.loads(failure_path.read_text()),
                     engine_generation=generation)
            append(folder/"trials.jsonl",row)
            print("RECORDED_FAILURE",case["trial"],flush=True)
            return 75
        append(folder/"trials.jsonl",row); rows.append(row)
        print("CASE",case["trial"],case["split"],case["condition"],"complete",flush=True)
        time.sleep(plan["fixed_case_gap_ms"]/1000)
    return 0


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("output",type=Path)
    parser.add_argument("--freeze-only",action="store_true")
    parser.add_argument("--run-frozen",action="store_true")
    parser.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    args=parser.parse_args(); folder=args.output.resolve()
    if args.worker: return worker(folder)
    if not args.run_frozen: freeze(folder)
    if args.freeze_only: return 0
    check_sources(json.loads((folder/"protocol.json").read_text()))
    while True:
        with (folder/"engine.log").open("a") as log:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),str(folder),"--worker"],stdout=log,stderr=log)
        if result.returncode==0: break
        if result.returncode!=75: raise RuntimeError(f"Unexpected failure; inspect {folder/'engine.log'}; no silent rerun")
    from protected_prefill_direct_analysis import analyze
    analyze(folder)
    print("COMPLETE",folder,flush=True)
    return 0


if __name__=="__main__": sys.exit(main())
