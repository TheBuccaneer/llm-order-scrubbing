"""Frozen train-only observers and paired contribution gate for block512.

No GPU use, no test-time refitting, no test-time direction selection.
``fit_observers(rows)`` is called before test acquisition; ``analyze``
uses only the persisted numeric models and writes a new analysis.json.
"""

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import beta, rankdata
from sklearn import __version__ as sklearn_version
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler

from protected_prefill_analysis import canonical


MODES = ("protected_block512", "ignore_hits", "release1240")
PROTECTED = MODES[0]


def _hash(rows):
    ordered = sorted(rows, key=lambda r:(r["split"], r["pair"], r["mode"], r["condition"], r["trial"]))
    raw = json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _features(row):
    failure = row["status"] != "ok"
    if failure:
        if row["status"] != "contract_failure":
            raise ValueError(f"Unknown outcome status {row['status']}")
        items = row["failure"]["submitted"]
        end = row["failure"]["observed_failure_ns"]
    else:
        items, end = row["requests"], None
    b = {r["label"]:r for r in items if r["tenant"] == "B"}
    if set(b) != set("ABCD") or sum(r["tenant"] == "B" for r in items) != 4:
        raise ValueError("Every outcome, including failure, requires all four submitted B labels")
    times = [((end if failure else b[label]["released_ns"])-b[label]["sent_ns"])/1e6 for label in "ABCD"]
    first = ((end if failure else min(r["released_ns"] for r in b.values()))-
             min(r["sent_ns"] for r in b.values()))/1e6
    x = np.array(times+[float(failure)], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(first) or np.any(x < 0) or first < 0:
        raise ValueError("Invalid observable client/error time")
    return x, float(first)


def fit_observers(rows):
    if len(rows) != 72 or any(r["split"] != "train" for r in rows):
        raise ValueError("Fit requires exactly all 72 training cohorts and no test cohort")
    result = dict(train_sha256=_hash(rows), train_cohorts=len(rows), sklearn_version=sklearn_version,
        features="B A/B/C/D own released-minus-sent milliseconds plus failure bit; no A/backend/cache fields",
        stump_feature="min(B released_ns)-min(B sent_ns); failure observed_failure_ns-min(B sent_ns)",
        threshold_tie="direction -1 before +1; ascending train midpoints; first maximum retained",
        models={})
    for mode in MODES:
        chosen = sorted((r for r in rows if r["mode"] == mode), key=lambda r:(r["pair"], r["condition"]))
        _pair_indices(chosen, expected=12)
        x, first = zip(*[_features(r) for r in chosen])
        x, first = np.array(x), np.array(first)
        y = np.array([int(r["condition"] == "warm") for r in chosen])
        unique = np.unique(first)
        thresholds = np.r_[unique[0]-1, (unique[:-1]+unique[1:])/2, unique[-1]+1]
        best = None
        for direction in (-1, 1):
            for threshold in thresholds:
                pred = direction*(first-threshold) >= 0
                ba = float(balanced_accuracy_score(y, pred))
                if best is None or ba > best["train_balanced_accuracy"]:
                    best = dict(direction=direction, threshold_ms=float(threshold), train_balanced_accuracy=ba)
        scaler = StandardScaler().fit(x)
        model = LogisticRegression(C=1, solver="lbfgs", max_iter=1000).fit(scaler.transform(x), y)
        result["models"][mode] = dict(stump=best,
            logistic=dict(mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
                          coefficient=model.coef_[0].tolist(), intercept=float(model.intercept_[0]),
                          classes=model.classes_.tolist(), C=1, solver="lbfgs", max_iter=1000),
            train_sha256=_hash(chosen), train_cohorts=len(chosen))
    return result


def _predict(rows, model):
    x, first = zip(*[_features(r) for r in rows])
    x, first = np.array(x), np.array(first)
    stump = model["stump"]
    stump_score = stump["direction"]*(first-stump["threshold_ms"])
    logistic = model["logistic"]
    score = ((x-np.array(logistic["mean"]))/np.array(logistic["scale"])) @ np.array(logistic["coefficient"]) + logistic["intercept"]
    # sklearn's binary decision rule uses >0; the explicit stump uses >=0.
    return np.column_stack((stump_score >= 0, score > 0)).astype(int), np.column_stack((stump_score, score))


def _pair_indices(rows, expected):
    pairs = {}
    for i, row in enumerate(rows):
        if row["condition"] not in ("cold", "warm"):
            raise ValueError("Unknown secret condition")
        conditions = pairs.setdefault(row["pair"], {})
        if row["condition"] in conditions:
            raise ValueError("Duplicate cohort in a warm/cold pair")
        conditions[row["condition"]] = i
    if len(pairs) != expected or any(set(p) != {"cold", "warm"} for p in pairs.values()):
        raise ValueError(f"Expected {expected} complete warm/cold pair blocks")
    return np.array([[pairs[p][c] for c in ("cold", "warm")] for p in sorted(pairs)])


def _observer_report(rows, model, reps, rng, primary=False):
    pairs = _pair_indices(rows, expected=24)
    pred, scores = _predict(rows, model)
    y = np.array([int(r["condition"] == "warm") for r in rows])
    correct = (pred == y[:, None])
    ba = correct.mean(axis=0)  # Every resampled block has one row of each class.
    draws = rng.integers(0, len(pairs), (reps, len(pairs)))
    boot_ba = correct[pairs].mean(axis=1)[draws].mean(axis=1)
    auc=np.array([roc_auc_score(y,scores[:,j]) for j in range(2)])
    cold,warm=scores[pairs[:,0]],scores[pairs[:,1]]
    kernel=(warm[:,None,:]>cold[None,:,:]).astype(float)+.5*(warm[:,None,:]==cold[None,:,:])
    counts=np.eye(len(pairs),dtype=int)[draws].sum(axis=1)
    boot_auc=np.einsum("bi,ijm,bj->bm",counts,kernel,counts,optimize=True)/len(pairs)**2
    separation=max(float(np.abs(ba-.5).max()),float(np.abs(auc-.5).max()))
    boot_separation=np.maximum(np.abs(boot_ba-.5).max(axis=1),np.abs(boot_auc-.5).max(axis=1))
    out = {name:dict(balanced_accuracy=float(ba[j]), auc=float(roc_auc_score(y, scores[:,j])),
                    confusion_cold_warm=confusion_matrix(y,pred[:,j],labels=[0,1]).tolist(),
                    n=len(rows), pair_bootstrap_ba95=np.quantile(boot_ba[:,j],[.025,.975]).tolist(),
                    pair_bootstrap_auc95=np.quantile(boot_auc[:,j],[.025,.975]).tolist())
           for j,name in enumerate(("stump", "logistic"))}
    out["max_balanced_accuracy"] = float(ba.max())
    out["max_ba_one_sided95_upper"] = float(np.quantile(boot_ba.max(axis=1), .95))
    out["max_absolute_BA_or_AUC_distance_from_chance"]=separation
    out["max_separation_one_sided95_upper"]=float(np.quantile(boot_separation,.95))
    if primary:
        swaps = rng.integers(0,2,(reps,len(pairs)))
        perm_labels = np.stack((swaps,1-swaps),axis=2)
        perm_ba = (pred[pairs][None,:,:,:] == perm_labels[:,:,:,None]).mean(axis=(1,2))
        ranks=rankdata(scores[pairs.reshape(-1)],axis=0)
        perm_auc=(perm_labels.reshape(reps,-1)@ranks-len(pairs)*(len(pairs)+1)/2)/len(pairs)**2
        perm_separation=np.maximum(np.abs(perm_ba-.5).max(axis=1),np.abs(perm_auc-.5).max(axis=1))
        p = (1+np.count_nonzero(perm_separation >= separation-1e-12))/(reps+1)
        out["paired_swap_max_separation_p"] = float(p)
        out["permutation"] = "Monte Carlo pair-label swaps; max absolute distance from chance across BA/AUC of two frozen observers; no prediction/score flip; +1 correction"
    return out


def _stats(values):
    if not values:
        return None
    a=np.asarray(values,dtype=float)
    return dict(n=len(a),mean=float(a.mean()),median=float(np.median(a)),minimum=float(a.min()),maximum=float(a.max()))


def _cost(row):
    if row["status"] != "ok":
        return None
    requests=row["requests"]
    a=[r for r in requests if r["tenant"]=="A"]
    b=[r for r in requests if r["tenant"]=="B"]
    if len(a)!=1 or len(b)!=4:
        raise ValueError("Cost cohort must contain one A and four B requests")
    duration=lambda r:(r["released_ns"]-r["sent_ns"])/1e6
    cuda=row.get("inference_cuda_intervals_ms")
    if row["mode"]==PROTECTED:
        copy=row["protected"]["normalization_result"].get("cuda_copy_interval_ms")
        cuda=None if cuda is None or copy is None else cuda+copy
    return [float(duration(a[0])),float(np.median([duration(r) for r in b])),
            None if cuda is None else float(cuda)]


def _cost_report(test, reps, rng):
    warm={(r["mode"],r["pair"]):r for r in test if r["condition"]=="warm"}
    pair_ids=sorted({r["pair"] for r in test})
    differences=[]; missing=[]
    for pair in pair_ids:
        left,right=warm[("ignore_hits",pair)],warm[(PROTECTED,pair)]
        lc,rc=_cost(left),_cost(right)
        if lc is None or rc is None:
            missing.append(pair)
            continue
        differences.append([None if a is None or b is None else a-b for a,b in zip(lc,rc)])
    out=dict(comparison="warm test matched pairs: ignore_hits minus protected_block512",
             unit="whole public pair block; B endpoint is within-cohort median own duration",
             statistic="mean of paired improvements; positive favors protected",
             missing_failure_pair_ids=missing, completed_only_pairs=len(differences), endpoints={},
             latency_pass=False,compute_pass=False,status="inconclusive" if missing else "evaluated")
    draws=rng.integers(0,len(pair_ids),(reps,len(pair_ids)))
    # A missing required pair is not replaced by success-only inference.
    for j,name in enumerate(("A_e2e_ms","B_cohort_median_e2e_ms","CUDA_inference_plus_copy_ms")):
        values=[d[j] for d in differences if d[j] is not None]
        endpoint=dict(completed_only_difference_ms=_stats(values), lower_simultaneous95=None)
        if not missing and len(values)==len(pair_ids):
            boot=np.array(values)[draws].mean(axis=1)
            endpoint["lower_simultaneous95"]=float(np.quantile(boot,.05/3))
        out["endpoints"][name]=endpoint
    lower=lambda n:out["endpoints"][n]["lower_simultaneous95"]
    out["latency_pass"]=all(lower(n) is not None and lower(n)>0 for n in ("A_e2e_ms","B_cohort_median_e2e_ms"))
    out["compute_pass"]=lower("CUDA_inference_plus_copy_ms") is not None and lower("CUDA_inference_plus_copy_ms")>0
    out["multiplicity"]="Bonferroni lower percentile alpha=.05/3 across the three preregistered endpoints"
    return out


def _phase_checks(rows):
    errors=[]; reference=None
    for row in rows:
        if row["mode"]!=PROTECTED or row.get("status","ok")!="ok":
            continue
        tag=str(row.get("trial",f"functional-{row.get('engine_generation')}"))
        p=row["protected"]; state=p["join_snapshot"]
        def check(ok,message):
            if not ok:errors.append(dict(trial=tag,error=message))
        check(p["joined"] and p["physical_normalizer_applied"],"missing physical join")
        check(not state["waiting"] and not state["inflight"] and not state["prev_step"],"noncanonical queues/inflight/previous-step state")
        check(state["scheduled_token_budget"]==2048 and state["prefill_chunk_threshold"]==512,"shared scheduler limits differ from frozen 2048/512")
        check(len(state["requests"])==5 and all(r["computed_tokens"]==548 and r["output_tokens"]==1 and r["total_logical_tokens"]==549
            and not r["preemptions"] and not r["output_placeholders"] and not r["speculative_tokens"] and not r["external_computed_tokens"]
            for r in state["requests"]),"wrong canonical logical frontier")
        events=p["trace"]
        config=next(e for e in events if e["event"]=="configure")
        join=next(e for e in events if e["event"]=="join")
        normal=next(e for e in events if e["event"]=="normalization_end")
        check(join["elapsed_ms"]>=config["join_ms"] and normal["elapsed_ms"]<=config["join_ms"],"public join/normalization deadline violated")
        steps=[e for e in events if e["event"]=="schedule"]
        check(all(all(rid.startswith(step["owner"]+":") for rid in step["scheduled_tokens"])
                  for step in steps if step["phase"]=="prefill"),"foreign protected execution")
        shared=[e for e in steps if e["phase"]=="shared_decode"]
        check(len(shared)==15 and all(len(e["scheduled_tokens"])==5 and set(e["scheduled_tokens"].values())=={1} for e in shared),"shared decode shape differs")
        check(bool(shared) and len(shared[0]["remapped_ids"])==5,"missing first shared remap")
        a=[r for r in row["requests"] if r["tenant"]=="A"]
        check(len(a)==1 and a[0]["cached_tokens"]==(512 if row["condition"]=="warm" else 0),"wrong actual A reuse")
        check(all(r["prompt_tokens"]==548 and len(r["token_ids"])==16 and not(r["tenant"]=="B" and r["cached_tokens"])
                  for r in row["requests"]),"response shape/B cache isolation failed")
        current=canonical(row)
        check(reference is None or current==reference,"normalized allocator metadata differs")
        reference=current if reference is None else reference
        tenants=current["tenants"]
        check(tenants["A"]["quota_blocks"]==128 and tenants["B"]["quota_blocks"]==256
              and tenants["A"]["free_blocks"]==92 and tenants["B"]["free_blocks"]==112,"fixed quota/reservation failed")
    return errors


def _functional_report(folder, generations):
    path=folder/"functional-checks.jsonl"
    if not path.exists():return dict(verified=False,errors=["functional-checks.jsonl missing"])
    rows=[json.loads(s) for s in path.read_text().splitlines()]
    errors=_phase_checks(rows)
    groups={}
    for row in rows:groups.setdefault(row["engine_generation"],[]).append(row)
    for generation in sorted(generations):
        pair=groups.get(generation,[])
        if len(pair)!=2 or {r["condition"] for r in pair}!={"cold","warm"}:
            errors.append(dict(generation=generation,error="missing fixed functional cold/warm pair"));continue
        hashes=[r["protected"]["normalization_result"].get("canonical_kv_sha256") for r in pair]
        layers=[r["protected"]["normalization_result"].get("layers") for r in pair]
        tokens=[{(r["tenant"],r["label"]):r["token_ids"] for r in row["requests"]} for row in pair]
        if not all(hashes) or hashes[0]!=hashes[1] or layers!=[28,28] or tokens[0]!=tokens[1] or len(tokens[0])!=5:
            errors.append(dict(generation=generation,error="all-layer payload hash/all-five-token functional equality failed"))
    return dict(verified=bool(groups) and not errors,errors=errors,engine_generations=len(groups),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def analyze(folder):
    folder=Path(folder)
    protocol=json.loads((folder/"protocol.json").read_text())
    reps=int(protocol["bootstrap_replicates"]); seed=int(protocol["seed"])
    limit=float(protocol["leakage_ba_limit"])
    rows=[json.loads(s) for s in (folder/"trials.jsonl").read_text().splitlines()]
    if len(rows)!=216 or any(r["split"]!="train" for r in rows[:72]) or any(r["split"]!="test" for r in rows[72:]):
        raise ValueError("Expected all 72 train cohorts followed by 144 test cohorts, including failures")
    models_path=folder/"observers.json"
    models=json.loads(models_path.read_text())
    fence=json.loads((folder/"test-start.json").read_text())
    if fence["observers_sha256"]!=hashlib.sha256(models_path.read_bytes()).hexdigest() or models["train_sha256"]!=_hash(rows[:72]):
        raise ValueError("Observer checkpoint/training hash mismatch")
    test=rows[72:]; rng=np.random.default_rng(seed)
    first_test=test[0]
    first_submitted=(first_test["requests"] if first_test["status"]=="ok" else first_test["failure"]["submitted"])
    if fence["perf_counter_ns"]>=min(r["sent_ns"] for r in first_submitted):
        raise ValueError("Observer freeze did not precede the first test request")
    configuration_errors=[]
    expected_settings=dict(chunk_tokens=512,token_budget=2048,worker_buffer_tokens=2048,preparation_chunk_tokens=512)
    for row in rows:
        if row["status"]!="ok":continue
        if row["scheduler_settings"]!=expected_settings:
            configuration_errors.append(dict(trial=row["trial"],error="scheduler configuration mismatch"))
        if any(s["scheduled_tokens"]>2048 or any(n>512 for n in s["tokens"].values()) for s in row["steps"]):
            configuration_errors.append(dict(trial=row["trial"],error="actual scheduled work exceeds common limits"))
        a=next(r for r in row["requests"] if r["tenant"]=="A")
        expected_hit=(512 if row["mode"]==PROTECTED else 544) if row["condition"]=="warm" and row["mode"]!="ignore_hits" else 0
        if a["cached_tokens"]!=expected_hit or any(r["cached_tokens"] for r in row["requests"] if r["tenant"]=="B"):
            configuration_errors.append(dict(trial=row["trial"],error="actual cache reuse differs from declared policy"))
    observers={}
    descriptive={}
    for mode in MODES:
        selected=[r for r in rows if r["mode"]==mode]
        if len(selected)!=72:raise ValueError("Expected 72 measured outcomes per policy")
        chosen=sorted((r for r in test if r["mode"]==mode),key=lambda r:(r["pair"],r["condition"]))
        observers[mode]=_observer_report(chosen,models["models"][mode],reps,rng,primary=mode==PROTECTED)
        descriptive[mode]={}
        for condition in ("cold","warm"):
            chosen=[r for r in test if r["mode"]==mode and r["condition"]==condition]
            costs=[_cost(r) for r in chosen if r["status"]=="ok"]
            descriptive[mode][condition]=dict(cohorts=len(chosen),failures=sum(r["status"]!="ok" for r in chosen),
                B_observed_own_ms=_stats([float(x) for r in chosen for x in _features(r)[0][:4]]),
                completed_only_A_e2e_ms=_stats([c[0] for c in costs]),
                completed_only_B_cohort_median_e2e_ms=_stats([c[1] for c in costs]),
                completed_only_CUDA_inference_plus_copy_ms=_stats([c[2] for c in costs if c[2] is not None]))
    phase_errors=_phase_checks(rows)
    functional=_functional_report(folder,{r["engine_generation"] for r in rows})
    protected=[r for r in rows if r["mode"]==PROTECTED]
    blocks={}
    for row in protected:blocks.setdefault((row["split"],row["pair"]),[]).append(row)
    if len(blocks)!=36 or any(len(block)!=2 for block in blocks.values()):
        raise ValueError("Expected all 36 protected warm/cold pairs")
    failed_pairs=sum(any(r["status"]!="ok" for r in block) for block in blocks.values())
    failures=sum(r["status"]!="ok" for r in protected)
    upper=1. if failed_pairs==36 else float(beta.ppf(.95,failed_pairs+1,36-failed_pairs))
    overrun=dict(failed_cohorts=failures,cohorts=72,failure_fraction=failures/72,
                 pairs_with_any_failure=failed_pairs,pairs=36,pair_failure_one_sided95_upper=upper,
                 passed=failures/72<=.05 and upper<.10)
    privacy=observers[PROTECTED]
    leakage_pass=privacy["paired_swap_max_separation_p"]>.05 and privacy["max_separation_one_sided95_upper"]<limit-.5
    cost=_cost_report(test,reps,rng)
    normalizer_verified=functional["verified"] and not phase_errors
    gates=dict(normalizer_verified=normalizer_verified,leakage_pass=leakage_pass,
               configuration_verified=not configuration_errors,
               overrun_pass=overrun["passed"],latency_pass=cost["latency_pass"],compute_pass=cost["compute_pass"])
    gates["combined_pass"]=normalizer_verified and not configuration_errors and leakage_pass and overrun["passed"] and (cost["latency_pass"] or cost["compute_pass"])
    result=dict(status="frozen configuration-controlled pilot gate; no general security or novelty guarantee",
        limitations="Leakage gate applies only to two frozen observers and this workload; pair-bootstrap and binomial assumptions do not establish hardware noninterference. CUDA intervals are not energy.",
        train_cohorts=72,test_cohorts=144,seed=seed,bootstrap_replicates=reps,
        input_sha256=hashlib.sha256((folder/"trials.jsonl").read_bytes()).hexdigest(),
        observers_sha256=hashlib.sha256(models_path.read_bytes()).hexdigest(),train_sha256=models["train_sha256"],
        observers=observers,descriptive_test_costs=descriptive,cost_comparison=cost,
        overruns=overrun,functional_checks=functional,phase_check_errors=phase_errors,
        configuration_errors=configuration_errors,gates=gates)
    with (folder/"analysis.json").open("x") as fp:json.dump(result,fp,indent=2);fp.write("\n")
    return result


if __name__=="__main__":
    print(json.dumps(analyze(Path(sys.argv[1])),indent=2))
