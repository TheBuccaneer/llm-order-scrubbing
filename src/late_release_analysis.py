"""Audit fixed-slot live runs and replay paired costs on earlier traces."""

import json
import math
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
NEW = ROOT / "results/late-release-20261102"
OLD = (ROOT / "results/decision-validation-20261102/slot-fallback/holdout",
       ROOT / "results/decision-validation-20261102/slot-fallback/confirm",
       ROOT / "results/release-boundary-20261102/c0")


def stats(values):
    ordered = sorted(values)
    return {"n": len(values), "median": round(statistics.median(values), 3),
            "p95": round(ordered[math.ceil(.95 * len(ordered)) - 1], 3),
            "max": round(ordered[-1], 3)}


def load(folder, filename="trials.jsonl"):
    trials = [json.loads(s) for s in (folder / filename).read_text().splitlines()]
    proxy = [json.loads(s) for s in (folder / "proxy.jsonl").read_text().splitlines()]
    by_id = {x["request_id"]: x for x in proxy}
    assert len(by_id) == len(proxy) == 4 * len(trials)
    return trials, by_id


def audit(folder):
    trials, by_id = load(folder)
    all_wait, warm_wait, all_e2e, warm_e2e = [], [], [], []
    reasons, full, offsets = Counter(), 0, []
    for trial in trials:
        assert trial["mode"] == "slot1200" and trial["output_tokens"] == 24
        assert set(trial["send_order"]) == set("ABCD")
        rows = []
        for label, p in trial["probes"].items():
            x = by_id[p["request_id"]]
            assert (x["group"], x["label"], x["mode"]) == (trial["group"], label, "slot1200")
            assert p["http_status"] == 200 and p["prompt_tokens"] == 548 and p["completion_tokens"] == 24
            assert p["cached_tokens_reported"] is None and x["cache_details_removed"]
            assert p["sent_ns"] <= x["arrival_ns"] <= x["backend_received_ns"] <= x["release_ns"] <= p["received_ns"]
            assert x["cached_tokens_reported"] == (544 if label == trial["warm"] else None)
            reasons[x["flush_reason"]] += 1
            e2e = (p["received_ns"] - p["sent_ns"]) / 1e6
            all_wait.append(x["added_wait_ms"])
            all_e2e.append(e2e)
            if label == trial["warm"]:
                warm_wait.append(x["added_wait_ms"])
                warm_e2e.append(e2e)
            rows.append(x)
        full += all(x["batch_size"] == 4 for x in rows)
        offsets.append((max(x["backend_received_ns"] for x in rows) -
                        min(x["arrival_ns"] for x in rows)) / 1e6)
    positives = [t for t in trials if t["warm"]]
    return {"groups": len(trials), "positive": len(positives),
            "unwarmed": len(trials) - len(positives), "responses": len(by_id),
            "position_counts": dict(Counter(t["send_order"].index(t["warm"]) + 1 for t in positives)),
            "case_seed": list({t["case_seed"] for t in trials}),
            "full_groups": full, "flush_reasons": dict(reasons),
            "backend_last_offset_ms": stats(offsets),
            "proxy_wait_all_ms": stats(all_wait), "proxy_wait_warm_ms": stats(warm_wait),
            "e2e_all_ms": stats(all_e2e), "e2e_warm_ms": stats(warm_e2e)}


def attack():
    train = [x for x in load(NEW / "dev")[0] if x["warm"]]
    test = [x for x in load(NEW / "holdout")[0] if x["warm"]]
    out = {"train_n": len(train), "test_n": len(test), "R1": rank1(test)}
    for feature in ("T1", "T2", "RT"):
        xtr, ytr = data(train, feature)
        xte, yte = data(test, feature)
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
        model.fit(xtr, ytr)
        out[feature] = score(yte, model.predict(xte))
    gaps = []
    for t in test:
        arrivals = sorted(p["received_ns"] for p in t["probes"].values())
        gaps.append(max((b - a) / 1e6 for a, b in zip(arrivals, arrivals[1:])))
    out["client_gap_gt10ms"] = sum(g > 10 for g in gaps)
    out["max_client_gap_ms"] = round(max(gaps), 3)
    return out


def paired_replay():
    all_old, all_new, all_diff, warm_diff, last_offsets = [], [], [], [], []
    counts = Counter()
    for folder in OLD:
        name = "trials.jsonl" if folder.name == "c0" else "trials-24.jsonl"
        trials, by_id = load(folder, name)
        for t in trials:
            rows = {label: by_id[p["request_id"]] for label, p in t["probes"].items()}
            anchor = min(x["arrival_ns"] for x in rows.values())
            last = max(x["backend_received_ns"] for x in rows.values())
            last_offsets.append((last - anchor) / 1e6)
            counts["groups"] += 1
            counts["ready_at_1200"] += last <= anchor + 1_200_000_000
            counts["ready_at_1050"] += last <= anchor + 1_050_000_000
            for label, x in rows.items():
                backend = x["backend_received_ns"]
                old = max(0, (anchor + 1_050_000_000 - backend) / 1e6)
                new = max(0, (anchor + 1_200_000_000 - backend) / 1e6)
                all_old.append(old)
                all_new.append(new)
                all_diff.append(new - old)
                if label == t["warm"]:
                    warm_diff.append(new - old)
    return {"groups": dict(counts), "last_backend_offset_ms": stats(last_offsets),
            "ideal_wait_1050_ms": stats(all_old), "ideal_wait_1200_ms": stats(all_new),
            "paired_individual_wait_difference_ms": stats(all_diff),
            "paired_warm_wait_difference_ms": stats(warm_diff),
            "method": "Idealized proxy readiness on the same recorded traces; excludes timer jitter, serial sends and backend feedback."}


def main(output):
    result = {"dev": audit(NEW / "dev"), "holdout": audit(NEW / "holdout"),
              "attack": attack(), "paired_replay": paired_replay()}
    with output.open("x") as f:
        json.dump(result, f, indent=2, default=lambda x: x.item() if isinstance(x, np.generic) else x)
        f.write("\n")
    print("holdout full", result["holdout"]["full_groups"], "/", result["holdout"]["groups"])
    print("attack", {k: result["attack"][k]["hits"] for k in ("R1", "T1", "T2", "RT")})
    print("paired wait delta", result["paired_replay"]["paired_individual_wait_difference_ms"])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
