"""Freeze a one-feature client-time rule on one run and score a later run."""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def observations(path: Path, mode: str) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        trial = json.loads(line)
        if trial["mode"] != mode or trial["warm"] is None:
            continue
        probes = trial["probes"]
        sent = sorted(probes, key=lambda label: probes[label]["sent_ns"])
        received = sorted(probes, key=lambda label: probes[label]["received_ns"])
        rows.append({
            "position": sent.index(trial["warm"]) + 1,
            "first_reply_ms": (
                min(item["received_ns"] for item in probes.values())
                - min(item["sent_ns"] for item in probes.values())
            ) / 1e6,
            "first_reply_label": received[0],
            "warm_label": trial["warm"],
        })
    return rows


def score(centers: dict[int, float], rows: list[dict]) -> dict:
    confusion = Counter()
    rank_correct = 0
    for row in rows:
        predicted = min(centers, key=lambda position: abs(
            row["first_reply_ms"] - centers[position]
        ))
        confusion[(row["position"], predicted)] += 1
        rank_correct += row["first_reply_label"] == row["warm_label"]
    timing_correct = sum(n for (actual, predicted), n in confusion.items()
                         if actual == predicted)
    return {
        "trials": len(rows),
        "timing_correct": timing_correct,
        "rank_first_correct": rank_correct,
        "confusion_actual_predicted": {
            f"{actual}->{predicted}": count
            for (actual, predicted), count in sorted(confusion.items())
        },
        "first_reply_ms_by_position": {
            str(position): {
                "median": statistics.median(
                    row["first_reply_ms"] for row in rows
                    if row["position"] == position
                ),
                "min": min(row["first_reply_ms"] for row in rows
                           if row["position"] == position),
                "max": max(row["first_reply_ms"] for row in rows
                           if row["position"] == position),
            }
            for position in range(1, 5)
        },
    }


def main(
    training: Path, holdout: Path, output: Path,
    training_mode: str, holdout_modes: tuple[str, ...],
) -> None:
    train = observations(training, training_mode)
    centers = {
        position: statistics.median(row["first_reply_ms"] for row in train
                                    if row["position"] == position)
        for position in range(1, 5)
    }
    result = {
        "feature": "first_client_reply_ns minus first_client_send_ns, in ms",
        "rule": "nearest training median for warm send position; map position to known send order",
        "training_file": str(training),
        "training_mode": training_mode,
        "training_warm_trials": len(train),
        "centers_ms": centers,
        "holdout_file": str(holdout),
        "holdout": {
            mode: score(centers, observations(holdout, mode))
            for mode in holdout_modes
        },
    }
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    mode = sys.argv[4] if len(sys.argv) > 4 else "bos4"
    holdout_modes = tuple(sys.argv[5].split(",")) if len(sys.argv) > 5 else ("bos4", "d250")
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), mode, holdout_modes)
