"""Client-only release-boundary observer; fixed gap rule and small baselines."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from observer_compare import data, rank1, score


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "slot16_dev": "results/bos-slot-20261102/trials-pilot.jsonl",
    "slot16_test": "results/bos-slot-20261102/trials-extended.jsonl",
    "slot24_dev": "results/decision-validation-20261102/slot-fallback/calibration/trials-24.jsonl",
    "slot24_holdout": "results/decision-validation-20261102/slot-fallback/holdout/trials-24.jsonl",
    "slot24_confirm": "results/decision-validation-20261102/slot-fallback/confirm/trials-24.jsonl",
    "new_c0": "results/release-boundary-20261102/c0/trials.jsonl",
    "new_c1": "results/release-boundary-20261102/c1/trials.jsonl",
    "new_cacheoff": "results/release-boundary-20261102/cacheoff/trials.jsonl",
}


def load(name):
    rows = [json.loads(s) for s in (ROOT / FILES[name]).read_text().splitlines()]
    return [r for r in rows if r["mode"] == "slot1050" and r["warm"]]


def boundary(row):
    """Only own send times and complete response receive times enter here."""
    order = row["send_order"]
    t0 = min(row["probes"][label]["sent_ns"] for label in order)
    arrivals = sorted(row["probes"][label]["received_ns"] for label in order)
    gaps = np.diff(arrivals) / 1e6
    largest = float(max(gaps))
    split = int(np.argmax(gaps) + 1) if largest > 10 else 0
    features = [np.log1p(max(g, 0)) for g in gaps] + [split]
    return {"gaps_ms": [round(float(g), 3) for g in gaps],
            "largest_gap_ms": round(largest, 3), "split": split,
            "first_ms": round((arrivals[0] - t0) / 1e6, 3),
            "features": features}


def fit_score(train, test, feature):
    xtr, ytr = data(train, feature)
    xte, yte = data(test, feature)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    model.fit(xtr, ytr)
    return score(yte, model.predict(xte))


def binary_score(y, predicted):
    hits = int(np.sum(y == predicted))
    n = len(y)
    ci = binomtest(hits, n).proportion_ci(method="wilson")
    return {"n": n, "hits": hits, "accuracy": round(hits / n, 4),
            "wilson95": [round(float(ci.low), 4), round(float(ci.high), 4)],
            "chance_p_one_sided": float(binomtest(hits, n, .5,
                                                    alternative="greater").pvalue)}


def binary_baseline(train, test, feature):
    xtr, ytr = data(train, feature)
    xte, yte = data(test, feature)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    model.fit(xtr, (ytr < 2).astype(int))
    return binary_score((yte < 2).astype(int), model.predict(xte))


def evaluate(train_name, test_name):
    train, test = load(train_name), load(test_name)
    ytr = np.array([r["send_order"].index(r["warm"]) for r in train])
    yte = np.array([r["send_order"].index(r["warm"]) for r in test])
    xtr = np.array([boundary(r)["features"] for r in train])
    xte = np.array([boundary(r)["features"] for r in test])
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    model.fit(xtr, ytr)
    predictions = model.predict(xte)
    detected = np.array([boundary(r)["split"] > 0 for r in test])
    binary = binary_score((yte < 2).astype(int), detected.astype(int))
    result = {"train": train_name, "test": test_name, "train_n": len(train),
              "threshold_ms": 10, "boundary_four_class": score(yte, predictions),
              "boundary_early_vs_late": binary,
              "binary_T1": binary_baseline(train, test, "T1"),
              "binary_T2": binary_baseline(train, test, "T2"),
              "binary_RT": binary_baseline(train, test, "RT"),
              "boundary_detected": int(detected.sum()),
              "R1": rank1(test),
              "T1": fit_score(train, test, "T1"),
              "T2": fit_score(train, test, "T2"),
              "RT": fit_score(train, test, "RT"),
              "cases": [{"truth_position": int(yte[i] + 1),
                         "boundary_prediction": int(predictions[i] + 1),
                         "boundary": boundary(r)} for i, r in enumerate(test)]}
    return result


def audit(name):
    path = ROOT / FILES[name]
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    proxy = [json.loads(s) for s in (path.parent / "proxy.jsonl").read_text().splitlines()]
    ids = {x["request_id"]: x for x in proxy}
    assert len(proxy) == len(ids) == 4 * len(rows)
    fallback = 0
    detected = 0
    false_alarm = 0
    missed = 0
    cache_hits = 0
    positions = [0] * 4
    for row in rows:
        assert len(row["probes"]) == 4 and len(set(row["send_order"])) == 4
        assert row["output_tokens"] == 24
        if row["warm"]:
            positions[row["send_order"].index(row["warm"])] += 1
        actual = False
        for label, response in row["probes"].items():
            x = ids[response["request_id"]]
            assert (x["group"], x["label"]) == (row["group"], label)
            assert response["http_status"] == 200
            assert response["prompt_tokens"] == 548 and response["completion_tokens"] == 24
            assert response["cached_tokens_reported"] is None and x["cache_details_removed"]
            assert response["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"]
            assert x["backend_received_ns"] <= x["release_ns"] <= response["received_ns"]
            cache_hits += x["cached_tokens_reported"] == 544
            actual |= x["flush_reason"] == "late_fallback"
        seen = boundary(row)["split"] > 0
        fallback += actual
        detected += seen
        false_alarm += seen and not actual
        missed += actual and not seen
    if name != "new_cacheoff":
        assert cache_hits == sum(bool(r["warm"]) for r in rows)
    else:
        assert cache_hits == 0
    return {"groups": len(rows), "marked_or_positive": sum(bool(r["warm"]) for r in rows),
            "unwarmed": sum(not r["warm"] for r in rows), "responses": len(proxy),
            "positions_1_to_4": positions, "case_seed": list({r["case_seed"] for r in rows}),
            "cache_hits": cache_hits, "fallback_groups": fallback,
            "client_gap_detected": detected, "client_gap_false_alarms": false_alarm,
            "client_gap_missed_fallback": missed}


def main(output):
    results = [evaluate("slot24_dev", "slot24_holdout"),
               evaluate("slot24_dev", "slot24_confirm"),
               evaluate("slot16_dev", "slot16_test"),
               evaluate("slot24_dev", "new_c0"),
               evaluate("slot24_dev", "new_c1"),
               evaluate("slot24_dev", "new_cacheoff")]
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {"comparisons": results,
               "audit": {name: audit(name) for name in ("new_c0", "new_c1", "new_cacheoff")}}
    with output.open("x") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    for r in results:
        print(r["train"], "to", r["test"],
              {k: r[k]["hits"] for k in ("boundary_four_class", "R1", "T1", "T2", "RT")},
              "early/late", r["boundary_early_vs_late"]["hits"], "/", r["boundary_early_vs_late"]["n"],
              "binary T2", r["binary_T2"]["hits"])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
