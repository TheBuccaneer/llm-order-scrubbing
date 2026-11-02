"""Compare fixed and simple trained client-only observers across sessions."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1] / "results"
FILES = {
    "bos_dev": "bos-pilot-20261102/trials-extended.jsonl",
    "bos_holdout": "bos-holdout-20261102/trials.jsonl",
    "sanitized": "bos-sanitized-20261102/trials.jsonl",
    "slot_pilot": "bos-slot-20261102/trials-pilot.jsonl",
    "slot_followup": "bos-slot-20261102/trials-extended.jsonl",
}


def load(name, mode):
    rows = [json.loads(line) for line in (ROOT / FILES[name]).read_text().splitlines()]
    return [x for x in rows if x["mode"] == mode and x["warm"]]


def data(rows, feature):
    X, y = [], []
    for r in rows:
        order = r["send_order"]
        receives = {label: r["probes"][label]["received_ns"] for label in order}
        ranked = sorted(order, key=lambda label: receives[label])
        rank_by_pos = [ranked.index(label) for label in order]
        rank_matrix = [int(rank_by_pos[i] == j) for i in range(4) for j in range(4)]
        t0 = min(r["probes"][label]["sent_ns"] for label in order)
        time_by_pos = [(receives[label] - t0) / 1e6 for label in order]
        if feature == "R2": x = rank_matrix
        elif feature == "T1": x = [min(time_by_pos)]
        elif feature == "T2": x = time_by_pos
        elif feature == "RT": x = rank_matrix + time_by_pos
        else: raise ValueError(feature)
        X.append(x)
        y.append(order.index(r["warm"]))
    return np.asarray(X), np.asarray(y)


def score(actual, predicted):
    n = len(actual)
    hits = int(np.sum(actual == predicted))
    ci = binomtest(hits, n).proportion_ci(confidence_level=0.95, method="wilson")
    return {"n": n, "hits": hits, "accuracy": round(hits / n, 4),
            "balanced_accuracy": round(float(balanced_accuracy_score(actual, predicted)), 4),
            "wilson95": [round(ci.low, 4), round(ci.high, 4)],
            "chance_p_one_sided": round(float(binomtest(hits, n, 0.25, alternative="greater").pvalue), 8),
            "confusion_actual_predicted": confusion_matrix(actual, predicted, labels=range(4)).tolist()}


def rank1(rows):
    actual, predicted = [], []
    for r in rows:
        order = r["send_order"]
        actual.append(order.index(r["warm"]))
        first = min(order, key=lambda label: r["probes"][label]["received_ns"])
        predicted.append(order.index(first))
    return score(np.array(actual), np.array(predicted))


def evaluate(train_name, test_name, mode):
    train, test = load(train_name, mode), load(test_name, mode)
    result = {"train_session": train_name, "test_session": test_name,
              "mode": mode, "train_n": len(train), "R1": rank1(test)}
    for feature in ("R2", "T1", "T2", "RT"):
        xtr, ytr = data(train, feature)
        xte, yte = data(test, feature)
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        model.fit(xtr, ytr)
        result[feature] = score(yte, model.predict(xte))
    return result


def main(path):
    comparisons = [
        ("bos_dev", "bos_holdout", "bos4"),
        ("bos_dev", "sanitized", "bos4"),
        ("bos_dev", "bos_holdout", "d250"),
        ("bos_dev", "sanitized", "d250"),
        ("slot_pilot", "slot_followup", "slot1050"),
        ("slot_pilot", "sanitized", "slot1050"),
    ]
    results = [evaluate(*x) for x in comparisons]
    Path(path).write_text(json.dumps(results, indent=2) + "\n")
    for r in results:
        print(r["train_session"], r["test_session"], r["mode"],
              {k: r[k]["hits"] for k in ("R1", "R2", "T1", "T2", "RT")})


if __name__ == "__main__":
    main(sys.argv[1])
