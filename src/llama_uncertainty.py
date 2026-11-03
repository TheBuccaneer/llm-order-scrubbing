"""Post-measurement uncertainty intervals; does not fit or alter attackers."""

import json
import sys
from pathlib import Path

import numpy as np

from llama_bos_analysis import first_time


def load(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def auc_interval(rows, seed, direction):
    pos = np.array([direction * first_time(r) for r in rows
                    if r["warm"] and r["send_order"].index(r["warm"]) == 0])
    neg = np.array([direction * first_time(r) for r in rows
                    if r["warm"] and r["send_order"].index(r["warm"]) != 0])
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(4000):
        a = rng.choice(pos, len(pos))[:, None]
        b = rng.choice(neg, len(neg))[None, :]
        draws.append(float(np.mean((a > b) + .5 * (a == b))))
    return [round(v, 4) for v in np.quantile(draws, [.025, .975])]


def paired_interval(rows, proxy, field, seed):
    by_id = {p["request_id"]: p for p in proxy}
    groups = {}
    for r in rows:
        if not r["warm"]:
            continue
        records = [by_id[r["probes"][label]["request_id"]] for label in r["send_order"]]
        value = first_time(r) if field == "client_block_ms" else (
            max(p["backend_received_ns"] for p in records) -
            min(p["arrival_ns"] for p in records)) / 1e6
        key = (r["warm"], tuple(r["send_order"]))
        groups[(r["structure"], key)] = value
    by_pos = [[] for _ in range(4)]
    for (structure, (warm, order)), v in groups.items():
        if structure == "p0":
            by_pos[order.index(warm)].append(groups[("p1", (warm, order))] - v)
    rng = np.random.default_rng(seed)
    draws = [float(np.median([v for cell in by_pos for v in rng.choice(cell, len(cell))]))
             for _ in range(4000)]
    return [round(v, 3) for v in np.quantile(draws, [.025, .975])]


def main(root, output):
    result = {}
    for index, config in enumerate(("c0", "c1")):
        dev = [r for r in load(root / f"bos-dev-{config}" / "trials.jsonl") if r["warm"]]
        a = [first_time(r) for r in dev if r["send_order"].index(r["warm"]) == 0]
        b = [first_time(r) for r in dev if r["send_order"].index(r["warm"]) != 0]
        direction = 1 if np.mean(np.asarray(a)[:, None] > np.asarray(b)[None, :]) >= .5 else -1
        bos = load(root / f"bos-test-{config}" / "trials.jsonl")
        docs = load(root / f"docs-{config}" / "trials.jsonl")
        proxy = load(root / f"docs-{config}" / "proxy.jsonl")
        result[config] = {
            "bos_binary_auc_bootstrap95": auc_interval(bos, 202611032401+index, direction),
            "document_binary_auc_bootstrap95": {
                structure: auc_interval([r for r in docs if r["structure"] == structure],
                                        202611032411+index*2+j, direction)
                for j, structure in enumerate(("p0", "p1"))},
            "document_paired_p1_minus_p0_median_bootstrap95_ms": {
                field: paired_interval(docs, proxy, field, 202611032421+index*2+j)
                for j, field in enumerate(("backend_last_ms", "client_block_ms"))}}
    output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
