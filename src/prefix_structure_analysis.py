"""Frozen client observers and integrity/mechanism summary for P0/P1 BOS."""

import json
import statistics
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from observer_compare import data, rank1, score


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/prefix-structure-20261103"
OLD = ROOT / "results/document-bos-20261103"
RUNS = (("run1-c0", "c0", 202611031501),
        ("run2-c1", "c1", 202611031501),
        ("run3-c1", "c1", 202611031502),
        ("run4-c0", "c0", 202611031502))
OLD_RUNS = {"c0": ("run1-c0", "run4-c0"), "c1": ("run2-c1", "run3-c1")}


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def fitted(rows, feature):
    x, y = data(rows, feature)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    model.fit(x, y)
    return model


def old_models(config):
    rows = [r for name in OLD_RUNS[config]
            for r in load(OLD / name / "trials.jsonl")
            if r["mode"] == "bos4" and r["warm"]]
    assert len(rows) == 32 and Counter(r["send_order"].index(r["warm"]) for r in rows) == {i: 8 for i in range(4)}
    return {name: fitted(rows, name) for name in ("R2", "T2")}


def med(values):
    return round(statistics.median(values), 3)


def binary_auc(rows):
    pos1 = [r["tblock_ms"] for r in rows if r["position"] == 1]
    later = [r["tblock_ms"] for r in rows if r["position"] != 1]
    test = mannwhitneyu(pos1, later, alternative="greater", method="exact")
    rng = np.random.default_rng(202611031505)
    boot = []
    for _ in range(2000):
        a, b = [], []
        for run in sorted({r["run"] for r in rows}):
            ra = [r["tblock_ms"] for r in rows if r["run"] == run and r["position"] == 1]
            rb = [r["tblock_ms"] for r in rows if r["run"] == run and r["position"] != 1]
            a.extend(rng.choice(ra, len(ra)))
            b.extend(rng.choice(rb, len(rb)))
        aa, bb = np.asarray(a)[:, None], np.asarray(b)[None, :]
        boot.append(float(np.mean((aa > bb) + .5 * (aa == bb))))
    boot.sort()
    return {"n_pos1": len(pos1), "n_later": len(later),
            "auc_position1_later": round(float(test.statistic / (len(pos1) * len(later))), 4),
            "bootstrap95_stratified_by_start": [round(boot[49], 4), round(boot[1949], 4)],
            "one_sided_exact_p": round(float(test.pvalue), 8)}


def assess_run(name, config, seed, models):
    folder = BASE / name
    trials = load(folder / "trials.jsonl")
    proxy = load(folder / "proxy.jsonl")
    assert len(trials) == 36 and len(proxy) == 144
    by_id = {p["request_id"]: p for p in proxy}
    assert len(by_id) == 144 and len({r["group"] for r in trials}) == 36
    assert len({r["salt"] for r in trials}) == 36
    assert {r["case_seed"] for r in trials} == {seed}
    group_rows = []
    result = {"config": config, "seed": seed, "groups": 36, "responses": 144}
    for structure in ("p0", "p1"):
        subset = [r for r in trials if r["structure"] == structure]
        positive = [r for r in subset if r["warm"]]
        assert len(subset) == 18 and len(positive) == 16
        assert Counter(r["send_order"].index(r["warm"]) for r in positive) == {i: 4 for i in range(4)}
        result[structure] = {"positive": 16, "controls": 2, "R1": rank1(positive)}
        for feature in ("R2", "T2"):
            x, y = data(positive, feature)
            result[structure][feature] = score(y, models[config][feature].predict(x))
        for r in subset:
            items = [by_id[r["probes"][label]["request_id"]] for label in r["send_order"]]
            assert r["mode"] == "bos4" and r["output_tokens"] == 16
            assert all(p["group"] == r["group"] and p["mode"] == "bos4"
                       and p["batch_size"] == 4 and p["flush_reason"] == "full" for p in items)
            assert sorted(p["release_position"] for p in items) == [1, 2, 3, 4]
            cache = {}
            waits, backend_durations, client_e2e = [], [], []
            for label in r["send_order"]:
                client = r["probes"][label]
                p = by_id[client["request_id"]]
                assert p["label"] == label and client["http_status"] == 200
                assert client["prompt_tokens"] == 548 and client["completion_tokens"] == 16
                assert client["cached_tokens_reported"] is None and p["cache_details_removed"]
                assert client["sent_ns"] <= p["arrival_ns"] <= p["backend_received_ns"] <= p["release_ns"] <= client["received_ns"]
                cache[label] = p["cached_tokens_reported"] or 0
                waits.append((p["release_ns"] - p["backend_received_ns"]) / 1e6)
                backend_durations.append((p["backend_received_ns"] - p["arrival_ns"]) / 1e6)
                client_e2e.append((client["received_ns"] - client["sent_ns"]) / 1e6)
            if r["warm"]:
                assert cache[r["warm"]] == 544
                if structure == "p0":
                    assert all(cache[label] == 0 for label in r["send_order"] if label != r["warm"])
            elif structure == "p0":
                assert all(value == 0 for value in cache.values())
            first_sent = min(p["sent_ns"] for p in r["probes"].values())
            first_client = min(p["received_ns"] for p in r["probes"].values())
            first_arrival = min(p["arrival_ns"] for p in items)
            row = {"run": name, "config": config, "seed": seed,
                   "structure": structure, "warm": r["warm"],
                   "order": r["send_order"], "position": r["send_order"].index(r["warm"]) + 1 if r["warm"] else None,
                   "cache_by_label": cache,
                   "tblock_ms": (first_client - first_sent) / 1e6,
                   "backend_last_ms": (max(p["backend_received_ns"] for p in items) - first_arrival) / 1e6,
                   "backend_completion_span_ms": (max(p["backend_received_ns"] for p in items) - min(p["backend_received_ns"] for p in items)) / 1e6,
                   "individual_proxy_wait_ms": waits,
                   "individual_client_e2e_ms": client_e2e,
                   "proxy_wait_median_ms": statistics.median(waits),
                   "backend_duration_median_ms": statistics.median(backend_durations),
                   "client_e2e_median_ms": statistics.median(client_e2e)}
            group_rows.append(row)
        positive_rows = [r for r in group_rows if r["run"] == name and r["structure"] == structure and r["warm"]]
        result[structure]["binary_block_close"] = binary_auc(positive_rows)
    return result, trials, group_rows


def paired(rows, config, metric):
    pairs = []
    strata = []
    for name, c, _ in RUNS:
        if c != config:
            continue
        subset = [r for r in rows if r["run"] == name and r["warm"]]
        by_structure = {s: {(r["warm"], tuple(r["order"])): r for r in subset if r["structure"] == s}
                        for s in ("p0", "p1")}
        assert by_structure["p0"].keys() == by_structure["p1"].keys()
        for pos in range(1, 5):
            cell = [by_structure["p1"][key][metric] - by_structure["p0"][key][metric]
                    for key in by_structure["p0"] if key[1].index(key[0]) + 1 == pos]
            assert len(cell) == 4
            pairs.extend(cell)
            strata.append(cell)
    assert len(pairs) == 32
    rng = np.random.default_rng(202611031503 if config == "c0" else 202611031504)
    boot = sorted(statistics.median(v for cell in strata for v in rng.choice(cell, 4))
                  for _ in range(2000))
    return {"median_p1_minus_p0_ms": med(pairs),
            "bootstrap95_stratified_by_start_and_position_ms": [round(boot[49], 3), round(boot[1949], 3)],
            "positive": sum(x > 0 for x in pairs), "negative": sum(x < 0 for x in pairs)}


def cross_start_recalibrated(config, structure, run_trials):
    starts = [name for name, c, _ in RUNS if c == config]
    correct = []
    directions = []
    for train, test in ((starts[0], starts[1]), (starts[1], starts[0])):
        a = [r for r in run_trials[train] if r["structure"] == structure and r["warm"]]
        b = [r for r in run_trials[test] if r["structure"] == structure and r["warm"]]
        for feature in ("R2", "T2"):
            predictor = fitted(a, feature)
            x, y = data(b, feature)
            hits = int(np.sum(predictor.predict(x) == y))
            correct.append((feature, hits))
            directions.append({"train": train, "test": test, "observer": feature, "hits": hits, "n": 16})
    combined = {}
    for feature in ("R2", "T2"):
        hits = sum(v for f, v in correct if f == feature)
        ci = binomtest(hits, 32).proportion_ci(confidence_level=.95, method="wilson")
        combined[feature] = {"hits": hits, "n": 32, "wilson95": [round(ci.low, 4), round(ci.high, 4)]}
    return {"combined": combined,
            "directions": directions}


def main():
    models = {config: old_models(config) for config in ("c0", "c1")}
    sessions, run_trials, rows = {}, {}, []
    for name, config, seed in RUNS:
        sessions[name], run_trials[name], group_rows = assess_run(name, config, seed, models)
        rows.extend(group_rows)
    for left, right in (("run1-c0", "run2-c1"), ("run4-c0", "run3-c1")):
        assert [(r["structure"], r["warm"], r["send_order"]) for r in run_trials[left]] == [
            (r["structure"], r["warm"], r["send_order"]) for r in run_trials[right]]
    aggregate = {}
    for config in ("c0", "c1"):
        aggregate[config] = {"cross_start_recalibrated": {
            structure: cross_start_recalibrated(config, structure, run_trials)
            for structure in ("p0", "p1")}}
        for structure in ("p0", "p1"):
            positive = [r for name, c, _ in RUNS if c == config
                        for r in run_trials[name] if r["structure"] == structure and r["warm"]]
            grp = [r for r in rows if r["config"] == config and r["structure"] == structure]
            pos_grp = [r for r in grp if r["warm"]]
            cold_cache = [r["cache_by_label"][label] for r in pos_grp
                          for label in r["order"] if label != r["warm"]]
            control_cache = [r["cache_by_label"][label] for r in grp if not r["warm"]
                             for label in r["order"]]
            item = {"positive": 32, "controls": 4, "R1": rank1(positive),
                    "binary_block_close": binary_auc(pos_grp),
                    "cold_cached_tokens": dict(sorted(Counter(cold_cache).items())),
                    "control_cached_tokens": dict(sorted(Counter(control_cache).items())),
                    "first_client_block_ms": med([r["tblock_ms"] for r in pos_grp]),
                    "backend_last_ms": med([r["backend_last_ms"] for r in pos_grp]),
                    "backend_completion_span_ms": med([r["backend_completion_span_ms"] for r in pos_grp]),
                    "individual_proxy_wait_median_ms": med([v for r in grp for v in r["individual_proxy_wait_ms"]]),
                    "backend_duration_median_ms": med([r["backend_duration_median_ms"] for r in grp]),
                    "individual_client_e2e_median_ms": med([v for r in grp for v in r["individual_client_e2e_ms"]])}
            for feature in ("R2", "T2"):
                x, y = data(positive, feature)
                item[feature] = score(y, models[config][feature].predict(x))
            aggregate[config][structure] = item
        aggregate[config]["paired_p1_minus_p0"] = {metric: paired(rows, config, metric)
                                                     for metric in ("tblock_ms", "backend_last_ms",
                                                                    "backend_completion_span_ms", "proxy_wait_median_ms",
                                                                    "client_e2e_median_ms")}
        correctness = []
        for name, c, _ in RUNS:
            if c != config:
                continue
            subsets = {s: [r for r in run_trials[name] if r["structure"] == s and r["warm"]]
                       for s in ("p0", "p1")}
            for s in subsets:
                subsets[s] = {(r["warm"], tuple(r["send_order"])): r for r in subsets[s]}
            for key in subsets["p0"]:
                outcomes = []
                for structure in ("p0", "p1"):
                    r = subsets[structure][key]
                    x, y = data([r], "T2")
                    outcomes.append(bool(models[config]["T2"].predict(x)[0] == y[0]))
                correctness.append(tuple(outcomes))
        only_p0 = sum(a and not b for a, b in correctness)
        only_p1 = sum(b and not a for a, b in correctness)
        aggregate[config]["paired_T2"] = {"only_p0_correct": only_p0,
                                           "only_p1_correct": only_p1,
                                           "mcnemar_exact_two_sided_p": round(float(
                                               binomtest(min(only_p0, only_p1), only_p0 + only_p1, .5).pvalue), 6)}
    result = {"protocol": "results/prefix-structure-20261103/protocol.json",
              "training": "Frozen R2/T2 models fitted on prior P0 document BOS runs, 32 positive groups per configuration; no current data",
              "sessions": sessions, "aggregate": aggregate, "group_metrics": rows}
    with (BASE / "analysis.json").open("x") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    for config in ("c0", "c1"):
        print(config, {s: {"T2": aggregate[config][s]["T2"]["hits"],
                           "R2": aggregate[config][s]["R2"]["hits"],
                           "AUC": aggregate[config][s]["binary_block_close"]["auc_position1_later"]}
                       for s in ("p0", "p1")})


if __name__ == "__main__":
    main()
