"""Paired, idealized replay of causal four-response release policies.

Uses recorded proxy arrival/completion times. Client times below are modeled:
release time plus 2 ms per serial response, with no network or timer jitter.
This is a policy screening tool, not a live security measurement.
"""

import hashlib
import json
import math
import random
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
SOURCES = {
    "development_a": ROOT / "results/decision-validation-20261102/slot-fallback/holdout",
    "development_b": ROOT / "results/decision-validation-20261102/slot-fallback/confirm",
    "holdout": ROOT / "results/release-boundary-20261102/c0",
}
MODES = ("bos4", "slot1050", "slot1160", "slot1200", "periodic100", "defer100")
MS = 1_000_000


def summary(values):
    ordered = sorted(values)
    return {"n": len(values), "median": round(statistics.median(values), 3),
            "p95": round(ordered[math.ceil(.95 * len(ordered)) - 1], 3),
            "max": round(ordered[-1], 3)}


def read_source(name, folder):
    filename = "trials.jsonl" if name == "holdout" else "trials-24.jsonl"
    trials = [json.loads(s) for s in (folder / filename).read_text().splitlines()]
    proxy = [json.loads(s) for s in (folder / "proxy.jsonl").read_text().splitlines()]
    by_id = {x["request_id"]: x for x in proxy}
    assert len(by_id) == len(proxy) == 4 * len(trials)
    out = []
    for trial in trials:
        assert trial["output_tokens"] == 24 and trial["warm"] in (*"ABCD", None)
        items = {label: by_id[p["request_id"]] for label, p in trial["probes"].items()}
        assert set(items) == set("ABCD")
        assert all(x["group"] == trial["group"] for x in items.values())
        assert all(trial["probes"][label]["received_ns"] >= x["release_ns"] >=
                   x["backend_received_ns"] >= x["arrival_ns"]
                   for label, x in items.items())
        out.append((trial, items))
    return out


def ceil_tick(value, period):
    return ((value + period - 1) // period) * period


def schedule(mode, items):
    """Return label -> release time; depends only on public arrival and readiness.

    The implementation would schedule the tick at arrival, then test readiness
    at each tick. max(completion) is used here only to replay those decisions.
    """
    anchor = min(x["arrival_ns"] for x in items.values())
    completion = {label: x["backend_received_ns"] for label, x in items.items()}
    last = max(completion.values())
    if mode == "bos4":
        return {label: last for label in items}
    if mode in ("slot1050", "slot1160", "slot1200"):
        tick = anchor + int(mode[4:]) * MS
        return {label: tick if ready <= tick else ready
                for label, ready in completion.items()}
    if mode == "periodic100":
        tick = ceil_tick(last, 100 * MS)
        return {label: tick for label in items}
    if mode == "defer100":
        first = anchor + 1050 * MS
        tick = first + ceil_tick(max(0, last - first), 100 * MS)
        return {label: tick for label in items}
    raise ValueError(mode)


def modeled_trial(trial, items, mode):
    release = schedule(mode, items)
    # One independent, fixed permutation per group. A partial slot batch is
    # permuted in the same order; late responses follow completion order.
    seed = int.from_bytes(hashlib.sha256(trial["group"].encode()).digest()[:8], "big")
    permutation = list("ABCD")
    random.Random(seed).shuffle(permutation)
    order = sorted(permutation, key=lambda label: (release[label], permutation.index(label)))
    position = Counter()
    row = dict(trial)
    row["probes"] = {label: dict(p) for label, p in trial["probes"].items()}
    for label in order:
        event = release[label]
        position[event] += 1
        row["probes"][label]["received_ns"] = event + 2 * MS * (position[event] - 1)
    return row, release


def analyze(sources):
    output = {"sources": {name: len(rows) for name, rows in sources.items()},
              "assumptions": {"time": "ideal proxy release + 2 ms serial spacing; no timer/network jitter",
                              "periodic100": "global monotonic 100 ms grid; wait for all four",
                              "defer100": "arrival-anchored 1050 ms first tick, then 100 ms; wait for all four",
                              "training": "64 positive old groups; separate 32-positive-group C0 session for test; costs include four no-warmup controls per source"},
              "policies": {}, "observer": {}, "slot1050_replay_check": {},
              "derived_rows": []}
    for mode in MODES:
        per_source = {}
        modeled = {}
        for source, rows in sources.items():
            waits, warm_waits, last_offsets, first_offsets = [], [], [], []
            full = 0
            modeled[source] = []
            for trial, items in rows:
                row, release = modeled_trial(trial, items, mode)
                modeled[source].append(row)
                anchor = min(x["arrival_ns"] for x in items.values())
                last_offsets.append((max(x["backend_received_ns"] for x in items.values()) - anchor) / MS)
                first_offsets.append((min(release.values()) - anchor) / MS)
                full += len(set(release.values())) == 1
                output["derived_rows"].append({
                    "source": source, "mode": mode, "group": trial["group"],
                    "warm_position": (trial["send_order"].index(trial["warm"]) + 1
                                      if trial["warm"] else None),
                    "send_order": trial["send_order"],
                    "last_completion_offset_ms": round(last_offsets[-1], 6),
                    "release_offset_ms": {label: round((t - anchor) / MS, 6)
                                          for label, t in release.items()},
                    "client_receive_offset_ms": {label: round(
                        (row["probes"][label]["received_ns"] - anchor) / MS, 6)
                        for label in items},
                    "wait_ms": {label: round((release[label] - x["backend_received_ns"]) / MS, 6)
                                for label, x in items.items()}})
                for label, x in items.items():
                    wait = (release[label] - x["backend_received_ns"]) / MS
                    assert wait >= 0
                    waits.append(wait)
                    if label == trial["warm"]:
                        warm_waits.append(wait)
            per_source[source] = {"groups": len(rows), "full_groups": full,
                                  "individual_wait_ms": summary(waits),
                                  "warm_wait_ms": summary(warm_waits),
                                  "first_release_offset_ms": summary(first_offsets),
                                  "last_completion_offset_ms": summary(last_offsets)}
        output["policies"][mode] = per_source
        train = [r for source in ("development_a", "development_b")
                 for r in modeled[source] if r["warm"]]
        test = [r for r in modeled["holdout"] if r["warm"]]
        result = {"R1": rank1(test)}
        for feature in ("R2", "T1", "T2", "RT"):
            xtr, ytr = data(train, feature)
            xte, yte = data(test, feature)
            model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
            model.fit(xtr, ytr)
            result[feature] = score(yte, model.predict(xte))
        output["observer"][mode] = result
    # Compare the old live 1050-ms batch signature to the ideal readiness rule.
    checks = {}
    for source, rows in sources.items():
        matched = 0
        errors = []
        for trial, items in rows:
            release = schedule("slot1050", items)
            tick = min(x["arrival_ns"] for x in items.values()) + 1050 * MS
            pred_early = {label for label, t in release.items() if t == tick}
            actual_early = {label for label, x in items.items() if x["flush_reason"] == "slot"}
            matched += pred_early == actual_early
            errors.extend((items[label]["release_ns"] - release[label]) / MS for label in items)
        checks[source] = {"matching_slot_membership": matched,
                          "groups": len(rows), "actual_minus_ideal_release_ms": summary(errors),
                          "min_error_ms": round(min(errors), 3)}
    output["slot1050_replay_check"] = checks
    all_dev = sources["development_a"] + sources["development_b"]
    output["fixed_slot_completion_coverage"] = {}
    for source, rows in (("development", all_dev), ("holdout", sources["holdout"])):
        offsets = [(max(x["backend_received_ns"] for x in items.values()) -
                    min(x["arrival_ns"] for x in items.values())) / MS
                   for _, items in rows]
        output["fixed_slot_completion_coverage"][source] = {
            str(slot): sum(x <= slot for x in offsets)
            for slot in (1050, 1100, 1150, 1160, 1200)}
    output["paired_wait_difference_vs_slot1200_ms"] = {}
    for mode in MODES:
        if mode == "slot1200":
            continue
        output["paired_wait_difference_vs_slot1200_ms"][mode] = {}
        for source in sources:
            current = {r["group"]: r for r in output["derived_rows"]
                       if r["source"] == source and r["mode"] == mode}
            baseline = {r["group"]: r for r in output["derived_rows"]
                        if r["source"] == source and r["mode"] == "slot1200"}
            differences = [current[group]["wait_ms"][label] - base["wait_ms"][label]
                           for group, base in baseline.items() for label in "ABCD"]
            output["paired_wait_difference_vs_slot1200_ms"][mode][source] = summary(differences)
    return output


if __name__ == "__main__":
    output = Path(sys.argv[1])
    sources = {name: read_source(name, folder) for name, folder in SOURCES.items()}
    result = analyze(sources)
    derived = result.pop("derived_rows")
    with output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    with output.with_name(output.stem + "-rows.jsonl").open("x") as f:
        for row in derived:
            f.write(json.dumps(row) + "\n")
    for mode in MODES:
        h = result["policies"][mode]["holdout"]
        obs = result["observer"][mode]
        print(mode, h["full_groups"], h["individual_wait_ms"],
              {key: obs[key]["hits"] for key in ("R1", "R2", "T1", "T2", "RT")})
