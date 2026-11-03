"""Frozen C1 BOS client-only observers; proxy data are integrity checks only."""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from c1_cocompletion_analysis import gap_rule
from observer_compare import data, rank1, score


ROOT = Path(__file__).resolve().parents[1]
OLD = [ROOT / f"results/decision-validation-20261102/config-c1-bos/{name}/trials.jsonl"
       for name in ("dev", "holdout")]


def load(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def interval(hits, total):
    ci = binomtest(hits, total).proportion_ci(.95, method="wilson")
    return [round(ci.low, 4), round(ci.high, 4)]


def main(trials_path, proxy_path, output_path):
    trials, proxy = load(trials_path), load(proxy_path)
    assert len(trials) == 36 and len(proxy) == 144
    by_id = {x["request_id"]: x for x in proxy}
    assert len(by_id) == 144 and len({x["group"] for x in trials}) == 36
    positive = [x for x in trials if x["warm"]]
    controls = [x for x in trials if not x["warm"]]
    assert len(positive) == 32 and len(controls) == 4
    assert Counter(x["send_order"].index(x["warm"]) for x in positive) == {i: 8 for i in range(4)}
    assert {x["case_seed"] for x in trials} == {202611030531}
    tblock = []
    waits = []
    gap_hits = 0
    gap_values = []
    for trial in trials:
        assert trial["mode"] == "bos4" and trial["output_tokens"] == 16
        items = [by_id[p["request_id"]] for p in trial["probes"].values()]
        assert all(x["group"] == trial["group"] and x["mode"] == "bos4"
                   and x["batch_size"] == 4 and x["flush_reason"] == "full" for x in items)
        assert sorted(x["release_position"] for x in items) == [1, 2, 3, 4]
        for label, p in trial["probes"].items():
            x = by_id[p["request_id"]]
            assert x["label"] == label and p["http_status"] == 200
            assert p["prompt_tokens"] == 548 and p["completion_tokens"] == 16
            assert p["cached_tokens_reported"] is None and x["cache_details_removed"]
            assert x["cached_tokens_reported"] == (544 if label == trial["warm"] else None)
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= p["received_ns"]
            waits.append((x["release_ns"] - x["backend_received_ns"]) / 1e6)
        first = min(p["received_ns"] for p in trial["probes"].values())
        sent = min(p["sent_ns"] for p in trial["probes"].values())
        value = (first - sent) / 1e6
        if trial["warm"]:
            pos = trial["send_order"].index(trial["warm"]) + 1
            guess, gaps = gap_rule(trial)
            gap_hits += guess + 1 == pos
            gap_values.append(min(abs(z) for z in gaps))
            tblock.append({"group": trial["group"], "warm_position": pos,
                           "first_complete_client_ms": round(value, 4),
                           "binary_prediction_position_1": value >= 780})
    pos1 = [x["first_complete_client_ms"] for x in tblock if x["warm_position"] == 1]
    later = [x["first_complete_client_ms"] for x in tblock if x["warm_position"] != 1]
    tp = sum(x >= 780 for x in pos1)
    fp = sum(x >= 780 for x in later)
    test = mannwhitneyu(pos1, later, alternative="greater", method="exact")
    old = [row for path in OLD for row in load(path) if row["warm"]]
    result = {"source": {"trials": str(trials_path), "proxy": str(proxy_path),
                         "training": [str(p) for p in OLD]},
              "groups": 36, "positive": 32, "controls": 4,
              "primary_binary": {"threshold_ms": 780, "tp": tp, "fn": 8 - tp,
                                 "fp": fp, "tn": 24 - fp,
                                 "sensitivity": round(tp / 8, 4),
                                 "sensitivity_wilson95": interval(tp, 8),
                                 "specificity": round((24 - fp) / 24, 4),
                                 "specificity_wilson95": interval(24 - fp, 24),
                                 "balanced_accuracy": round((tp / 8 + (24 - fp) / 24) / 2, 4),
                                 "auc": round(test.statistic / (8 * 24), 4),
                                 "mann_whitney_one_sided_p": round(test.pvalue, 8)},
              "binary_cases": tblock,
              "control_first_complete_client_ms": [round((min(p["received_ns"] for p in x["probes"].values()) - min(p["sent_ns"] for p in x["probes"].values())) / 1e6, 4) for x in controls],
              "gap_rule_hits_four_class": gap_hits,
              "smallest_client_gap_ms": {"median": round(statistics.median(gap_values), 4),
                                         "min": round(min(gap_values), 4), "max": round(max(gap_values), 4)},
              "individual_proxy_wait_ms": {"median": round(statistics.median(waits), 3),
                                            "max": round(max(waits), 3)},
              "R1": rank1(positive)}
    for feature in ("R2", "T1", "T2", "RT"):
        xtr, ytr = data(old, feature)
        xte, yte = data(positive, feature)
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
        model.fit(xtr, ytr)
        result[feature] = score(yte, model.predict(xte))
    with output_path.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print("binary", tp, "/8 TP", fp, "/24 FP; four-class",
          {k: result[k]["hits"] for k in ("R1", "R2", "T1", "T2", "RT")})


if __name__ == "__main__":
    main(*(Path(x) for x in sys.argv[1:4]))
