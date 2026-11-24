"""One frozen configuration-controlled gate; no defender parameter search.

The supervisor persists the entire case plan before starting CUDA. A worker
runs until completion or a protected contract failure. Failure is a measured
outcome, then a fresh process resumes the next PREPLANNED case. Observers are
fit and persisted after all training cases and before any test case.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MODES = ["protected_block512", "ignore_hits", "release1240"]


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def write_new(path, obj):
    with path.open("x") as fp:
        json.dump(obj, fp, indent=2); fp.write("\n")


def append_row(path, obj):
    with path.open("a") as fp:
        fp.write(json.dumps(obj)+"\n"); fp.flush()


def freeze(folder):
    folder.mkdir(parents=True, exist_ok=False)
    rng = random.Random(202611037031)
    cases = []
    for split, pairs in (("train", 12), ("test", 24)):
        for pair in range(pairs):
            modes = MODES.copy(); rng.shuffle(modes)
            for mode in modes:
                conditions = ["cold", "warm"]; rng.shuffle(conditions)
                for condition in conditions:
                    cases.append(dict(trial=len(cases), split=split, pair=pair,
                                      mode=mode, condition=condition))
    sources = ["protected_prefill_gate.py", "protected_prefill_gate_analysis.py",
               "protected_prefill_pilot.py", "protected_prefill_scheduler.py",
               "tenant_kv_partition.py"]
    protocol = dict(
        frozen_utc=datetime.now(timezone.utc).isoformat(), seed=202611037031,
        status="configuration-controlled pilot, not a general security proof",
        modes=MODES, train_pairs=12, test_pairs=24, cases=cases,
        scheduler=dict(chunk_tokens=512, token_budget=2048, worker_buffer_tokens=2048,
                       preparation_chunk_tokens=512, shared_decode_limits_identical=True),
        protected=dict(windows_ms={"A":[0,200], "B_and_normalization":[200,700]},
                       join_ms=700, normalizer="unchanged", private_warm_hits=512),
        release_only=dict(B_arrival_anchored_ms=1240, A_unpadded=True, native_warm_hits=544),
        reset="identical fresh real KV managers before every case; one standalone A preparation",
        fixed_case_gap_ms=50, fixed_profile=True,
        unit="one five-request cohort; bootstrap and label swaps use whole warm/cold pair blocks",
        observations="in-process own full-response/error availability, four B document labels; no HTTP validation",
        split="all 12 training pair blocks before 24 new test pair blocks; no cohort reused across splits",
        observers=dict(
            primary_policy="protected_block512",
            first_B="min B released_ns minus min B sent_ns; train-fitted threshold and direction",
            joint="four label-ordered own B durations and error flag; StandardScaler+LogisticRegression(C=1,solver=lbfgs,max_iter=1000); train only",
            test="fixed models, no test-direction flip, no test feature or hyperparameter selection",
            errors="all four B error availability times and status included; never filter failures from observers"),
        bootstrap_replicates=5000, leakage_ba_limit=.65,
        gates=dict(
            normalization="all-layer active KV hash and all five outputs equal in separate fixed functional pair; unchanged managers/copy; canonical scheduler metadata and worker remap checked on every successful protected cohort",
            leakage="primary protected policy: paired-swap p>.05 AND paired-bootstrap 95% upper bound on max absolute distance from .5 across BA/AUC of both frozen observers <.15; signed predictions/scores unchanged; limited to these observers and this workload",
            latency="test warm paired ignore-minus-protected improvement >0 for both A and cohort-median B; simultaneous 95% lower bounds across A/B/CUDA via alpha=.05/3",
            compute="same simultaneous lower bound >0 for CUDA inference intervals plus canonical copy, warm test pairs; not energy",
            failures="cost comparison inconclusive if any required test cohort fails; successful-only costs descriptive",
            overruns="protected failure fraction <=.05, and one-sided 95% exact binomial upper bound on probability(any failure in a complete warm/cold pair) <.10 across all36 pairs",
            combined="normalization AND leakage AND overruns AND (latency OR compute); no general privacy or novelty claim"),
        recovery="count the failing case, discard engine, fresh worker continues next preplanned case; never retry that case or enlarge J",
        versions={name:version(name) for name in ("vllm","torch","numpy","scipy","scikit-learn")},
        source_sha256={name:hashlib.sha256((ROOT/"src"/name).read_bytes()).hexdigest() for name in sources})
    prior=json.loads((ROOT/"results/tenant-release-feasibility-20261103/analysis.json").read_text())["input_sha256"]
    for path in (ROOT/"results").glob("protected-prefill*/trials.jsonl"):
        prior[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    protocol["prior_raw_sha256"]=prior
    for name,expected in prior.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, name
    write_new(folder/"protocol.json", protocol)
    snapshot=folder/"source"; snapshot.mkdir()
    for name in sources:
        with (snapshot/name).open("xb") as fp:
            fp.write((ROOT/"src"/name).read_bytes())


def worker(folder):
    from protected_prefill_pilot import Pilot
    from protected_prefill_scheduler import ProtectedPrefillError
    from protected_prefill_gate_analysis import fit_observers

    plan = json.loads((folder/"protocol.json").read_text())
    for name, expected in plan["source_sha256"].items():
        assert hashlib.sha256((ROOT/"src"/name).read_bytes()).hexdigest()==expected, name
    rows = read_rows(folder/"trials.jsonl")
    completed = {r["trial"] for r in rows}
    assert completed==set(range(len(rows))), "noncontiguous or duplicate results"
    if len(rows)==len(plan["cases"]):
        return 0
    generations = folder/"engines"; generations.mkdir(exist_ok=True)
    generation = len(list(generations.iterdir()))
    segment = generations/f"engine-{generation:03d}"; segment.mkdir()
    pilot = Pilot(segment, profile=True, block_prefill=True, matched_scheduler=True,
                  audit_kv_bytes=True)
    # Fixed functional allowance only. Never feed these two rows to observers.
    for condition in ("cold", "warm"):
        row = pilot.case("protected_block512", condition)
        row["engine_generation"] = generation
        append_row(folder/"functional-checks.jsonl", row)
    pilot.audit_kv_bytes = False
    for case in plan["cases"]:
        if case["trial"] in completed:
            continue
        if case["split"]=="test":
            model_path = folder/"observers.json"
            if not model_path.exists():
                assert len(rows)==72 and all(r["split"]=="train" for r in rows)
                write_new(model_path, fit_observers(rows))
            model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
            fence = folder/"test-start.json"
            if not fence.exists():
                write_new(fence, dict(utc=datetime.now(timezone.utc).isoformat(),
                    perf_counter_ns=time.perf_counter_ns(),
                    training_cohorts=72, test_cohorts_already_measured=0,
                    observers_sha256=model_hash))
            assert json.loads(fence.read_text())["observers_sha256"]==model_hash
        try:
            row = pilot.case(case["mode"], case["condition"])
            row.update(case, status="ok", engine_generation=generation)
        except ProtectedPrefillError:
            failure = json.loads((segment/"failed-contract.json").read_text())
            row = dict(**case, status="contract_failure", failure=failure,
                       engine_generation=generation)
            append_row(folder/"trials.jsonl", row)
            print("CONTRACT_FAILURE", case["trial"], case["split"], flush=True)
            return 75
        append_row(folder/"trials.jsonl", row); rows.append(row)
        print("CASE", case["trial"], case["split"], "complete", flush=True)
        time.sleep(plan["fixed_case_gap_ms"]/1000)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(); folder = args.output.resolve()
    if args.worker:
        return worker(folder)
    freeze(folder)
    while True:
        with (folder/"engine.log").open("a") as log:
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                     str(folder), "--worker"], stdout=log, stderr=log)
        if result.returncode==0:
            break
        if result.returncode!=75:
            raise RuntimeError(f"Worker stopped with unexpected error; inspect {folder/'engine.log'}")
        print("Recorded failure; fresh worker resumes next planned case", flush=True)
    from protected_prefill_gate_analysis import analyze
    analyze(folder)
    print("COMPLETE", folder, flush=True)
    return 0


if __name__=="__main__":
    sys.exit(main())
