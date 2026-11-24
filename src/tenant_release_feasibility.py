"""Exploratory, read-only replay of public release schedules on tenant traces.

No scheduler simulation: recorded backend completions remain fixed. Schedules
are calibrated on old development files only, then frozen for all other files.
Run with the existing scientific Python environment; pass a NEW output folder.
"""

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


ROOT = Path(__file__).resolve().parents[1]
GRID_MS = 10
GAP_MS = 2


def load(folder, single=False):
    path = folder / ("trial.json" if single else "trials.jsonl")
    rows = [json.loads(path.read_text())] if single else [
        json.loads(line) for line in path.read_text().splitlines()]
    proxy_path = folder / "proxy.jsonl"
    proxy = {p["request_id"]: p for p in map(json.loads, proxy_path.read_text().splitlines())}
    out = []
    for row in rows:
        items = [proxy[row["probes"][label]["request_id"]] for label in row["send_order"]]
        anchor = min(p["arrival_ns"] for p in items)
        origin = min(q["sent_ns"] for q in row["probes"].values())
        sends = np.array([(row["probes"][label]["sent_ns"] - origin) / 1e6
                          for label in row["send_order"]])
        arrivals = np.array([(p["arrival_ns"] - anchor) / 1e6 for p in items])
        completions = np.array([(p["backend_received_ns"] - anchor) / 1e6 for p in items])
        observed = np.array([(row["probes"][label]["received_ns"] - origin) / 1e6
                             for label in row["send_order"]])
        assert np.all(completions >= arrivals)
        assert all(row["probes"][label]["http_status"] == 200 for label in row["send_order"])
        victim = row["victim_target"]
        out.append(dict(row=row, anchor_from_send=(anchor-origin)/1e6,
                        sends=sends, arrivals=arrivals, completions=completions,
                        observed=observed, victim_ms=None if victim is None else
                        (victim["received_ns"]-victim["sent_ns"])/1e6,
                        files=[path, proxy_path]))
    return out


def rounded(value):
    return GRID_MS * math.ceil(float(value) / GRID_MS)


def calibrate(rows):
    c = np.array([r["completions"] for r in rows])
    a = np.array([r["arrivals"] for r in rows])
    vector = np.maximum.accumulate([rounded(x) for x in np.max(c, axis=0)])
    # Preserve the public send order and allow the existing 2 ms serialization.
    for k in range(1, 4):
        vector[k] = max(vector[k], vector[k-1] + GAP_MS)
    return dict(group_ms=rounded(c.max()), request_ms=rounded((c-a).max()),
                vector_ms=vector.tolist(), victim_ms=rounded(max(
                    r["victim_ms"] for r in rows if r["victim_ms"] is not None)))


def replay(row, policy, schedule):
    c, a = row["completions"], row["arrivals"]
    if policy == "group":
        due = schedule["group_ms"] + np.arange(4) * GAP_MS
    elif policy == "request":
        due = a + schedule["request_ms"]
    elif policy == "vector":
        due = np.array(schedule["vector_ms"])
    else:
        raise ValueError(policy)
    late = c > due
    # Explicit INSECURE late fallback, retained to expose failures of the slot.
    release = np.maximum(c, due)
    return release + row["anchor_from_send"], release-c, late


def summary(values):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return None
    return dict(n=len(a), mean=float(a.mean()), median=float(np.median(a)),
                p95=float(np.quantile(a, .95)), maximum=float(a.max()))


def features(rows, policy, schedule):
    result = []
    for r in rows:
        times = r["observed"] if policy == "observed" else replay(r, policy, schedule)[0]
        # Complete four receives, own send times, ranks, and first/last receives.
        ranks = np.argsort(np.argsort(times, kind="stable"), kind="stable")
        result.append(np.r_[times, r["sends"], ranks, times.min(), times.max()])
    return np.asarray(result)


def attacks(train, test, policy, schedule):
    train = [r for r in train if r["row"]["condition"] in ("warm", "cold")]
    test = [r for r in test if r["row"]["condition"] in ("warm", "cold")]
    xtr, xte = features(train, policy, schedule), features(test, policy, schedule)
    ytr = np.array([int(r["row"]["condition"] == "warm") for r in train])
    yte = np.array([int(r["row"]["condition"] == "warm") for r in test])
    models = dict(logistic=make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=2000)),
                  rbf=make_pipeline(StandardScaler(), SVC(C=1, gamma="scale")),
                  forest=RandomForestClassifier(n_estimators=200, min_samples_leaf=2,
                                                max_depth=3, random_state=20261103))
    out = {}
    for name, model in models.items():
        model.fit(xtr, ytr)
        score = model.decision_function(xte) if hasattr(model, "decision_function") else model.predict_proba(xte)[:, 1]
        out[name] = dict(balanced_accuracy=float(balanced_accuracy_score(yte, model.predict(xte))),
                         auc=float(roc_auc_score(yte, score)), n=len(yte))
    return out


def evaluate(rows, schedule):
    out = dict(groups=len(rows), observed_B_e2e_ms=summary(np.concatenate([
        r["observed"]-r["sends"] for r in rows])),
        A_unchanged_e2e_ms=summary([r["victim_ms"] for r in rows if r["victim_ms"] is not None]),
        required_group_ms_diagnostic_only=max(float(r["completions"].max()) for r in rows),
        required_request_ms_diagnostic_only=max(float((r["completions"]-r["arrivals"]).max()) for r in rows),
        required_vector_ms_diagnostic_only=np.max([r["completions"] for r in rows], axis=0).tolist(),
        conditions={})
    for policy in ("group", "request", "vector"):
        out[policy] = {}
        for condition in ("all", "warm", "cold", "absent", "other_cold"):
            selected = rows if condition == "all" else [r for r in rows if r["row"]["condition"] == condition]
            if not selected:
                continue
            values = [replay(r, policy, schedule) for r in selected]
            out[policy][condition] = dict(groups=len(selected),
                late_groups=sum(bool(l.any()) for _, _, l in values),
                late_responses=sum(int(l.sum()) for _, _, l in values),
                B_wait_ms=summary(np.concatenate([w for _, w, _ in values])),
                B_e2e_ms=summary(np.concatenate([t-r["sends"] for r,(t,_,_) in zip(selected,values)])),
                A_added_wait_ms=0,
                symmetric_A_wait_ms=summary([max(0,schedule["victim_ms"]-r["victim_ms"])
                                             for r in selected if r["victim_ms"] is not None]))
    return out


def main(output):
    output.mkdir(parents=True, exist_ok=False)
    manifest, results = {}, {}
    base = ROOT / "results/tenant-scheduler-20261103"
    for name, rel in (("fresh_direct", ""), ("fixed_direct", "fixed-direct"),
                      ("fresh_bos", "bos"), ("fixed_bos", "fixed-bos")):
        dev, test = load(base/rel/"dev"), load(base/rel/"holdout")
        schedule = calibrate(dev)
        results[name] = dict(schedule_from_development=schedule,
                            development=evaluate(dev,schedule), old_test=evaluate(test,schedule),
                            attacks={policy:attacks(dev,test,policy,schedule)
                                     for policy in ("observed","group","request","vector")})
        for r in dev+test:
            for p in r["files"]:
                manifest[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
        if name == "fresh_direct":
            offset = sum([load(p, single=True) for p in sorted((ROOT/"results/tenant-offset-20261103").glob("case-*"))], [])
            results["hidden_offset"] = dict(schedule_from_fresh_direct_development=copy.deepcopy(schedule),
                old_test=evaluate(offset,schedule), attacks={policy:attacks(dev,offset,policy,schedule)
                    for policy in ("observed","group","request","vector")})
            for r in offset:
                for p in r["files"]:
                    manifest[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    result = dict(status="exploratory offline replay, no live defense measurements",
                  calibration="each old dev set; hidden-offset uses fresh-direct dev only",
                  grid_ms=GRID_MS, serialization_gap_ms=GAP_MS,
                  late_rule="immediate release at completion: insecure fallback",
                  input_sha256=manifest, results=results)
    (output/"analysis.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:dict(schedule=v.get("schedule_from_development",v.get("schedule_from_fresh_direct_development")),
                            group=v["old_test"]["group"]["all"],vector=v["old_test"]["vector"]["all"])
                      for k,v in results.items()},indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
