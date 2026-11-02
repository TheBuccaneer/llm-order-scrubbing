"""Per-request live proxy wait and client latency for the existing series."""

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


SETS = {
    "main16": ("results/bos-pilot-20261102/trials-extended.jsonl",
               "results/bos-pilot-20261102/proxy-extended.jsonl"),
    "sanitized16": ("results/bos-sanitized-20261102/trials.jsonl",
                    "results/bos-sanitized-20261102/proxy.jsonl"),
    "fallback24_holdout": ("results/decision-validation-20261102/slot-fallback/holdout/trials-24.jsonl",
                           "results/decision-validation-20261102/slot-fallback/holdout/proxy.jsonl"),
    "fallback24_confirm": ("results/decision-validation-20261102/slot-fallback/confirm/trials-24.jsonl",
                           "results/decision-validation-20261102/slot-fallback/confirm/proxy.jsonl"),
}


def stats(values):
    ordered = sorted(values)
    return {"n": len(ordered), "median": round(statistics.median(ordered), 3),
            "p95": round(ordered[math.ceil(.95 * len(ordered)) - 1], 3),
            "max": round(ordered[-1], 3)}


def main(output):
    result = {}
    for session, (trial_file, proxy_file) in SETS.items():
        trials = [json.loads(s) for s in Path(trial_file).read_text().splitlines()]
        proxy = [json.loads(s) for s in Path(proxy_file).read_text().splitlines()]
        by_id = {x["request_id"]: x for x in proxy if "request_id" in x}
        assert len(by_id) == len(proxy) == len(trials) * 4
        modes = defaultdict(list)
        for trial in trials:
            probes = trial["probes"]
            joined = [(label, p, by_id[p["request_id"]]) for label, p in probes.items()]
            assert all(x["group"] == trial["group"] and x["label"] == label
                       for label, _, x in joined)
            modes[trial["mode"]].append((trial, joined))
        result[session] = {}
        for mode, groups in modes.items():
            all_waits, all_e2e, warm_waits, warm_e2e = [], [], [], []
            full = fallback_groups = fallback_responses = 0
            rank1 = 0
            for trial, joined in groups:
                full += all(x["batch_size"] == 4 for _, _, x in joined)
                fallback = sum(x["flush_reason"] == "late_fallback" for _, _, x in joined)
                fallback_groups += fallback > 0
                fallback_responses += fallback
                for label, p, x in joined:
                    wait = (x["release_ns"] - x["backend_received_ns"]) / 1e6
                    e2e = (p["received_ns"] - p["sent_ns"]) / 1e6
                    all_waits.append(wait)
                    all_e2e.append(e2e)
                    if label == trial["warm"]:
                        warm_waits.append(wait)
                        warm_e2e.append(e2e)
                if trial["warm"]:
                    rank1 += min(joined, key=lambda z: z[1]["received_ns"])[0] == trial["warm"]
            result[session][mode] = {
                "groups": len(groups), "positive_groups": len(warm_waits),
                "warm_rank1": rank1, "full_groups": full,
                "fallback_groups": fallback_groups,
                "fallback_responses": fallback_responses,
                "all_proxy_wait_ms": stats(all_waits),
                "warm_proxy_wait_ms": stats(warm_waits),
                "all_client_e2e_ms": stats(all_e2e),
                "warm_client_e2e_ms": stats(warm_e2e),
            }
    with Path(output).open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(output)


if __name__ == "__main__":
    main(sys.argv[1])
