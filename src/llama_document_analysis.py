"""Exploratory Llama P0/P1 transfer using frozen artificial-prompt observers."""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from llama_bos_analysis import binary_auc, first_time
from observer_compare import data, rank1, score


def load(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def fitted(rows, feature):
    x, y = data(rows, feature)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    model.fit(x, y)
    return model


def evaluate(root, config):
    dev = [r for r in load(root / f"bos-dev-{config}" / "trials.jsonl") if r["warm"]]
    trials = load(root / f"docs-{config}" / "trials.jsonl")
    proxy = load(root / f"docs-{config}" / "proxy.jsonl")
    by_id = {p["request_id"]: p for p in proxy}
    dev_direction = 1 if binary_auc(dev, 1) >= 0.5 else -1
    models = {feature: fitted(dev, feature) for feature in ("R2", "T2")}
    groups = {}
    for r in trials:
        records = [by_id[r["probes"][label]["request_id"]] for label in r["send_order"]]
        groups[r["group"]] = {
            "backend_last_ms": (max(p["backend_received_ns"] for p in records) -
                                min(p["arrival_ns"] for p in records)) / 1e6,
            "client_block_ms": first_time(r),
            "cache": {p["label"]: p["cached_tokens_reported"] or 0 for p in records},
            "waits": [p["added_wait_ms"] for p in records],
        }
    result = {"groups": len(trials), "responses": len(proxy), "structure": {}}
    for structure in ("p0", "p1"):
        subset = [r for r in trials if r["structure"] == structure]
        pos = [r for r in subset if r["warm"]]
        cache = Counter(groups[r["group"]]["cache"][label]
                        for r in subset for label in r["send_order"] if label != r["warm"])
        block = [groups[r["group"]]["client_block_ms"] for r in pos]
        backend = [groups[r["group"]]["backend_last_ms"] for r in pos]
        item = {"positive": len(pos), "controls": len(subset)-len(pos),
                "cold_or_control_cache_tokens": dict(sorted(cache.items())),
                "warm_cache_tokens": dict(sorted(Counter(groups[r["group"]]["cache"][r["warm"]] for r in pos).items())),
                "full_bos_blocks": sum(all(p["batch_size"] == 4 and p["flush_reason"] == "full"
                      for p in (by_id[r["probes"][label]["request_id"]] for label in r["send_order"])) for r in subset),
                "client_block_median_ms": round(float(np.median(block)), 3),
                "backend_last_median_ms": round(float(np.median(backend)), 3),
                "individual_proxy_wait_median_ms": round(float(np.median([v for r in subset for v in groups[r["group"]]["waits"]])), 3),
                "R1": rank1(pos),
                "binary_auc_frozen_direction": binary_auc(pos, dev_direction)}
        for feature, model in models.items():
            x, y = data(pos, feature)
            item[feature] = score(y, model.predict(x))
        result["structure"][structure] = item
    by_structure = {s: {(r["warm"], tuple(r["send_order"])): groups[r["group"]]
                       for r in trials if r["structure"] == s and r["warm"]}
                    for s in ("p0", "p1")}
    assert by_structure["p0"].keys() == by_structure["p1"].keys()
    result["paired_p1_minus_p0_median_ms"] = {
        field: round(float(np.median([by_structure["p1"][key][field] - by_structure["p0"][key][field]
                                      for key in by_structure["p0"]])), 3)
        for field in ("backend_last_ms", "client_block_ms")}
    result["basic_integrity"] = {
        "http200_prompt549_completion16_client_cache_hidden": all(
            q["http_status"] == 200 and q["prompt_tokens"] == 549 and
            q["completion_tokens"] == 16 and q["cached_tokens_reported"] is None
            for r in trials for q in r["probes"].values()),
        "all_full_blocks": all(p["batch_size"] == 4 and p["flush_reason"] == "full" for p in proxy),
        "all_warm544": all(groups[r["group"]]["cache"][r["warm"]] == 544
                           for r in trials if r["warm"]),
    }
    return result


def main(root, output):
    results = {config: evaluate(root, config) for config in ("c0", "c1")}
    output.write_text(json.dumps(results, indent=2) + "\n")
    for config, r in results.items():
        print(config, {s: {f: r["structure"][s][f]["hits"] for f in ("R1", "R2", "T2")}
                       for s in ("p0", "p1")}, r["paired_p1_minus_p0_median_ms"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
