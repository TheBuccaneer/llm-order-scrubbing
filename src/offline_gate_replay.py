"""Ideal release-time replay on recorded proxy arrivals and backend responses.

The replay omits Python timer jitter and serial HTTP writes. It is used for
paired cost comparisons, never as a substitute for a live leakage result.
"""

import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path


MODES = ("direct", "bos4", "d100", "d250", "slot1050")


def quantile(values, q):
    values = sorted(values)
    return values[math.ceil(q * len(values)) - 1]


def replay(items, mode):
    """Return request ID -> (ideal release ns, batch size, reason)."""
    ordered = sorted(items, key=lambda x: x["backend_received_ns"])
    if mode == "direct":
        return {x["request_id"]: (x["backend_received_ns"], 1, "direct")
                for x in ordered}
    if mode == "bos4":
        close = ordered[-1]["backend_received_ns"]
        return {x["request_id"]: (close, 4, "full") for x in ordered}
    if mode == "slot1050":
        cutoff = min(x["arrival_ns"] for x in ordered) + 1_050_000_000
        early = [x for x in ordered if x["backend_received_ns"] <= cutoff]
        out = {x["request_id"]: (cutoff, len(early), "slot") for x in early}
        out.update({x["request_id"]: (x["backend_received_ns"], 1,
                                      "late_fallback") for x in ordered
                    if x["backend_received_ns"] > cutoff})
        return out
    if mode in ("d100", "d250"):
        interval_ns = (int(mode[1:]) - 10) * 1_000_000
        out = {}
        i = 0
        while i < len(ordered):
            deadline = ordered[i]["backend_received_ns"] + interval_ns
            batch = [ordered[i]]
            j = i + 1
            while j < len(ordered) and len(batch) < 4 and ordered[j]["backend_received_ns"] <= deadline:
                batch.append(ordered[j])
                j += 1
            full = len(batch) == 4
            release = batch[-1]["backend_received_ns"] if full else deadline
            for x in batch:
                out[x["request_id"]] = (release, len(batch), "full" if full else "deadline")
            i = j
        return out
    raise ValueError(mode)


def summary(values):
    return {"n": len(values), "median": round(statistics.median(values), 3),
            "p95": round(quantile(values, .95), 3), "max": round(max(values), 3)}


def main(trials_path, proxy_path, output_path):
    trials = [json.loads(s) for s in Path(trials_path).read_text().splitlines()]
    proxy = [json.loads(s) for s in Path(proxy_path).read_text().splitlines()]
    by_id = {x["request_id"]: x for x in proxy if "request_id" in x}
    assert len(by_id) == len(proxy) == 4 * len(trials)
    by_group = {trial["group"]: trial for trial in trials}
    all_waits = {mode: [] for mode in MODES}
    warm_waits = {mode: [] for mode in MODES}
    traces = []
    live_error = []
    live_pattern_agreement = Counter()
    for trial in trials:
        items = [by_id[p["request_id"]] for p in trial["probes"].values()]
        predictions = {mode: replay(items, mode) for mode in MODES}
        actual_mode = trial["mode"]
        if actual_mode in MODES:
            same = all(predictions[actual_mode][x["request_id"]][1:] ==
                       (x["batch_size"], x["flush_reason"]) for x in items)
            live_pattern_agreement["match" if same else "different"] += 1
            live_error.extend((x["release_ns"] - predictions[actual_mode][x["request_id"]][0]) / 1e6
                              for x in items)
        trace = {"group": trial["group"], "warm": trial["warm"],
                 "source_mode": actual_mode, "replay": {}}
        for mode in MODES:
            predicted = predictions[mode]
            waits = {x["request_id"]: max(0.0, (predicted[x["request_id"]][0] -
                                                x["backend_received_ns"]) / 1e6)
                     for x in items}
            all_waits[mode].extend(waits.values())
            if trial["warm"]:
                warm_id = trial["probes"][trial["warm"]]["request_id"]
                warm_waits[mode].append(waits[warm_id])
            trace["replay"][mode] = {
                "wait_ms": waits,
                "full_group": all(predicted[x["request_id"]][1] == 4 for x in items),
                "late_fallback_responses": sum(predicted[x["request_id"]][2] == "late_fallback"
                                               for x in items),
                "batch_sizes": sorted(set(predicted[x["request_id"]][1] for x in items)),
            }
        traces.append(trace)
    paired = {}
    for mode in MODES:
        if mode == "bos4":
            continue
        diffs = []
        warm_diffs = []
        for trace in traces:
            base = trace["replay"]["bos4"]["wait_ms"]
            other = trace["replay"][mode]["wait_ms"]
            diffs.extend(other[rid] - base[rid] for rid in base)
            if trace["warm"]:
                original = by_group[trace["group"]]
                warm_id = original["probes"][trace["warm"]]["request_id"]
                warm_diffs.append(other[warm_id] - base[warm_id])
        paired[mode] = {"all_individual_median_ms": round(statistics.median(diffs), 3),
                        "warm_individual_median_ms": round(statistics.median(warm_diffs), 3),
                        "difference_of_warm_medians_ms": round(statistics.median(warm_waits[mode]) -
                                                               statistics.median(warm_waits["bos4"]), 3)}
    result = {"source": {"trials": str(trials_path), "proxy": str(proxy_path),
                         "groups": len(trials), "responses": len(proxy)},
              "method": "Ideal release readiness; 10 ms early deadline timer; excludes serial sends and timer jitter",
              "live_validation": {"batch_pattern_agreement": dict(live_pattern_agreement),
                                  "actual_minus_ideal_release_ms": summary(live_error),
                                  "min_ms": round(min(live_error), 3)},
              "modes": {mode: {"all_wait_ms": summary(all_waits[mode]),
                               "warm_wait_ms": summary(warm_waits[mode]),
                               "full_groups": sum(t["replay"][mode]["full_group"] for t in traces),
                               "late_fallback_responses": sum(t["replay"][mode]["late_fallback_responses"] for t in traces)}
                        for mode in MODES},
              "paired_vs_bos4": paired}
    with Path(output_path).open("x") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(output_path, result["live_validation"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
