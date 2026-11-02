"""Independent, offline reconstruction of the existing BOS evidence."""

import json
import random
import statistics as stats
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SETS = {
    "development": ("bos-pilot-20261102/trials-extended.jsonl", "bos-pilot-20261102/proxy-extended.jsonl"),
    "holdout": ("bos-holdout-20261102/trials.jsonl", "bos-holdout-20261102/proxy.jsonl"),
    "slot_development": ("bos-slot-20261102/trials-extended.jsonl", "bos-slot-20261102/proxy-extended.jsonl"),
    "sanitized": ("bos-sanitized-20261102/trials.jsonl", "bos-sanitized-20261102/proxy.jsonl"),
}


def load(path):
    return [json.loads(line) for line in (ROOT / "results" / path).read_text().splitlines() if line]


def median_ms(values):
    return round(stats.median(values), 3)


def percentile(values, q):
    return round(float(np.percentile(values, q)), 3)


def analyze(name, paths):
    trials, proxy = map(load, paths)
    by_request = {x["request_id"]: x for x in proxy if "request_id" in x}
    assert len(by_request) == len(proxy) == len(trials) * 4, name
    seen_ids, seen_salts = set(), set()
    counts = Counter()
    pos_by_mode = defaultdict(Counter)
    records = []
    shuffle_checked = 0
    for t in trials:
        assert t["group"] == t["salt"] and t["salt"] not in seen_salts
        seen_salts.add(t["salt"])
        assert set(t["send_order"]) == set("ABCD") and len(t["probes"]) == 4
        warm = t["warm"]
        counts[(t["mode"], "warm" if warm else "cold")] += 1
        if warm:
            pos_by_mode[t["mode"]][t["send_order"].index(warm) + 1] += 1
        joined = []
        for label, p in t["probes"].items():
            rid = p["request_id"]
            assert rid not in seen_ids and rid in by_request
            seen_ids.add(rid)
            x = by_request[rid]
            assert (x["label"], x["group"], x["mode"]) == (label, t["group"], t["mode"])
            assert p["http_status"] == 200 and p["prompt_tokens"] == 548 and p["completion_tokens"] == 16
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= x["sent_ns"] <= p["received_ns"]
            if name == "sanitized":
                assert x["cache_details_removed"] is True and p["cached_tokens_reported"] is None
            if warm and label == warm:
                assert x["cached_tokens_reported"] == 544
            elif warm:
                assert x["cached_tokens_reported"] in (None, 0)
            joined.append((label, p, x))
        if warm:
            assert t["warmup"] and t["warmup"]["received_ns"] < min(p["sent_ns"] for _, p, _ in joined)
        assert [label for label, _, _ in sorted(joined, key=lambda z: z[1]["sent_ns"])] == t["send_order"]
        assert [label for label, _, _ in sorted(joined, key=lambda z: z[1]["received_ns"])] == [label for label, _, _ in sorted(joined, key=lambda z: z[2]["release_ns"])]
        for batch in set(x["batch"] for _, _, x in joined):
            items = [(label, p, x) for label, p, x in joined if x["batch"] == batch]
            if items[0][2]["shuffle_seed"] is not None:
                incoming = sorted(items, key=lambda z: z[2]["backend_received_ns"])
                rng = random.Random(items[0][2]["shuffle_seed"])
                rng.shuffle(incoming)
                observed = sorted(items, key=lambda z: z[2]["release_position"])
                assert [z[0] for z in incoming] == [z[0] for z in observed], (name, t["trial"], batch)
                shuffle_checked += 1
        first_sent = min(p["sent_ns"] for _, p, _ in joined)
        first_client = min(p["received_ns"] for _, p, _ in joined)
        last_backend = max(x["backend_received_ns"] for _, _, x in joined)
        first_release = min(x["release_ns"] for _, _, x in joined)
        rank1 = min(joined, key=lambda z: z[1]["received_ns"])[0]
        records.append({"mode": t["mode"], "warm": warm, "send_order": t["send_order"],
                        "warm_position": t["send_order"].index(warm) + 1 if warm else None,
                        "rank1": rank1,
                        "first_client_ms": (first_client - first_sent) / 1e6,
                        "last_backend_ms": (last_backend - first_sent) / 1e6,
                        "first_release_ms": (first_release - first_sent) / 1e6,
                        "client_after_release_ms": (first_client - first_release) / 1e6,
                        "release_after_close_ms": (first_release - last_backend) / 1e6,
                        "batch_sizes": sorted(x["batch_size"] for _, _, x in joined),
                        "flush_reasons": Counter(x["flush_reason"] for _, _, x in joined),
                        "probe_wait_ms": [(x["release_ns"] - x["backend_received_ns"]) / 1e6 for _, _, x in joined],
                        "warm_wait_ms": (next(x for label, _, x in joined if label == warm)["added_wait_ms"] if warm else None),
                        "warm_e2e_ms": ((next(p for label, p, _ in joined if label == warm)["received_ns"] - next(p for label, p, _ in joined if label == warm)["sent_ns"]) / 1e6 if warm else None)})
    assert len(seen_ids) == len(proxy)
    return {"name": name, "counts": {f"{mode}:{kind}": n for (mode, kind), n in sorted(counts.items())},
            "warm_position_counts": {m: dict(sorted(c.items())) for m, c in pos_by_mode.items()},
            "responses": len(proxy), "shuffle_batches_reconstructed": shuffle_checked,
            "records": records}


def summarize(data):
    out = {}
    for name, block in data.items():
        modes = {}
        for mode in sorted(set(r["mode"] for r in block["records"])):
            rs = [r for r in block["records"] if r["mode"] == mode]
            warm = [r for r in rs if r["warm"]]
            waits = [w for r in rs for w in r["probe_wait_ms"]]
            z = {"trials": len(rs), "warm_trials": len(warm),
                 "rank1_hits": sum(r["rank1"] == r["warm"] for r in warm),
                 "full_groups": sum(all(n == 4 for n in r["batch_sizes"]) for r in rs),
                 "late_fallback_responses": sum(r["flush_reasons"].get("late_fallback", 0) for r in rs),
                 "all_wait_ms": {"median": median_ms(waits), "p95": percentile(waits, 95), "max": round(max(waits), 3)}}
            if warm:
                z["warm_wait_ms"] = {"median": median_ms([r["warm_wait_ms"] for r in warm]),
                                      "p95": percentile([r["warm_wait_ms"] for r in warm], 95),
                                      "max": round(max(r["warm_wait_ms"] for r in warm), 3)}
            if mode in ("bos4", "d250") and all(all(n == 4 for n in r["batch_sizes"]) for r in rs):
                x = np.array([r["last_backend_ms"] for r in warm])
                y = np.array([r["first_client_ms"] for r in warm])
                z["block_close_mechanism"] = {"pearson_r": round(float(np.corrcoef(x, y)[0, 1]), 5),
                                               "median_client_after_close_ms": median_ms(y - x),
                                               "median_release_after_close_ms": median_ms([r["release_after_close_ms"] for r in warm])}
            modes[mode] = z
        out[name] = {"counts": block["counts"], "responses": block["responses"],
                     "shuffle_batches_reconstructed": block["shuffle_batches_reconstructed"],
                     "warm_position_counts": block["warm_position_counts"], "modes": modes}
    return out


def main(output):
    data = {name: analyze(name, paths) for name, paths in SETS.items()}
    summary = summarize(data)
    centers = {pos: stats.median(r["first_client_ms"] for r in data["development"]["records"]
                                 if r["mode"] == "bos4" and r["warm_position"] == pos)
               for pos in range(1, 5)}
    for name in ("holdout", "sanitized"):
        summary[name]["frozen_bos_t1"] = {}
        for mode in ("bos4", "d250"):
            warm = [r for r in data[name]["records"] if r["mode"] == mode and r["warm"]]
            summary[name]["frozen_bos_t1"][mode] = sum(
                min(centers, key=lambda pos: abs(centers[pos] - r["first_client_ms"])) == r["warm_position"]
                for r in warm)
    Path(output).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": output, "responses": {n: b["responses"] for n, b in data.items()},
                      "frozen_hits": {n: summary[n].get("frozen_bos_t1") for n in ("holdout", "sanitized")}}, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
