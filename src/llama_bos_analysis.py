"""Frozen client observers and integrity summary for Llama BOS development/holdout."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from observer_compare import data, rank1, score


FEATURES = ("R2", "T1", "T2", "RT")


def load(folder):
    trials = [json.loads(s) for s in (folder / "trials.jsonl").read_text().splitlines()]
    proxy = [json.loads(s) for s in (folder / "proxy.jsonl").read_text().splitlines()]
    return trials, proxy


def first_time(row):
    return (min(p["received_ns"] for p in row["probes"].values()) -
            min(p["sent_ns"] for p in row["probes"].values())) / 1e6


def binary_auc(rows, direction):
    positive = [first_time(r) * direction for r in rows if r["send_order"].index(r["warm"]) == 0]
    negative = [first_time(r) * direction for r in rows if r["send_order"].index(r["warm"]) != 0]
    return round(float(mannwhitneyu(positive, negative, alternative="greater").statistic /
                       (len(positive) * len(negative))), 4)


def integrity(trials, proxy):
    lookup = {(p["group"], p["label"]): p for p in proxy}
    failures = []
    if len(proxy) != 4 * len(trials):
        failures.append("proxy response count")
    for r in trials:
        group = [lookup.get((r["group"], label)) for label in r["send_order"]]
        if any(p is None for p in group):
            failures.append(f"{r['group']} missing proxy row")
            continue
        if any(p.get("batch_size") != 4 or p.get("flush_reason") != "full" for p in group):
            failures.append(f"{r['group']} incomplete BOS block")
        if any(not p.get("cache_details_removed") for p in group):
            failures.append(f"{r['group']} cache detail exposed")
        for label, p in zip(r["send_order"], group):
            q = r["probes"][label]
            # vLLM omits the cache detail for a miss; the proxy records None.
            expected = 544 if label == r["warm"] else None
            if p.get("cached_tokens_reported") != expected:
                failures.append(f"{r['group']} {label} cache")
            if (q["http_status"], q["prompt_tokens"], q["completion_tokens"],
                q["cached_tokens_reported"]) != (200, 549, 16, None):
                failures.append(f"{r['group']} {label} response")
            if q["request_id"] != p["request_id"]:
                failures.append(f"{r['group']} {label} ID")
    return {"groups": len(trials), "positive": sum(bool(r["warm"]) for r in trials),
            "controls": sum(not r["warm"] for r in trials), "responses": len(proxy),
            "failures": failures[:30], "failure_count": len(failures)}


def evaluate(root, config):
    dev, dev_proxy = load(root / f"bos-dev-{config}")
    test, test_proxy = load(root / f"bos-test-{config}")
    dev_pos = [r for r in dev if r["warm"]]
    test_pos = [r for r in test if r["warm"]]
    if len(dev_pos) != 16 or len(test_pos) != 32:
        raise ValueError("unexpected development/holdout count")
    dev_auc_plus = binary_auc(dev_pos, 1)
    direction = 1 if dev_auc_plus >= 0.5 else -1
    result = {"development_integrity": integrity(dev, dev_proxy),
              "holdout_integrity": integrity(test, test_proxy),
              "binary_direction": "later" if direction == 1 else "earlier",
              "development_binary_auc": binary_auc(dev_pos, direction),
              "holdout_binary_auc": binary_auc(test_pos, direction),
              "holdout_first_time_median_ms_by_warm_position": {
                  str(pos+1): round(float(np.median([first_time(r) for r in test_pos
                     if r["send_order"].index(r["warm"]) == pos])), 3)
                  for pos in range(4)},
              "R1": rank1(test_pos)}
    for feature in FEATURES:
        xtr, ytr = data(dev_pos, feature)
        xte, yte = data(test_pos, feature)
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        model.fit(xtr, ytr)
        predicted = model.predict(xte)
        result[feature] = score(yte, predicted)
        result[feature]["errors"] = [
            {"trial": r["trial"], "actual": int(y), "predicted": int(p)}
            for r, y, p in zip(test_pos, yte, predicted) if y != p]
    result["holdout_proxy_wait_ms"] = {
        "median": round(float(np.median([p["added_wait_ms"] for p in test_proxy])), 3),
        "p95": round(float(np.quantile([p["added_wait_ms"] for p in test_proxy], .95)), 3)}
    return result


def main(root, output):
    results = {config: evaluate(root, config) for config in ("c0", "c1")}
    output.write_text(json.dumps(results, indent=2) + "\n")
    for config, r in results.items():
        print(config, {f: r[f]["hits"] for f in ("R1",) + FEATURES},
              "AUC", r["holdout_binary_auc"],
              "integrity", r["holdout_integrity"]["failure_count"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
