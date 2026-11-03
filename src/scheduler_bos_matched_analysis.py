"""Frozen matched C0/C1 BOS comparison using only client traces for attacks."""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from c1_cocompletion_analysis import gap_rule
from observer_compare import data, rank1, score


ROOT = Path(__file__).resolve().parents[1]
OLD_C0 = ROOT / "results/bos-pilot-20261102/trials-extended.jsonl"
OLD_C1 = [ROOT / f"results/decision-validation-20261102/config-c1-bos/{name}/trials.jsonl"
          for name in ("dev", "holdout")]


def load(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def training(config):
    if config == "c1":
        rows = [r for path in OLD_C1 for r in load(path) if r["warm"]]
    else:
        candidates = [r for r in load(OLD_C0) if r["mode"] == "bos4" and r["warm"]]
        counts = Counter()
        rows = []
        for r in candidates:
            pos = r["send_order"].index(r["warm"])
            if counts[pos] < 8:
                rows.append(r)
                counts[pos] += 1
    assert len(rows) == 32
    assert Counter(r["send_order"].index(r["warm"]) for r in rows) == {i: 8 for i in range(4)}
    return rows


def auc(values_a, values_b):
    return mannwhitneyu(values_a, values_b, alternative="greater", method="exact").statistic / (len(values_a) * len(values_b))


def evaluate(config, folder):
    trials, proxy = load(folder / "trials.jsonl"), load(folder / "proxy.jsonl")
    assert len(trials) == 36 and len(proxy) == 144
    by_id = {x["request_id"]: x for x in proxy}
    assert len(by_id) == 144 and len({r["group"] for r in trials}) == 36
    positive = [r for r in trials if r["warm"]]
    controls = [r for r in trials if not r["warm"]]
    assert len(positive) == 32 and len(controls) == 4
    assert Counter(r["send_order"].index(r["warm"]) for r in positive) == {i: 8 for i in range(4)}
    assert {r["case_seed"] for r in trials} == {202611030901}
    waits, tblock, backend_last, gap_hits = [], [], [], 0
    for r in trials:
        assert r["mode"] == "bos4" and r["output_tokens"] == 16
        items = [by_id[p["request_id"]] for p in r["probes"].values()]
        assert all(x["group"] == r["group"] and x["batch_size"] == 4
                   and x["flush_reason"] == "full" for x in items)
        assert sorted(x["release_position"] for x in items) == [1, 2, 3, 4]
        anchor = min(x["arrival_ns"] for x in items)
        for label, p in r["probes"].items():
            x = by_id[p["request_id"]]
            assert x["label"] == label and p["http_status"] == 200
            assert p["prompt_tokens"] == 548 and p["completion_tokens"] == 16
            assert p["cached_tokens_reported"] is None and x["cache_details_removed"]
            assert x["cached_tokens_reported"] == (544 if label == r["warm"] else None)
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= p["received_ns"]
            waits.append((x["release_ns"] - x["backend_received_ns"]) / 1e6)
        if r["warm"]:
            pos = r["send_order"].index(r["warm"]) + 1
            first = min(p["received_ns"] for p in r["probes"].values())
            sent = min(p["sent_ns"] for p in r["probes"].values())
            tblock.append({"position": pos, "ms": (first - sent) / 1e6})
            backend_last.append({"position": pos,
                                 "ms": (max(x["backend_received_ns"] for x in items) - anchor) / 1e6})
            gap_hits += gap_rule(r)[0] + 1 == pos
    pos1 = [z["ms"] for z in tblock if z["position"] == 1]
    later = [z["ms"] for z in tblock if z["position"] != 1]
    rng = np.random.default_rng(202611030901)
    boot = sorted(auc(rng.choice(pos1, 8), rng.choice(later, 24)) for _ in range(3000))
    old = training(config)
    result = {"n_positive": 32, "n_controls": 4, "R1": rank1(positive),
              "binary_tblock_auc": round(auc(pos1, later), 4),
              "binary_tblock_auc_bootstrap95": [round(boot[75], 4), round(boot[2924], 4)],
              "binary_tblock_exact_one_sided_p": round(mannwhitneyu(pos1, later, alternative="greater", method="exact").pvalue, 8),
              "tblock_ms_by_position": {str(i): {"median": round(statistics.median(z["ms"] for z in tblock if z["position"] == i), 3),
                                               "min": round(min(z["ms"] for z in tblock if z["position"] == i), 3),
                                               "max": round(max(z["ms"] for z in tblock if z["position"] == i), 3)} for i in range(1, 5)},
              "backend_last_ms_by_position": {str(i): round(statistics.median(z["ms"] for z in backend_last if z["position"] == i), 3) for i in range(1, 5)},
              "individual_proxy_wait_median_ms": round(statistics.median(waits), 3),
              "gap_rule_hits_four_class": gap_hits,
              "old_780ms_binary": {"tp": sum(x >= 780 for x in pos1), "fp": sum(x >= 780 for x in later)}}
    for feature in ("R2", "T1", "T2", "RT"):
        xtr, ytr = data(old, feature)
        xte, yte = data(positive, feature)
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
        model.fit(xtr, ytr)
        result[feature] = score(yte, model.predict(xte))
    return result, [(r["warm"], r["send_order"]) for r in trials]


def main(c0_folder, c1_folder, output):
    c0, sequence0 = evaluate("c0", c0_folder)
    c1, sequence1 = evaluate("c1", c1_folder)
    assert sequence0 == sequence1
    result = {"source": {"c0": str(c0_folder), "c1": str(c1_folder)},
              "paired_case_sequence": True,
              "training": "32 balanced old BOS groups per configuration; separate model per configuration",
              "c0": c0, "c1": c1,
              "four_class_T2_accuracy_difference_c0_minus_c1": round(c0["T2"]["accuracy"] - c1["T2"]["accuracy"], 4)}
    with output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print("C0", {k: c0[k]["hits"] for k in ("R1", "R2", "T1", "T2", "RT")}, "AUC", c0["binary_tblock_auc"])
    print("C1", {k: c1[k]["hits"] for k in ("R1", "R2", "T1", "T2", "RT")}, "AUC", c1["binary_tblock_auc"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
