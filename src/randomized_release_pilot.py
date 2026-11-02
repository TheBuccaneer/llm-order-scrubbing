"""Offline screen of state-independent random slots against matched fixed slots.

All client traces are idealized: recorded completion times, a per-group
label-independent shuffle, 2 ms serial writes, no timer or network jitter.
"""

import hashlib
import json
import math
import random
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from causal_release_pilot import MS, SOURCES, read_source


SLOTS = (1050, 1100, 1105, 1130, 1150, 1155, 1160, 1200)
POLICIES = {
    "fixed_1105": {1105: 1.0},
    "coin_1050_1160": {1050: .5, 1160: .5},
    "fixed_1130": {1130: 1.0},
    "coin_1100_1160": {1100: .5, 1160: .5},
    "fixed_1155": {1155: 1.0},
    "coin_1150_1160": {1150: .5, 1160: .5},
    "fixed_1160": {1160: 1.0},
    "fixed_1200": {1200: 1.0},
}
SESSIONS = {
    "development": ("development_a", "development_b"),
    "separate_c0": ("holdout",),
}


def outcome(trial, items, slot):
    """Emulate the existing slot/fallback rule with only public arrivals.

    In the real policy a timer fires at anchor+slot, releasing ready jobs;
    subsequent completions release individually. Recorded future completion
    times are used only to replay that causal behavior.
    """
    anchor = min(x["arrival_ns"] for x in items.values())
    tick = anchor + slot * MS
    ready = [label for label, x in items.items() if x["backend_received_ns"] <= tick]
    late = [label for label in items if label not in ready]
    seed = int.from_bytes(hashlib.sha256(trial["group"].encode()).digest()[:8], "big")
    order = list("ABCD")
    random.Random(seed).shuffle(order)
    ready.sort(key=order.index)
    late.sort(key=lambda label: (items[label]["backend_received_ns"], order.index(label)))
    release = {label: tick for label in ready}
    release.update({label: items[label]["backend_received_ns"] for label in late})
    receive = {label: tick + i * 2 * MS for i, label in enumerate(ready)}
    receive.update({label: release[label] for label in late})
    t0 = min(p["sent_ns"] for p in trial["probes"].values())
    send_order = trial["send_order"]
    client_times = [(receive[label] - t0) / MS for label in send_order]
    ranked = sorted(send_order, key=lambda label: receive[label])
    ranks = [ranked.index(label) for label in send_order]
    rank_matrix = [float(ranks[i] == j) for i in range(4) for j in range(4)]
    sorted_times = sorted(receive.values())
    gap = max((b - a) / MS for a, b in zip(sorted_times, sorted_times[1:]))
    return {
        "group": trial["group"], "source_warm": trial["warm"],
        "warm_position": (send_order.index(trial["warm"]) if trial["warm"] else None),
        "slot_ms": slot, "fallback": bool(late), "client_gap_gt10ms": gap > 10,
        "mean_wait_ms": sum((release[label] - x["backend_received_ns"]) / MS
                            for label, x in items.items()) / 4,
        "client_time_ms": client_times,
        "rank_matrix": rank_matrix,
    }


def feature(row, kind):
    times = np.asarray(row["client_time_ms"], dtype=float)
    if kind == "T2":
        return times
    if kind == "RT":
        return np.r_[np.asarray(row["rank_matrix"]), times]
    if kind == "MMD":
        # Fixed, declared scales: 50 ms for each client time, 0.25 for
        # rank indicators. The rank is also implicit in the four times.
        return np.r_[times / 50, np.asarray(row["rank_matrix"]) * .25]
    raise ValueError(kind)


def gram(groups, weights):
    names = list(groups)
    vectors = [[feature(groups[g][d], "MMD") for d in weights] for g in names]
    probabilities = list(weights.values())
    n = len(names)
    k = np.ones((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            similarity = sum(probabilities[a] * probabilities[b] *
                             math.exp(-sum((vectors[i][a] - vectors[j][b]) ** 2) / 2)
                             for a in range(len(weights)) for b in range(len(weights)))
            k[i, j] = k[j, i] = similarity
    return k


def four_class_mmd(k, labels):
    values = []
    for a, b in combinations(range(4), 2):
        ia, ib = np.where(labels == a)[0], np.where(labels == b)[0]
        values.append(k[np.ix_(ia, ia)].mean() + k[np.ix_(ib, ib)].mean() -
                      2 * k[np.ix_(ia, ib)].mean())
    return float(np.mean(values))


def distinguishability(groups, weights, seed):
    positives = {g: rows for g, rows in groups.items()
                 if next(iter(rows.values()))["warm_position"] is not None}
    labels = np.asarray([next(iter(rows.values()))["warm_position"]
                         for rows in positives.values()])
    assert all(np.sum(labels == position) == len(labels) // 4 for position in range(4))
    k = gram(positives, weights)
    observed = four_class_mmd(k, labels)
    rng = np.random.default_rng(seed)
    # The two old sessions reused the same randomized case order. Permute
    # their labels as paired cases, not as 64 independent assignments.
    if len(labels) == 64:
        assert np.array_equal(labels[:32], labels[32:])
        null = np.asarray([four_class_mmd(k, np.tile(rng.permutation(labels[:32]), 2))
                           for _ in range(999)])
    else:
        null = np.asarray([four_class_mmd(k, rng.permutation(labels)) for _ in range(999)])
    gap_rates = []
    fallback_rates = []
    for position in range(4):
        group_rows = [rows for rows in positives.values()
                      if next(iter(rows.values()))["warm_position"] == position]
        gap_rates.append(sum(p * rows[d]["client_gap_gt10ms"]
                             for rows in group_rows for d, p in weights.items()) / len(group_rows))
        fallback_rates.append(sum(p * rows[d]["fallback"]
                                  for rows in group_rows for d, p in weights.items()) / len(group_rows))
    return {"mmd2_full_trace": round(observed, 6),
            "permutation_p": round((1 + np.sum(null >= observed)) / 1000, 4),
            "permutation_null_median": round(float(np.median(null)), 6),
            "observable_gap_rate_by_position": [round(x, 4) for x in gap_rates],
            "gap_event_tv_lower_bound_max_pair": round(max(gap_rates) - min(gap_rates), 4),
            "internal_fallback_rate_by_position": [round(x, 4) for x in fallback_rates]}


def attack(train, test, weights, kind):
    x, y, sample_weight = [], [], []
    for rows in train.values():
        label = next(iter(rows.values()))["warm_position"]
        if label is None:
            continue
        for d, p in weights.items():
            x.append(feature(rows[d], kind))
            y.append(label)
            sample_weight.append(p)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
    model.fit(np.asarray(x), np.asarray(y), logisticregression__sample_weight=np.asarray(sample_weight))
    expected_hits = 0.0
    for rows in test.values():
        label = next(iter(rows.values()))["warm_position"]
        if label is None:
            continue
        expected_hits += sum(p * (int(model.predict(feature(rows[d], kind)[None, :])[0]) == label)
                             for d, p in weights.items())
    return round(expected_hits, 3)


def main(output):
    source_rows = {name: read_source(name, folder) for name, folder in SOURCES.items()}
    component_rows = {name: {trial["group"]: {d: outcome(trial, items, d) for d in SLOTS}
                             for trial, items in rows}
                      for name, rows in source_rows.items()}
    sessions = {name: {group: values for source in sources
                       for group, values in component_rows[source].items()}
                for name, sources in SESSIONS.items()}
    result = {"protocol": {"slots_ms": SLOTS, "policies": POLICIES,
                           "client_model": "ideal slot/fallback, fixed label-independent shuffle, 2ms serialization; no jitter/network/backend feedback",
                           "training": "64 older positive groups; 32 already-inspected separate C0 positive groups for cross-session check",
                           "MMD": "mean of six pairwise biased Gaussian-kernel MMD squared values; four complete client times/ID ranks; fixed 50ms and 0.25 scales; 999 balanced-label permutations; old two sessions permuted as paired case sequences",
                           "risk": "fraction of groups with any late response; internal availability metric, not attacker feature"},
              "sessions": {}}
    for name, groups in sessions.items():
        result["sessions"][name] = {}
        for policy, weights in POLICIES.items():
            cost = sum(sum(p * rows[d]["mean_wait_ms"] for d, p in weights.items())
                       for rows in groups.values()) / len(groups)
            risk = sum(sum(p * rows[d]["fallback"] for d, p in weights.items())
                       for rows in groups.values()) / len(groups)
            result["sessions"][name][policy] = {
                "mean_individual_wait_ms": round(cost, 4),
                "group_fallback_risk": round(risk, 4),
                "expected_fallback_groups": round(risk * len(groups), 4),
                **distinguishability(groups, weights, seed=20261102),
            }
    for policy, weights in POLICIES.items():
        result["sessions"]["separate_c0"][policy]["expected_T2_hits_of_32"] = \
            attack(sessions["development"], sessions["separate_c0"], weights, "T2")
        result["sessions"]["separate_c0"][policy]["expected_RT_hits_of_32"] = \
            attack(sessions["development"], sessions["separate_c0"], weights, "RT")
    with output.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    with output.with_name(output.stem + "-components.jsonl").open("x") as f:
        for source, groups in component_rows.items():
            for rows in groups.values():
                for d in SLOTS:
                    f.write(json.dumps({"source": source, **rows[d]}) + "\n")
    for policy in POLICIES:
        dev = result["sessions"]["development"][policy]
        test = result["sessions"]["separate_c0"][policy]
        print(policy, "dev", dev["mean_individual_wait_ms"], dev["group_fallback_risk"],
              dev["mmd2_full_trace"], "test", test["mean_individual_wait_ms"],
              test["group_fallback_risk"], test["mmd2_full_trace"],
              test["expected_T2_hits_of_32"])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
