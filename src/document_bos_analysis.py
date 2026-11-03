"""Client-only observers and integrity checks for the document crossover pilot."""

import json
import statistics
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from scipy.stats import mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from c1_cocompletion_analysis import gap_rule
from observer_compare import data, rank1, score
from scheduler_bos_matched_analysis import training


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/document-bos-20261103"
RUNS = (("run1-c0", "c0", 202611031101),
        ("run2-c1", "c1", 202611031101),
        ("run3-c1", "c1", 202611031102),
        ("run4-c0", "c0", 202611031102))


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def model(config, feature):
    x, y = data(training(config), feature)
    fitted = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    fitted.fit(x, y)
    return fitted


def assess_run(name, config, seed, models):
    folder = BASE / name
    trials, proxy = load(folder / "trials.jsonl"), load(folder / "proxy.jsonl")
    assert len(trials) == 23 and len(proxy) == 92
    ids = {row["request_id"]: row for row in proxy}
    assert len(ids) == 92 and len({r["group"] for r in trials}) == 23
    assert {r["case_seed"] for r in trials} == {seed}
    bos = [r for r in trials if r["mode"] == "bos4" and r["warm"]]
    direct = [r for r in trials if r["mode"] == "direct" and r["warm"]]
    assert len(bos) == 16 and len(direct) == 4
    assert sum(r["mode"] == "bos4" and not r["warm"] for r in trials) == 2
    assert sum(r["mode"] == "direct" and not r["warm"] for r in trials) == 1
    assert Counter(r["send_order"].index(r["warm"]) for r in bos) == {i: 4 for i in range(4)}
    assert Counter(r["send_order"].index(r["warm"]) for r in direct) == {i: 1 for i in range(4)}
    rows = []
    for r in trials:
        items = [ids[p["request_id"]] for p in r["probes"].values()]
        assert r["output_tokens"] == 16
        assert all(x["group"] == r["group"] and x["mode"] == r["mode"] for x in items)
        if r["mode"] == "bos4":
            assert all(x["batch_size"] == 4 and x["flush_reason"] == "full" for x in items)
            assert sorted(x["release_position"] for x in items) == [1, 2, 3, 4]
        else:
            assert all(x["batch_size"] == 1 and x["flush_reason"] == "direct" for x in items)
        for label, p in r["probes"].items():
            x = ids[p["request_id"]]
            assert p["http_status"] == 200 and p["prompt_tokens"] == 548 and p["completion_tokens"] == 16
            assert p["cached_tokens_reported"] is None and x["cache_details_removed"]
            assert x["label"] == label
            assert x["cached_tokens_reported"] == (544 if label == r["warm"] else None)
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= p["received_ns"]
        if r["warm"]:
            pos = r["send_order"].index(r["warm"]) + 1
            first = min(p["received_ns"] for p in r["probes"].values())
            sent = min(p["sent_ns"] for p in r["probes"].values())
            rows.append({"run": name, "mode": r["mode"], "trial": r["trial"],
                         "seed": seed, "position": pos, "tblock_ms": (first - sent) / 1e6})
    summary = {"config": config, "seed": seed, "groups": 23, "responses": 92,
               "bos": {"n": 16, "R1": rank1(bos)},
               "direct": {"n": 4, "R1": rank1(direct),
                          "existing_gap_rule": gap_score(direct)},
               "bos_proxy_wait_median_ms": round(statistics.median(
                   (ids[p["request_id"]]["release_ns"] - ids[p["request_id"]]["backend_received_ns"]) / 1e6
                   for r in trials if r["mode"] == "bos4" for p in r["probes"].values()), 3)}
    for feature in ("R2", "T1", "T2", "RT"):
        x, y = data(bos, feature)
        summary["bos"][feature] = score(y, models[config][feature].predict(x))
    return summary, bos, direct, rows


def gap_score(rows):
    actual = np.asarray([r["send_order"].index(r["warm"]) for r in rows])
    guesses = np.asarray([gap_rule(r)[0] for r in rows])
    return score(actual, guesses)


def auc(rows):
    a = [r["tblock_ms"] for r in rows if r["position"] == 1]
    b = [r["tblock_ms"] for r in rows if r["position"] != 1]
    return {"n_pos1": len(a), "n_other": len(b),
            "auc": round(mannwhitneyu(a, b, alternative="greater", method="exact").statistic / (len(a)*len(b)), 4),
            "median_pos1_ms": round(statistics.median(a), 3),
            "median_other_ms": round(statistics.median(b), 3)}


def bos_waits(name):
    folder = BASE / name
    trials = load(folder / "trials.jsonl")
    proxy = {r["request_id"]: r for r in load(folder / "proxy.jsonl")}
    return [(proxy[p["request_id"]]["release_ns"] - proxy[p["request_id"]]["backend_received_ns"]) / 1e6
            for r in trials if r["mode"] == "bos4" for p in r["probes"].values()]


def main():
    models = {config: {feature: model(config, feature) for feature in ("R2", "T1", "T2", "RT")}
              for config in ("c0", "c1")}
    sessions, all_bos, all_direct, all_rows = {}, {"c0": [], "c1": []}, {"c0": [], "c1": []}, []
    for name, config, seed in RUNS:
        summary, bos, direct, rows = assess_run(name, config, seed, models)
        sessions[name] = summary
        all_bos[config].extend(bos)
        all_direct[config].extend(direct)
        all_rows.extend(rows)
    for left, right in (("run1-c0", "run2-c1"), ("run4-c0", "run3-c1")):
        a, b = load(BASE / left / "trials.jsonl"), load(BASE / right / "trials.jsonl")
        assert [(r["mode"], r["warm"], r["send_order"]) for r in a] == [
            (r["mode"], r["warm"], r["send_order"]) for r in b]
    paired = []
    for left, right in (("run1-c0", "run2-c1"), ("run4-c0", "run3-c1")):
        a = [r for r in load(BASE / left / "trials.jsonl") if r["mode"] == "bos4" and r["warm"]]
        b = [r for r in load(BASE / right / "trials.jsonl") if r["mode"] == "bos4" and r["warm"]]
        xa, ya = data(a, "T2")
        xb, yb = data(b, "T2")
        assert np.array_equal(ya, yb)
        pa = models["c0"]["T2"].predict(xa) == ya
        pb = models["c1"]["T2"].predict(xb) == yb
        paired.extend(zip(pa.tolist(), pb.tolist()))
    aggregate = {}
    for config in ("c0", "c1"):
        aggregate[config] = {"bos": {"R1": rank1(all_bos[config])},
                             "direct": {"R1": rank1(all_direct[config]),
                                        "existing_gap_rule": gap_score(all_direct[config])}}
        for feature in ("R2", "T1", "T2", "RT"):
            x, y = data(all_bos[config], feature)
            aggregate[config]["bos"][feature] = score(y, models[config][feature].predict(x))
        for name, _, _ in (x for x in RUNS if x[1] == config):
            sessions[name]["bos"]["binary_tblock"] = auc([r for r in all_rows if r["run"] == name and r["mode"] == "bos4"])
        aggregate[config]["bos"]["binary_tblock"] = auc([r for r in all_rows if r["mode"] == "bos4" and r["run"] in [x[0] for x in RUNS if x[1] == config]])
        aggregate[config]["bos"]["proxy_wait_median_ms"] = round(statistics.median(
            wait for name, c, _ in RUNS if c == config for wait in bos_waits(name)), 3)
    hits0 = aggregate["c0"]["bos"]["T2"]["hits"]
    hits1 = aggregate["c1"]["bos"]["T2"]["hits"]
    paired_starts = (sessions["run1-c0"]["bos"]["T2"]["hits"] > sessions["run2-c1"]["bos"]["T2"]["hits"] and
                     sessions["run4-c0"]["bos"]["T2"]["hits"] > sessions["run3-c1"]["bos"]["T2"]["hits"])
    only_c0 = sum(a and not b for a, b in paired)
    only_c1 = sum(b and not a for a, b in paired)
    result = {"protocol": "results/document-bos-20261103/protocol.json",
              "training": "old 32-group synthetic-prompt BOS set per configuration; no document data used for fitting",
              "paired_case_sequences": True, "sessions": sessions, "aggregate": aggregate,
              "paired_T2": {"both_correct": sum(a and b for a, b in paired),
                            "only_c0_correct": only_c0, "only_c1_correct": only_c1,
                            "neither_correct": sum(not a and not b for a, b in paired),
                            "mcnemar_exact_two_sided_p": round(float(binomtest(min(only_c0, only_c1), only_c0 + only_c1, .5).pvalue), 6)},
              "decision_guide_met": hits0 >= 18 and hits1 <= 14 and hits0-hits1 >= 6 and paired_starts}
    output = BASE / "analysis.json"
    with output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print("C0 T2", hits0, "C1 T2", hits1, "guide", result["decision_guide_met"])


if __name__ == "__main__":
    main()
