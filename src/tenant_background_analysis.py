"""Prespecified paired effects and old C2 observer transfer; never fits a model."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import balanced_accuracy_score,roc_auc_score,confusion_matrix

from tenant_scheduler_analysis import client_features,first_time

ROOT=Path(__file__).resolve().parents[1]


def predict(rows,model,feature):
    x=np.array([client_features(r,feature) for r in rows])
    score=((x-np.array(model["mean"]))/np.array(model["scale"]))@np.array(model["coefficient"])+model["intercept"]
    return (score>0).astype(int),score


def summary(values):
    if not values: return None
    a=np.array(values,dtype=float)
    return dict(n=len(a),median=float(np.median(a)),mean=float(a.mean()),minimum=float(a.min()),maximum=float(a.max()))


def analyze(folder):
    from tenant_background_run import digest,write
    plan=json.loads((folder/"protocol.json").read_text())
    models=json.loads((folder/"observers.json").read_text())
    for name,h in plan["source_sha256"].items(): assert digest(ROOT/name)==h,name
    for name,h in plan["artifact_sha256"].items(): assert digest(folder/name)==h,name
    for name,h in plan["prior_results_sha256"].items(): assert digest(ROOT/name)==h,name
    for name,h in plan["installed_sha256"].items(): assert digest(Path(name))==h,name
    rows=[]; audits=[]; errors=[]; records=[]
    for case in plan["cases"]:
        i=case["index"]; run=folder/f"case-{i:02d}"
        state=json.loads((run/"status.json").read_text()); records.append(state)
        if not (run/"trial.json").exists():
            errors.append(dict(index=i,error="missing trial, retained as failed planned case")); continue
        row=json.loads((run/"trial.json").read_text()); rows.append(row); local=[]
        for k in case:
            if row.get(k)!=case[k]: local.append("case plan mismatch: "+k)
        prep=row["preparation"]
        if (prep.get("http_status"),prep.get("prompt_tokens"),prep.get("completion_tokens"),prep.get("cached_tokens_reported"))!=(200,548,1,None): local.append("preparation invalid")
        b=row["probes"]; good_b=len(b)==4 and set(b)==set("ABCD") and all(
            (r.get("http_status"),r.get("prompt_tokens"),r.get("completion_tokens"),r.get("cached_tokens_reported"))==(200,548,16,None) for r in b.values())
        if not good_b: local.append("B response/length/cache or missing/error")
        proxy=[json.loads(s) for s in (run/"proxy.jsonl").read_text().splitlines()] if (run/"proxy.jsonl").exists() else []
        by_id={p.get("request_id"):p for p in proxy}
        if len(proxy)!=4 or len(by_id)!=4: local.append("proxy count")
        for label,r in b.items():
            p=by_id.get(r.get("request_id"),{})
            if (p.get("mode"),p.get("batch_size"),p.get("cached_tokens_reported"),p.get("cache_details_removed"))!=("direct",1,None,True): local.append("B proxy integrity "+label)
        a=row["victim_target"]; condition=row["condition"]
        if condition=="absent":
            if a is not None: local.append("A not absent")
        elif a is None or (a.get("http_status"),a.get("prompt_tokens"),a.get("completion_tokens"),a.get("cached_tokens_reported"))!=(200,548,16,544 if condition=="warm" else None): local.append("A cache/response integrity")
        c=row["background"]; usage=c.get("usage") or {}; events=c.get("token_events",[])
        if (c.get("http_status"),usage.get("prompt_tokens"),usage.get("completion_tokens"))!=(200,548,256): local.append("C inference completion/length")
        if (usage.get("prompt_tokens_details") or {}).get("cached_tokens") not in (None,0): local.append("unexpected C hit")
        audit=dict(index=i,condition=condition,offset_ms=case["victim_offset_ms"],B_valid=good_b,
                   C_token_events=len(events),C_sent_ns=c.get("sent_ns"),C_complete_ns=c.get("received_ns"))
        if good_b and c.get("received_ns") and events:
            t0=min(q["sent_ns"] for q in b.values()); end=max(q["received_ns"] for q in b.values())
            interval=max(0,min(end,c["received_ns"])-max(t0,c["sent_ns"]))/1e6
            during=[e["received_ns"] for e in events if t0<=e["received_ns"]<=end]
            audit.update(C_actual_start_relative_B_ms=(c["sent_ns"]-t0)/1e6,
                C_first_token_relative_B_ms=(events[0]["received_ns"]-t0)/1e6,
                C_last_token_relative_B_ms=(events[-1]["received_ns"]-t0)/1e6,
                C_complete_relative_B_ms=(c["received_ns"]-t0)/1e6,
                C_request_interval_overlap_B_ms=interval,C_token_events_during_B=len(during),
                C_first_progress_during_B_ns=min(during) if during else None,
                C_last_progress_during_B_ns=max(during) if during else None)
            if interval<=0 or not during: local.append("no observed C token progress while B pending")
            if a and a.get("sent_ns") and a.get("received_ns"):
                audit["A_actual_offset_ms"]=(a["sent_ns"]-t0)/1e6
                audit["A_B_interval_overlap_ms"]=max(0,min(end,a["received_ns"])-max(t0,a["sent_ns"]))/1e6
                if audit["A_B_interval_overlap_ms"]<=0: local.append("no A/B request overlap")
        else: local.append("C overlap unverified")
        if not state["backend_ready"] or state["client_returncode"]!=0: local.append("backend/client failure")
        audit["errors"]=local; audits.append(audit)
        errors.extend(dict(index=i,error=e) for e in local)
    primary=[r for r in rows if r["condition"] in ("warm","cold")]
    scorable=[r for r in primary if next(a for a in audits if a["index"]==r["index"])["B_valid"]]
    complete=len(scorable)==48
    deltas=[]; paired=[]
    if complete:
        for pair in range(24):
            r={r["condition"]:r for r in primary if r["pair"]==pair}
            assert set(r)=={"warm","cold"}
            assert r["warm"]["send_order"]==r["cold"]["send_order"]
            assert r["warm"]["victim_offset_ms"]==r["cold"]["victim_offset_ms"]
            delta=first_time(r["cold"])-first_time(r["warm"])
            deltas.append(delta); paired.append(dict(pair=pair,offset_ms=r["warm"]["victim_offset_ms"],cold_minus_warm_ms=delta))
    rng=np.random.default_rng(plan["seed"]); reps=plan["bootstrap_replicates"]
    rq1=dict(complete_pairs=len(deltas),planned_pairs=24,interpretation="effect not equivalent to single-case exploitation")
    rq2={}; effect=False; attack=False
    if complete:
        # Six whole pair blocks per public offset; resample within offset strata.
        strata=[np.array([i for i,p in enumerate(paired) if p["offset_ms"]==offset]) for offset in (0,150,300,450)]
        draws=np.concatenate([rng.choice(s,(reps,6)) for s in strata],axis=1)
        d=np.array(deltas); positive=int((d>0).sum());negative=int((d<0).sum());ties=int((d==0).sum())
        p=float(binomtest(positive,positive+negative,.5,alternative="greater").pvalue) if positive+negative else 1.
        rq1.update(cold_minus_warm_ms=summary(deltas),positive=positive,negative=negative,ties=ties,
            exact_one_sided_sign_p=p,rows=paired,
            stratified_pair_bootstrap_median95=np.quantile(np.median(d[draws],axis=1),[.025,.975]).tolist(),
            stratified_pair_bootstrap_mean95=np.quantile(d[draws].mean(axis=1),[.025,.975]).tolist())
        effect=not errors and p<.05 and rq1["stratified_pair_bootstrap_median95"][0]>0
        ordered=[next(r for r in primary if r["pair"]==pair and r["condition"]==c) for pair in range(24) for c in ("cold","warm")]
        y=np.tile([0,1],24); boot_indices=(2*draws[:,:,None]+np.array([0,1])).reshape(reps,-1)
        for name in ("T1","T2"):
            pred,scores=predict(ordered,models["models"][name],name)
            correct=(pred==y); boot_acc=correct[boot_indices].mean(axis=1)
            cold,warm=scores[::2],scores[1::2]
            kernel=(warm[:,None]>cold[None,:]).astype(float)+.5*(warm[:,None]==cold[None,:])
            counts=np.eye(24)[draws].sum(axis=1)
            boot_auc=np.einsum('bi,ij,bj->b',counts,kernel,counts,optimize=True)/24**2
            rq2[name]=dict(n=48,hits=int(correct.sum()),accuracy=float(correct.mean()),
                balanced_accuracy=float(balanced_accuracy_score(y,pred)),auc=float(roc_auc_score(y,scores)),
                confusion_cold_warm=confusion_matrix(y,pred,labels=[0,1]).tolist(),
                stratified_pair_bootstrap_ba95=np.quantile(boot_acc,[.025,.975]).tolist(),
                stratified_pair_bootstrap_auc95=np.quantile(boot_auc,[.025,.975]).tolist())
        attack=not errors and any(r["stratified_pair_bootstrap_ba95"][0]>.5 and
                    r["stratified_pair_bootstrap_auc95"][0]>.5 for r in rq2.values())
    controls={}
    for condition in ("absent","other_cold"):
        chosen=[r for r in rows if r["condition"]==condition and next(a for a in audits if a["index"]==r["index"])["B_valid"]]
        controls[condition]=dict(planned=8,scorable=len(chosen),first_B_ms=summary([first_time(r) for r in chosen]),observers={})
        if chosen:
            for name in ("T1","T2"):
                pred,scores=predict(chosen,models["models"][name],name)
                controls[condition]["observers"][name]=dict(predicted_warm=int(pred.sum()),predicted_cold=int((1-pred).sum()),
                    predictions_by_case={str(r["index"]):int(v) for r,v in zip(chosen,pred)})
    classification="technical/integrity failure; no robustness conclusion" if errors else (
        "A: paired effect and frozen single-case recognition supported" if effect and attack else
        "B: paired effect supported; frozen single-case recognition not established" if effect else
        "C: robustness not established under fixed load" if not attack else
        "mixed: single-case association but primary paired-effect criterion not met")
    result=dict(status="one fixed C2 background profile; no observer refit",classification=classification,
        RQ1=rq1,RQ2=rq2,controls=controls,effect_supported=effect,recognition_supported=attack,
        specificity="Report absent and other-cold predictions regardless of A/B/C. Other-cold calls are not target-document identification; constant cold calls also invalidate absence inference.",
        integrity=dict(planned_cases=64,recorded_trials=len(rows),backend_ready=sum(r["backend_ready"] for r in records),
            errors=errors,error_count=len(errors),case_audits=audits),
        load_limits="Client request overlap and streaming output progress demonstrate real C inference during B pending windows; neither GPU kernel overlap nor identical realized utilization is measured. Equal public C schedules need not cause equal execution.",
        baseline_unloaded=json.loads((ROOT/"results/tenant-offset-20261103/analysis.json").read_text()),
        input_sha256={str(p.relative_to(folder)):digest(p) for p in sorted(folder.glob('case-*/*.json'))},
        observers_sha256=digest(folder/"observers.json"),protocol_sha256=digest(folder/"protocol.json"))
    write(folder/"analysis.json",result)
    write(folder/"verification.json",dict(sources_and_artifacts_match_freeze=True,
        prior_result_files_unchanged=len(plan["prior_results_sha256"]),installed_backend_unchanged=True,
        all64_planned_case_slots_recorded=len(records)==64,analysis_sha256=digest(folder/"analysis.json")))
    return result


if __name__=="__main__": analyze(Path(sys.argv[1]).resolve())
