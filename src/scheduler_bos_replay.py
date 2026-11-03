"""Ideal C0/C1 release replay; modeled times are never live client times."""

import hashlib
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from offline_gate_replay import replay


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "c0_direct": ("results/bos-pilot-20261102/trials-extended.jsonl",
                  "results/bos-pilot-20261102/proxy-extended.jsonl", "direct"),
    "c1_direct": ("results/novelty-c1-20261102/confirm/trials.jsonl",
                  "results/novelty-c1-20261102/confirm/proxy.jsonl", "direct"),
}
MODES = ("direct", "bos4", "slot1050")
MS = 1_000_000


def load(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def describe(values):
    return {"n": len(values), "min": round(min(values), 3),
            "median": round(statistics.median(values), 3),
            "max": round(max(values), 3)}


def model_client(trial, schedule, mode):
    """Use a fixed independent permutation and ideal 2 ms serial writes."""
    permutation = list(trial["send_order"])
    seed = int.from_bytes(hashlib.sha256(trial["group"].encode()).digest()[:8], "big")
    random.Random(seed).shuffle(permutation)
    ordered = sorted(permutation, key=lambda label: (
        schedule[trial["probes"][label]["request_id"]][0], permutation.index(label)))
    seen = defaultdict(int)
    received = {}
    for label in ordered:
        release = schedule[trial["probes"][label]["request_id"]][0]
        received[label] = release + (0 if mode == "direct" else 2 * MS * seen[release])
        seen[release] += 1
    return received


def run():
    rows = []
    for source, (trials_path, proxy_path, actual_mode) in SOURCES.items():
        trials = [x for x in load(trials_path) if x["mode"] == actual_mode]
        proxy = {x["request_id"]: x for x in load(proxy_path)}
        assert len(trials) == (68 if source == "c0_direct" else 36)
        for trial in trials:
            items = [proxy[p["request_id"]] for p in trial["probes"].values()]
            assert len(items) == 4 and all(x["group"] == trial["group"] for x in items)
            if trial["warm"]:
                assert proxy[trial["probes"][trial["warm"]]["request_id"]]["cached_tokens_reported"] == 544
            send_order = trial["send_order"]
            first_send = min(p["sent_ns"] for p in trial["probes"].values())
            anchor = min(x["arrival_ns"] for x in items)
            last = max(x["backend_received_ns"] for x in items)
            for mode in MODES:
                schedule = replay(items, mode)
                received = model_client(trial, schedule, mode)
                gaps = [(received[b] - received[a]) / MS for a, b in zip(send_order, send_order[1:])]
                closest = min(range(3), key=lambda i: abs(gaps[i]))
                guess = 1 if abs(gaps[closest]) > 10 else closest + 2
                waits = [(schedule[x["request_id"]][0] - x["backend_received_ns"]) / MS for x in items]
                rows.append({"source": source, "mode": mode, "group": trial["group"],
                             "warm_position": send_order.index(trial["warm"]) + 1 if trial["warm"] else None,
                             "first_modeled_client_ms": (min(received.values()) - first_send) / MS,
                             "last_backend_ms": (last - anchor) / MS,
                             "smallest_abs_adjacent_gap_ms": min(abs(x) for x in gaps),
                             "gap_rule_guess_position": guess,
                             "mean_wait_ms": statistics.mean(waits),
                             "full_group": all(schedule[x["request_id"]][1] == 4 for x in items),
                             "late_fallback_responses": sum(schedule[x["request_id"]][2] == "late_fallback" for x in items)})
    summary = {"assumption": "Ideal backend readiness; direct client time = backend HTTP completion; BOS/slot client time = ideal release + 2 ms per serial answer; no network/timer jitter or backend feedback.",
               "sources": SOURCES, "results": {}}
    for source in SOURCES:
        for mode in MODES:
            subset = [r for r in rows if r["source"] == source and r["mode"] == mode]
            positive = [r for r in subset if r["warm_position"]]
            summary["results"][f"{source}_{mode}"] = {
                "groups": len(subset), "positive": len(positive),
                "full_groups": sum(r["full_group"] for r in subset),
                "late_fallback_responses": sum(r["late_fallback_responses"] for r in subset),
                "mean_individual_wait_ms": describe([r["mean_wait_ms"] for r in subset]),
                "smallest_gap_ms": describe([r["smallest_abs_adjacent_gap_ms"] for r in positive]),
                "gap_rule_hits": sum(r["gap_rule_guess_position"] == r["warm_position"] for r in positive),
                "first_client_by_warm_position_ms": {
                    str(pos): describe([r["first_modeled_client_ms"] for r in positive if r["warm_position"] == pos])
                    for pos in range(1, 5)},
            }
    return summary, rows


if __name__ == "__main__":
    path = Path(sys.argv[1])
    summary, rows = run()
    with path.open("x") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    with path.with_name("replay-rows.jsonl").open("x") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    for key, value in summary["results"].items():
        print(key, value["gap_rule_hits"], "/", value["positive"],
              "full", value["full_groups"], "/", value["groups"])
