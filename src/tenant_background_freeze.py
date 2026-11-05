"""Materialize only the OLD C2 models and freeze one64-case plan, CPU only."""
from datetime import datetime,timezone
import hashlib
from importlib.metadata import version,distribution
import json
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from tenant_scheduler_analysis import client_features
from tenant_background_analysis import predict

ROOT=Path(__file__).resolve().parents[1]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,obj):
    with path.open("x") as fp: json.dump(obj,fp,indent=2); fp.write("\n")


def main(folder):
    folder.mkdir(parents=True,exist_ok=False)
    old=ROOT/"results/tenant-offset-20261103"
    training=ROOT/"results/tenant-scheduler-20261103/dev/trials.jsonl"
    train=[json.loads(s) for s in training.read_text().splitlines() if json.loads(s)["condition"] in ("cold","warm")]
    assert len(train)==16
    old_rows=[json.loads((old/f"case-{i:02d}/trial.json").read_text()) for i in range(24)]
    main_old=[r for r in old_rows if r["condition"] in ("warm","cold")]
    y=np.array([int(r["condition"]=="warm") for r in train])
    expected=json.loads((old/"analysis.json").read_text())
    models={}
    for name in ("T1","T2"):
        model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=1000))
        model.fit(np.array([client_features(r,name) for r in train]),y)
        scaler,lr=model.steps[0][1],model.steps[1][1]
        numeric=dict(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
            coefficient=lr.coef_[0].tolist(),intercept=float(lr.intercept_[0]),classes=lr.classes_.tolist())
        pred,_=predict(main_old,numeric,name)
        assert np.array_equal(pred,model.predict(np.array([client_features(r,name) for r in main_old])))
        hits=int(sum(p==int(r["condition"]=="warm") for r,p in zip(main_old,pred)))
        assert hits==expected["attacker"][name]["hits"]
        for condition in ("absent","other_cold"):
            controls=[r for r in old_rows if r["condition"]==condition]
            cp,_=predict(controls,numeric,name)
            assert int(cp.sum())==expected["attacker"][name]["control_predictions_warm"][condition]
        models[name]=numeric
    write(folder/"observers.json",dict(status="old models reconstructed deterministically from old16 development groups only; no new-data fitting",
        old_training_sha256=digest(training),recipe="unmodified C2 StandardScaler+LogisticRegression(C=1,max_iter=1000,default lbfgs)",
        old_hidden_offset_hits_reproduced={name:expected["attacker"][name]["hits"] for name in models},models=models))
    salts=json.loads((old/"salts.json").read_text())
    salts["tenant_C"]=hashlib.sha256(b"ICCAI2027 fixed C2 background tenant C 20261105").hexdigest()
    assert len(set(salts.values()))==3
    write(folder/"salts.json",salts)
    (folder/"prompts.json").write_bytes((ROOT/"data/document-workload-20261103/prompts.json").read_bytes())
    seed=2026110501; rng=random.Random(seed); offsets=[0,150,300,450]*6; rng.shuffle(offsets)
    blocks=[]
    for pair,offset in enumerate(offsets):
        order=list("ABCD"); rng.shuffle(order)
        conditions=["cold","warm"]; rng.shuffle(conditions)
        blocks.append([dict(pair=pair,condition=c,victim_offset_ms=offset,send_order=order) for c in conditions])
    for condition in ("absent","other_cold"):
        for offset in [0,150,300,450]*2:
            order=list("ABCD");rng.shuffle(order)
            blocks.append([dict(pair=None,condition=condition,victim_offset_ms=offset,send_order=order)])
    rng.shuffle(blocks)
    cases=[dict(index=i,**case) for i,case in enumerate(c for block in blocks for c in block)]
    model="/home/rock/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28"
    server=[sys.executable,"-m","vllm.entrypoints.openai.api_server","--host","127.0.0.1","--port","8765",
        "--model",model,"--served-model-name","Qwen/Qwen2.5-7B-Instruct","--max-model-len","2048",
        "--gpu-memory-utilization","0.8","--enforce-eager","--enable-prefix-caching","--enable-prompt-tokens-details",
        "--max-num-batched-tokens","256","--long-prefill-token-threshold","64"]
    source_names=["tenant_background_freeze.py","tenant_background_case.py","tenant_background_run.py","tenant_background_analysis.py",
        "tenant_offset_case.py","tenant_offset_analysis.py","tenant_scheduler_analysis.py","bos_pilot.py","cache_order_pilot.py","order_release_proxy.py"]
    prior={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/"results").rglob('*')) if p.is_file() and folder not in p.parents}
    installed=["vllm/v1/core/sched/scheduler.py","vllm/entrypoints/openai/completion/serving.py"]
    plan=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),seed=seed,cases=cases,
        scope="single final C2 background-load test; no C1 GPU test; no profile search",
        main_pairs=24,main_cases=48,controls={"absent":8,"other_cold":8},offsets_ms=[0,150,300,450],
        server_command=server,backend="fresh API backend per case; same native C2 config256/64, model and version",
        background=dict(tenant="C",request_count=1,prompt_label="B",prompt_tokens=548,
            max_tokens=256,min_tokens=256,temperature=0,cache="fresh, distinct fixed C salt, no C preparation",
            planned_start_ms_relative_group=-100,stream=True,stream_usage=True,
            execution="one request only, no condition-dependent refill/cancellation; wait for full completion even after B finishes"),
        timing="unchanged A preparation then250ms quiet; release C thread, wait100ms, release A/B threads. B0/10/20/30ms; A hidden0/150/300/450ms. Equal C parameters in all64 cases",
        load_validation="require C548 input/256 generated tokens, positive C/B request interval overlap AND at least one C text-stream event while B pending in every case; record actual start/first/last-token/complete times. Stream events prove progress, not exact GPU kernel overlap/utilization equality",
        cache_validation="A warm544/cold0, B0, C0. Pinned vLLM serving.py omits prompt_tokens_details for zero cached tokens; backend/proxy raw None therefore zero on unstripped responses, while sanitized B None alone is not evidence",
        observers="old T1/T2 from results/tenant-scheduler-20261103/dev/trials.jsonl,16 groups; serialized before test. Old analysis did not persist coefficients; deterministic reconstruction with unchanged recipe reproduces old14/16 and16/16 plus controls. No new data in fitting, no later calibration",
        bootstrap_replicates=5000,
        statistics=dict(primary="cold-minus-warm first B full receipt relative first B send; all24 pairs; exact one-sided sign test at.05 excluding exact zero ties;5000 whole-pair percentile CIs for median and mean stratified by four offsets,6 pairs resampled per offset",
            secondary="T1/T2 fixed numeric score>0, accuracy/BA/ROC-AUC (warm positive); same5000 stratified pair draws; no score flipping, retraining or A/C features",
            decision_RQ1="no integrity failure, all24 pairs complete, sign p<.05 AND median-effect95% lower bound>0",
            decision_RQ2="no integrity failure, all48 main cases scorable AND at least one fixed observer with BA95% lower>.5 AND AUC95% lower>.5; nominal exploratory intervals for the two existing observers, no new algorithm",
            controls="all16 controls reported separately; other-cold classifications cannot identify document A; if both absent and other-cold called cold, report nonspecific/uncalibrated responses",
            interpretation="A if both criteria, B if only primary, C if neither; mixed if only secondary. Specificity D independently. Statistical paired effect is not a single-request exploit"),
        errors="all64 planned case slots run once. No retries; errors/timeouts/missing responses retained. Missing B makes inferential gate incomplete, success-only numbers descriptive. Startup failure continues next planned case with failure recorded",
        source_sha256={"src/"+name:digest(ROOT/"src"/name) for name in source_names},
        installed_sha256={str(distribution("vllm").locate_file(name)):digest(distribution("vllm").locate_file(name)) for name in installed},
        artifact_sha256={name:digest(folder/name) for name in ("observers.json","salts.json","prompts.json")},
        prior_results_sha256=prior,versions={n:version(n) for n in ("vllm","torch","numpy","scipy","scikit-learn")},
        gpu_inventory=subprocess.check_output(["nvidia-smi","-q"],text=True),
        commit_requirement="protocol/artifacts/source snapshot committed locally before first GPU backend; commit.json records commitID and protocolSHA, checked by runner")
    write(folder/"protocol.json",plan)
    snapshot=folder/"source";snapshot.mkdir()
    for name in source_names: (snapshot/name).write_bytes((ROOT/"src"/name).read_bytes())
    print("FROZEN",folder,"64 cases",len(prior),"prior result files",flush=True)


if __name__=="__main__": main(Path(sys.argv[1]).resolve())
