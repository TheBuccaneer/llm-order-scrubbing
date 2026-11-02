"""Check the small C1/C2 and alternate-prompt transfer series."""

import json
import math
import statistics
import sys
from pathlib import Path


FILES = {
    "c1_primary": ("config-c1/primary.jsonl", True, None),
    "c1_holdout": ("config-c1/holdout.jsonl", True, None),
    "c1_cacheoff": ("config-c1/cacheoff.jsonl", False, None),
    "c2_primary": ("config-c2/primary.jsonl", True, None),
    "c2_cacheoff": ("config-c2/cacheoff.jsonl", False, None),
    "prompt_primary": ("prompt-v2/primary.jsonl", True, True),
    "prompt_holdout": ("prompt-v2/holdout.jsonl", True, True),
    "prompt_cacheoff": ("prompt-v2/cacheoff.jsonl", False, True),
}


def wilson(hits, n):
    z = 1.959963984540054
    p = hits / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(center - spread, 4), round(center + spread, 4)]


def analyze(path, cache_on, alternate, seen_salts):
    trials = [json.loads(s) for s in path.read_text().splitlines()]
    assert trials
    rows = []
    hashes = set()
    for t in trials:
        assert t["salt"] not in seen_salts
        seen_salts.add(t["salt"])
        assert set(t["send_order"]) == set("ABCD") and set(t["probes"]) == set("ABCD")
        assert bool(t.get("prompt_set_sha256")) == bool(alternate)
        if alternate:
            hashes.add(t["prompt_set_sha256"])
        probes = t["probes"]
        sent = sorted(probes, key=lambda x: probes[x]["sent_ns"])
        recv = sorted(probes, key=lambda x: probes[x]["received_ns"])
        assert sent == t["send_order"]
        for label, p in probes.items():
            assert p["sent_ns"] < p["received_ns"] and p["http_status"] == 200
            assert p["prompt_tokens"] == 548 and p["completion_tokens"] == 16
            expected = 544 if cache_on and label == t["warm"] else None
            assert p["cached_tokens_reported"] == expected
        if t["warm"]:
            assert t["warmup"] and t["warmup"]["received_ns"] < min(p["sent_ns"] for p in probes.values())
            position = sent.index(t["warm"]) + 1
            rows.append({"position": position, "rank": recv.index(t["warm"]) + 1,
                         "first_reply_ms": (min(p["received_ns"] for p in probes.values()) -
                                            min(p["sent_ns"] for p in probes.values())) / 1e6})
    by_pos = {str(i): [r for r in rows if r["position"] == i] for i in range(1, 5)}
    hits = sum(r["rank"] == 1 for r in rows)
    return {"trials": len(trials), "warm_trials": len(rows),
            "cold_controls": len(trials) - len(rows),
            "warm_rank1": hits, "rank1_accuracy": round(hits / len(rows), 4),
            "wilson95": wilson(hits, len(rows)),
            "later_warm_rank1": sum(r["rank"] == 1 and r["position"] > 1 for r in rows),
            "later_warm_trials": sum(r["position"] > 1 for r in rows),
            "by_position": {str(i): {"n": len(by_pos[str(i)]),
                                     "rank1": sum(r["rank"] == 1 for r in by_pos[str(i)]),
                                     "median_first_reply_ms": round(statistics.median(r["first_reply_ms"] for r in by_pos[str(i)]), 3)}
                            for i in range(1, 5)},
            "prompt_set_sha256": next(iter(hashes)) if hashes else None,
            "observations": rows}


def main(root, output):
    root = Path(root)
    seen_salts = set()
    result = {name: analyze(root / relative, cache_on, alternate, seen_salts)
              for name, (relative, cache_on, alternate) in FILES.items()}
    train = result["c1_primary"]["observations"]
    test = result["c1_holdout"]["observations"]
    centers = {i: statistics.median(r["first_reply_ms"] for r in train if r["position"] == i)
               for i in range(1, 5)}
    result["c1_t1_train_primary_test_holdout"] = {
        "centers_ms": {str(i): round(v, 3) for i, v in centers.items()},
        "hits": sum(min(centers, key=lambda i: abs(centers[i] - r["first_reply_ms"])) == r["position"]
                    for r in test),
        "n": len(test),
    }
    for value in result.values():
        if isinstance(value, dict):
            value.pop("observations", None)
    with Path(output).open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(output, {name: (z["warm_rank1"], z["warm_trials"]) for name, z in result.items()
                   if "warm_rank1" in z})


if __name__ == "__main__":
    main(*sys.argv[1:3])
