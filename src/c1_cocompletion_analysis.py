"""Frozen client-only co-completion observer for the new C1 direct run."""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from observer_compare import data, rank1, score


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "results/decision-validation-20261102/config-c1/primary.jsonl"


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def gap_rule(trial):
    order = trial["send_order"]
    times = [trial["probes"][label]["received_ns"] for label in order]
    gaps_ms = [(b - a) / 1e6 for a, b in zip(times, times[1:])]
    closest = min(range(3), key=lambda i: abs(gaps_ms[i]))
    guess = 0 if abs(gaps_ms[closest]) > 10 else closest + 1
    return guess, gaps_ms


def main(trials_path, proxy_path, output_path):
    trials = load(trials_path)
    proxy = load(proxy_path)
    assert len(trials) == 36 and len(proxy) == 144
    by_id = {x["request_id"]: x for x in proxy if "request_id" in x}
    assert len(by_id) == 144
    assert len({x["group"] for x in trials}) == 36
    positive = [x for x in trials if x["warm"]]
    controls = [x for x in trials if not x["warm"]]
    assert len(positive) == 32 and len(controls) == 4
    assert Counter(x["send_order"].index(x["warm"]) for x in positive) == {i: 8 for i in range(4)}
    guesses, actual, gaps, controls_near = [], [], [], 0
    for trial in trials:
        assert trial["mode"] == "direct" and trial["output_tokens"] == 16
        guess, trial_gaps = gap_rule(trial)
        if trial["warm"]:
            guesses.append(guess)
            actual.append(trial["send_order"].index(trial["warm"]))
            gaps.append({"group": trial["group"], "actual_position": actual[-1] + 1,
                         "predicted_position": guess + 1,
                         "adjacent_client_gaps_ms": [round(x, 4) for x in trial_gaps]})
        else:
            controls_near += min(abs(x) for x in trial_gaps) <= 10
        for label, p in trial["probes"].items():
            x = by_id[p["request_id"]]
            assert x["group"] == trial["group"] and x["label"] == label
            assert p["http_status"] == 200 and p["prompt_tokens"] == 548
            assert p["completion_tokens"] == 16 and p["cached_tokens_reported"] is None
            assert x["cache_details_removed"] and x["flush_reason"] == "direct"
            assert x["cached_tokens_reported"] == (544 if label == trial["warm"] else None)
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= p["received_ns"]
    old = [x for x in load(OLD) if x["warm"]]
    result = {
        "source": {"trials": str(trials_path), "proxy": str(proxy_path),
                   "old_training": str(OLD)},
        "groups": len(trials), "positive": len(positive), "controls": len(controls),
        "primary_gap_rule": score(np.asarray(actual), np.asarray(guesses)),
        "controls_with_gap_at_most_10ms": controls_near,
        "R1": rank1(positive),
        "gaps": gaps,
        "closest_gap_ms_by_position": {
            str(pos): {"median": round(statistics.median(
                min(abs(z) for z in row["adjacent_client_gaps_ms"])
                for row in gaps if row["actual_position"] == pos), 4),
                       "max": round(max(min(abs(z) for z in row["adjacent_client_gaps_ms"])
                                        for row in gaps if row["actual_position"] == pos), 4)}
            for pos in range(1, 5)},
    }
    for feature in ("R2", "T2", "RT"):
        xtr, ytr = data(old, feature)
        xte, yte = data(positive, feature)
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
        model.fit(xtr, ytr)
        result[feature] = score(yte, model.predict(xte))
    with output_path.open("x") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print("gap", result["primary_gap_rule"]["hits"], "/32",
          "R1", result["R1"]["hits"], "/32",
          "T2", result["T2"]["hits"], "/32",
          "controls near", controls_near)


if __name__ == "__main__":
    main(*(Path(x) for x in sys.argv[1:4]))
