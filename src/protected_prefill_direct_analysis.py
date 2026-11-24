"""C3 direct control: exact original observer recipes, independent new data."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from sklearn import __version__ as sklearn_version
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.preprocessing import StandardScaler

from protected_prefill_gate_analysis import (_features, _hash, _observer_report,
    _pair_indices, _stats, _cost)

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"results/protected-prefill-gate-20261103-01"


def fit_direct(rows):
    if len(rows)!=24 or any(r["split"]!="train" or r["mode"]!="direct" for r in rows):
        raise ValueError("Only the24 new direct training cohorts are permitted")
    chosen=sorted(rows,key=lambda r:(r["pair"],r["condition"]))
    _pair_indices(chosen,expected=12)
    x,first=zip(*[_features(r) for r in chosen]); x,first=np.array(x),np.array(first)
    y=np.array([int(r["condition"]=="warm") for r in chosen])
    unique=np.unique(first)
    thresholds=np.r_[unique[0]-1,(unique[:-1]+unique[1:])/2,unique[-1]+1]
    best=None
    for direction in (-1,1):
        for threshold in thresholds:
            pred=direction*(first-threshold)>=0
            ba=float(balanced_accuracy_score(y,pred))
            if best is None or ba>best["train_balanced_accuracy"]:
                best=dict(direction=direction,threshold_ms=float(threshold),train_balanced_accuracy=ba)
    scaler=StandardScaler().fit(x)
    model=LogisticRegression(C=1,solver="lbfgs",max_iter=1000).fit(scaler.transform(x),y)
    return dict(train_sha256=_hash(rows),train_cohorts=24,sklearn_version=sklearn_version,
        features="unchanged _features: four label-ordered own B durations plus failure bit; first full B relative first B send",
        threshold_tie="direction -1 before +1; ascending train midpoints; first maximum retained",
        models={"direct":dict(stump=best,
            logistic=dict(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
                coefficient=model.coef_[0].tolist(),intercept=float(model.intercept_[0]),
                classes=model.classes_.tolist(),C=1,solver="lbfgs",max_iter=1000),
            train_sha256=_hash(chosen),train_cohorts=24)})


def analyze(folder):
    folder=Path(folder)
    from protected_prefill_direct_control import digest,write_new,check_sources
    plan=json.loads((folder/"protocol.json").read_text()); check_sources(plan)
    rows=[json.loads(s) for s in (folder/"trials.jsonl").read_text().splitlines()]
    assert len(rows)==72
    assert all(all(row[k]==case[k] for k in case) for row,case in zip(rows,plan["cases"]))
    train,test=rows[:24],rows[24:]; pairs=_pair_indices(test,expected=24)
    model_path=folder/"observers.json"; models=json.loads(model_path.read_text())
    fence=json.loads((folder/"test-start.json").read_text())
    assert models["train_sha256"]==_hash(train)
    assert digest(model_path)==fence["observers_sha256"]
    submitted=test[0]["requests"] if test[0]["status"]=="ok" else test[0]["failure"]["submitted"]
    assert fence["perf_counter_ns"]<min(r["sent_ns"] for r in submitted)
    for path,expected in plan["prior_results_sha256"].items():
        assert digest(ROOT/path)==expected, f"Old result changed: {path}"
    for name,expected in plan["source_sha256"].items():
        assert digest(folder/"source"/name)==expected
    errors=[]; completed=0; hit_counts={"warm":[],"cold":[],"B":[]}
    for row in rows:
        if row["status"]!="ok": continue
        tag=row["trial"]
        def check(condition,message):
            if not condition: errors.append(dict(trial=tag,error=message))
        check(row["scheduler_settings"]==dict(chunk_tokens=512,token_budget=2048,
              worker_buffer_tokens=2048,preparation_chunk_tokens=512),"settings mismatch")
        check(row["protected"] is None,"protected execution used")
        check(all(s["phase"]=="native" and s["scheduled_tokens"]<=2048 and
              all(n<=512 for n in s["tokens"].values()) for s in row["steps"]),"non-native or excess schedule")
        req=row["requests"]; a=[r for r in req if r["tenant"]=="A"]; b=[r for r in req if r["tenant"]=="B"]
        completed+=len(req)
        check(len(a)==1 and len(b)==4 and {r["label"] for r in b}==set("ABCD"),"missing request")
        check(all(r["prompt_tokens"]==548 and len(r["token_ids"])==16 for r in req),"length mismatch")
        check(all(r["released_ns"]==r["completed_ns"] for r in req),"artificial release delay")
        hits=544 if row["condition"]=="warm" else 0
        check(len(a)==1 and a[0]["cached_tokens"]==hits,"actual A cache state mismatch")
        check(all(r["cached_tokens"]==0 for r in b),"B cache hit")
        if a: hit_counts[row["condition"]].append(a[0]["cached_tokens"])
        hit_counts["B"].extend(r["cached_tokens"] for r in b)
        check(row["pools"]["protected_alignment_tokens"]==0,"protected alignment active")
        check({t:v["quota_blocks"] for t,v in row["pools"]["tenants"].items()}=={"A":128,"B":256},"quota mismatch")
    reps=plan["bootstrap_replicates"]; rng=np.random.default_rng(plan["seed"])
    observers=_observer_report(sorted(test,key=lambda r:(r["pair"],r["condition"])),
        models["models"]["direct"],reps,rng,primary=True)
    # Additional requested paired differences; same whole-pair percentile approach.
    differences=[]
    for cold,warm in pairs:
        c,w=test[cold],test[warm]
        if c["status"]!="ok" or w["status"]!="ok": continue
        cf,wf=_features(c)[1],_features(w)[1]; cc,wc=_cost(c),_cost(w)
        differences.append(dict(pair=c["pair"],first_full_B_ms=cf-wf,
            median_B_ms=cc[1]-wc[1],A_ms=cc[0]-wc[0]))
    paired={}
    if differences:
        draws=rng.integers(0,len(differences),(reps,len(differences)))
        for key in ("first_full_B_ms","median_B_ms","A_ms"):
            values=np.array([d[key] for d in differences])
            paired[key]=dict(cold_minus_warm=_stats(values.tolist()),
                nominal_pair_bootstrap_mean95=np.quantile(values[draws].mean(axis=1),[.025,.975]).tolist(),
                positive_pairs=int((values>0).sum()),negative_pairs=int((values<0).sum()))
    failed=sum(r["status"]!="ok" for r in rows)
    reliable=[name for name in ("stump","logistic") if
        observers[name]["pair_bootstrap_ba95"][0]>.5 and observers[name]["pair_bootstrap_auc95"][0]>.5]
    positive=not errors and not any(r["status"]!="ok" for r in test) and bool(reliable) and observers["paired_swap_max_separation_p"]<.05
    decision="C: configuration/technical mismatch" if errors else (
        "A: unprotected signal supported for frozen observers" if positive else
        "B: no convincing unprotected positive control with frozen observers")
    previous=json.loads((OLD/"analysis.json").read_text())
    comparison={"direct":{k:observers[k] for k in ("stump","logistic")}}
    comparison.update({mode:{k:values[k] for k in ("stump","logistic")}
                       for mode,values in previous["observers"].items()})
    result=dict(status="final frozen direct positive control; no general timing guarantee",
        decision=decision,positive_control_pass=positive,reliable_frozen_observers=reliable,
        train_cohorts=24,test_cohorts=48,bootstrap_replicates=reps,
        observers=observers,comparison_existing_policies=comparison,
        paired_test_differences=paired,paired_test_rows=differences,
        paired_difference_missing_pairs=24-len(differences),
        configuration_errors=errors,completed_responses=completed,expected_responses=360,
        missing_successful_responses=360-completed,failed_cohorts=failed,
        failures=[r for r in rows if r["status"]!="ok"],
        overruns="not applicable: direct has no public join/deadline",
        cache_hit_counts=hit_counts,
        inputs_sha256={name:digest(folder/name) for name in ("protocol.json","trials.jsonl","observers.json","test-start.json")},
        reference_analysis_sha256=digest(OLD/"analysis.json"),
        deviations_from_old_gate=plan["differences"]+[
            "fit_direct changes only per-policy cohort count24 instead of pooled72 and loops over direct alone; identical features, preprocessing, tie handling and solver",
            "unchanged _observer_report applied to direct as primary to provide the same joint pair-swap diagnostic",
            "requested cold-minus-warm mean intervals added via5000 whole-pair bootstraps, nominal and descriptive; no cross-policy paired inference"],
        interpretation="Old policies are frozen earlier-session results, not a newly randomized four-policy comparison. A successful direct control does not prove protection; an unsuccessful control leaves C3 an implementation/normalization/cost case study.")
    write_new(folder/"analysis.json",result)
    write_new(folder/"verification.json",dict(source_unchanged_after_freeze=True,
        source_snapshot_hashes_match=True,old_result_files_unchanged=len(plan["prior_results_sha256"]),
        plan_completed=72,observer_checkpoint_precedes_first_test=True,
        configuration_verified=not errors,analysis_sha256=digest(folder/"analysis.json")))
    return result


if __name__=="__main__": print(json.dumps(analyze(Path(sys.argv[1])),indent=2))
