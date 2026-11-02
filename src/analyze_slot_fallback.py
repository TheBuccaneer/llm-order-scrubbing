"""Summarize the frozen 24-token slot calibration and independent holdout."""

import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


def percentile(values, q):
    values = sorted(values)
    return values[math.ceil(q * len(values)) - 1]


def stats(values):
    return {"n": len(values), "median": round(statistics.median(values), 3),
            "p95": round(percentile(values, .95), 3), "max": round(max(values), 3)}


def load(trials_path, proxy_path):
    trials = [json.loads(s) for s in Path(trials_path).read_text().splitlines()]
    proxy = [json.loads(s) for s in Path(proxy_path).read_text().splitlines()]
    by_id = {x["request_id"]: x for x in proxy if "request_id" in x}
    assert len(by_id) == len(proxy) == 4 * len(trials)
    rows = []
    for t in trials:
        assert t["mode"] == "slot1050" and t["output_tokens"] == 24
        assert set(t["send_order"]) == set("ABCD")
        items = []
        for label, p in t["probes"].items():
            x = by_id[p["request_id"]]
            assert (x["group"], x["label"], x["mode"]) == (t["group"], label, t["mode"])
            assert p["http_status"] == 200 and p["prompt_tokens"] == 548 and p["completion_tokens"] == 24
            assert p["cached_tokens_reported"] is None and x["cache_details_removed"] is True
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= x["sent_ns"] <= p["received_ns"]
            if t["warm"] == label:
                assert x["cached_tokens_reported"] == 544
            else:
                assert x["cached_tokens_reported"] in (None, 0)
            items.append((label, p, x))
        assert [a for a, _, _ in sorted(items, key=lambda z: z[1]["sent_ns"])] == t["send_order"]
        assert [a for a, _, _ in sorted(items, key=lambda z: z[1]["received_ns"])] == [a for a, _, _ in sorted(items, key=lambda z: z[2]["release_ns"])]
        if t["warm"]:
            assert t["warmup"]["received_ns"] < min(p["sent_ns"] for _, p, _ in items)
        arrivals = sorted(p["received_ns"] for _, p, _ in items)
        max_gap = max((b - a) / 1e6 for a, b in zip(arrivals, arrivals[1:]))
        late = sum(x["flush_reason"] == "late_fallback" for _, _, x in items)
        pos = t["send_order"].index(t["warm"]) + 1 if t["warm"] else 0
        rows.append({"position": pos, "warm": t["warm"], "late_responses": late,
                     "full_group": all(x["batch_size"] == 4 for _, _, x in items),
                     "max_client_gap_ms": max_gap,
                     "first_reply_ms": (arrivals[0] - min(p["sent_ns"] for _, p, _ in items)) / 1e6,
                     "rank1": min(items, key=lambda z: z[1]["received_ns"])[0],
                     "wait_ms": [x["added_wait_ms"] for _, _, x in items],
                     "e2e_ms": [(p["received_ns"] - p["sent_ns"]) / 1e6 for _, p, _ in items]})
    return rows, len(proxy)


def chi_square(table):
    total = sum(sum(row) for row in table)
    col = [sum(row[j] for row in table) for j in range(4)]
    score = 0.0
    for row in table:
        for j in range(4):
            expected = sum(row) * col[j] / total
            if expected:
                score += (row[j] - expected) ** 2 / expected
    return score


def association(rows, permutations=100_000):
    positive = [r for r in rows if r["position"]]
    labels = [r["position"] for r in positive]
    late = [r["late_responses"] for r in positive]
    table = [[sum(p == i and n == j for p, n in zip(labels, late)) for j in range(4)]
             for i in range(1, 5)]
    observed = chi_square(table)
    rng = random.Random(20261102)
    at_least = 0
    for _ in range(permutations):
        rng.shuffle(labels)
        perm = [[sum(p == i and n == j for p, n in zip(labels, late)) for j in range(4)]
                for i in range(1, 5)]
        at_least += chi_square(perm) >= observed - 1e-12
    return {"table_rows_position_1_to_4_cols_late_0_to_3": table,
            "chi_square": round(observed, 4), "balanced_label_permutation_p": round((at_least + 1) / (permutations + 1), 6),
            "permutations": permutations}


def describe(rows, proxy_count):
    positive = [r for r in rows if r["position"]]
    by_position = defaultdict(list)
    for r in positive:
        by_position[r["position"]].append(r)
    detect = Counter((r["late_responses"] > 0, r["max_client_gap_ms"] > 10) for r in rows)
    return {"groups": len(rows), "responses": proxy_count, "positive_groups": len(positive),
            "control_groups": len(rows) - len(positive),
            "position_counts": {str(i): len(by_position[i]) for i in range(1, 5)},
            "late_response_count": dict(sorted(Counter(r["late_responses"] for r in rows).items())),
            "full_groups": sum(r["full_group"] for r in rows),
            "groups_with_fallback": sum(r["late_responses"] > 0 for r in rows),
            "late_fallback_responses": sum(r["late_responses"] for r in rows),
            "warm_rank1": sum(r["rank1"] == r["warm"] for r in positive),
            "by_position": {str(i): {"n": len(by_position[i]),
                                     "fallback_groups": sum(r["late_responses"] > 0 for r in by_position[i]),
                                     "late_response_counts": dict(sorted(Counter(r["late_responses"] for r in by_position[i]).items())),
                                     "first_reply_ms": stats([r["first_reply_ms"] for r in by_position[i]])}
                            for i in range(1, 5)},
            "all_wait_ms": stats([w for r in rows for w in r["wait_ms"]]),
            "all_e2e_ms": stats([w for r in rows for w in r["e2e_ms"]]),
            "client_gap_gt_10ms_true_fallback": {f"{a}:{b}": n for (a, b), n in sorted(detect.items())}}


def main(cal_trials, cal_proxy, test_trials, test_proxy, output):
    cal, cal_n = load(cal_trials, cal_proxy)
    test, test_n = load(test_trials, test_proxy)
    result = {"calibration": describe(cal, cal_n), "holdout": describe(test, test_n),
              "holdout_association": association(test),
              "client_gap_rule": "maximum gap between four client receipts >10 ms; selected from calibration only"}
    with Path(output).open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(output, "calibration", len(cal), "holdout", len(test),
          "holdout permutation p", result["holdout_association"]["balanced_label_permutation_p"])


if __name__ == "__main__":
    main(*sys.argv[1:6])
