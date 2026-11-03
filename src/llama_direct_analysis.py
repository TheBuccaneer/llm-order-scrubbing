"""Integrity and frozen client-only observers for the small Llama direct pilot."""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu

from c1_cocompletion_analysis import gap_rule
from observer_compare import rank1, score


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def evaluate(folder):
    trials, proxy = load(folder / "trials.jsonl"), load(folder / "proxy.jsonl")
    assert len(trials) == 20 and len(proxy) == 80
    by_id = {p["request_id"]: p for p in proxy}
    assert len(by_id) == 80 and len({r["group"] for r in trials}) == 20
    positives = [r for r in trials if r["warm"]]
    controls = [r for r in trials if not r["warm"]]
    assert len(positives) == 16 and len(controls) == 4
    assert Counter(r["send_order"].index(r["warm"]) for r in positives) == {i: 4 for i in range(4)}
    guesses, actual, backend_warm_first, control_gap = [], [], 0, 0
    first_times = []
    for r in trials:
        assert r["mode"] == "direct" and r["output_tokens"] == 16
        items = [by_id[p["request_id"]] for p in r["probes"].values()]
        assert all(x["group"] == r["group"] and x["mode"] == "direct"
                   and x["batch_size"] == 1 and x["flush_reason"] == "direct" for x in items)
        for label, p in r["probes"].items():
            x = by_id[p["request_id"]]
            assert x["label"] == label and p["http_status"] == 200
            assert p["prompt_tokens"] == 549 and p["completion_tokens"] == 16
            assert p["cached_tokens_reported"] is None and x["cache_details_removed"]
            assert (x["cached_tokens_reported"] or 0) == (544 if label == r["warm"] else 0)
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= p["received_ns"]
        guess, gaps = gap_rule(r)
        if r["warm"]:
            pos = r["send_order"].index(r["warm"])
            guesses.append(guess)
            actual.append(pos)
            backend_warm_first += min(items, key=lambda x: x["backend_received_ns"])["label"] == r["warm"]
            first_times.append({"position": pos + 1,
                                "ms": (min(p["received_ns"] for p in r["probes"].values()) -
                                       min(p["sent_ns"] for p in r["probes"].values())) / 1e6})
        else:
            control_gap += min(abs(x) for x in gaps) <= 10
    a = [x["ms"] for x in first_times if x["position"] == 1]
    b = [x["ms"] for x in first_times if x["position"] != 1]
    auc = mannwhitneyu(a, b, alternative="two-sided", method="exact").statistic / (len(a) * len(b))
    return {"groups": 20, "positive": 16, "controls": 4, "responses": 80,
            "R1": rank1(positives),
            "frozen_gap_rule": score(np.asarray(actual), np.asarray(guesses)),
            "backend_warm_first": backend_warm_first,
            "controls_with_adjacent_gap_at_most_10ms": control_gap,
            "first_complete_client_auc_position1_vs_later": round(float(auc), 4),
            "first_complete_client_ms_by_position": {str(i): [round(x["ms"], 3) for x in first_times if x["position"] == i]
                                                     for i in range(1, 5)},
            "case_sequence": [(r["warm"], r["send_order"]) for r in trials]}


def main(c0, c1, output):
    a, b = evaluate(c0), evaluate(c1)
    assert a["case_sequence"] == b["case_sequence"]
    guide = any(x["R1"]["hits"] >= 12 or x["frozen_gap_rule"]["hits"] >= 12 for x in (a, b))
    result = {"protocol": "results/llama-reference-20261103/phase-c-protocol.json",
              "c0": a, "c1": b, "decision_guide_met": guide}
    with output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print("C0",a["R1"]["hits"],a["frozen_gap_rule"]["hits"],"C1",b["R1"]["hits"],b["frozen_gap_rule"]["hits"],"guide",guide)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
