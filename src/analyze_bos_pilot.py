"""Join client and proxy records and check the release-channel measurements."""

import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(fraction * len(ordered)) - 1]


def main(trials_path: Path, proxy_path: Path, output: Path) -> None:
    trials = [json.loads(line) for line in trials_path.read_text().splitlines()]
    proxy = [json.loads(line) for line in proxy_path.read_text().splitlines()]
    if any("error" in row for row in proxy):
        raise RuntimeError("proxy recorded errors")
    by_id = {row["request_id"]: row for row in proxy}
    if len(by_id) != len(proxy) or len(proxy) != 4 * len(trials):
        raise RuntimeError("missing or duplicate proxy records")

    summary = {"trials": len(trials), "requests": len(proxy), "modes": {}}
    for mode in ("direct", "bos4", "d100", "d250", "slot1050"):
        subset = [trial for trial in trials if trial["mode"] == mode]
        if not subset:
            continue
        warm_rank = Counter()
        warm_send_position = Counter()
        later_warm_first = 0
        raw_warm_first = 0
        full_block_warm = 0
        no_warm_exact = 0
        proxy_client_order_equal = 0
        send_order_equal = 0
        timestamp_errors = 0
        cache_control_errors = 0
        waits = []
        warm_waits = []
        batch_patterns = Counter()
        for trial in subset:
            probes = trial["probes"]
            joined = {label: by_id[item["request_id"]] for label, item in probes.items()}
            if any(row["group"] != trial["group"] or row["label"] != label
                   for label, row in joined.items()):
                raise RuntimeError("request ID to group/label mismatch")
            sent = sorted(probes, key=lambda label: probes[label]["sent_ns"])
            raw = sorted(joined, key=lambda label: joined[label]["backend_received_ns"])
            released = sorted(joined, key=lambda label: joined[label]["release_ns"])
            received = sorted(probes, key=lambda label: probes[label]["received_ns"])
            send_order_equal += sent == trial["send_order"]
            proxy_client_order_equal += released == received
            if mode != "direct":
                sizes = Counter(row["batch"] for row in joined.values())
                batch_patterns[tuple(sorted(sizes.values()))] += 1
            for label, item in probes.items():
                row = joined[label]
                times = (
                    item["sent_ns"], row["arrival_ns"],
                    row["backend_received_ns"], row["release_ns"],
                    row["sent_ns"], item["received_ns"],
                )
                timestamp_errors += list(times) != sorted(times)
                wait = row["added_wait_ms"]
                waits.append(wait)
                if label == trial["warm"]:
                    warm_waits.append(wait)
                    cache_control_errors += row["cached_tokens_reported"] != 544
                else:
                    cache_control_errors += row["cached_tokens_reported"] not in (None, 0)
                if row.get("cache_details_removed"):
                    cache_control_errors += item["cached_tokens_reported"] is not None
                cache_control_errors += item["completion_tokens"] != 16
            if trial["warm"] is None:
                no_warm_exact += sent == received
                continue
            warm = trial["warm"]
            position = sent.index(warm) + 1
            warm_send_position[position] += 1
            warm_rank[received.index(warm) + 1] += 1
            if position > 1:
                later_warm_first += received[0] == warm
            raw_warm_first += raw[0] == warm
            full_block_warm += all(row["batch_size"] == 4 for row in joined.values())

        target = int(mode[1:]) if mode in ("d100", "d250") else None
        summary["modes"][mode] = {
            "trials": len(subset),
            "warm_trials": sum(warm_rank.values()),
            "warm_send_position": dict(sorted(warm_send_position.items())),
            "warm_received_rank": dict(sorted(warm_rank.items())),
            "later_warm_rank1": later_warm_first,
            "later_warm_trials": sum(n for pos, n in warm_send_position.items() if pos > 1),
            "warm_backend_rank1": raw_warm_first,
            "warm_full_block": full_block_warm,
            "no_warm_exact_send_receive": no_warm_exact,
            "no_warm_trials": len(subset) - sum(warm_rank.values()),
            "send_order_agreement": send_order_equal,
            "release_client_order_agreement": proxy_client_order_equal,
            "batch_patterns": {str(key): count for key, count in sorted(batch_patterns.items())},
            "all_wait_ms": {
                "median": statistics.median(waits), "p95": percentile(waits, 0.95),
                "max": max(waits),
            },
            "warm_wait_ms": {
                "median": statistics.median(warm_waits),
                "p95": percentile(warm_waits, 0.95),
                "max": max(warm_waits),
            },
            "target_ms": target,
            "target_exceedances": sum(wait > target for wait in waits) if target else None,
            "timestamp_errors": timestamp_errors,
            "cache_control_errors": cache_control_errors,
        }
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
