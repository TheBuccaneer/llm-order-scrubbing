"""Frozen B-only observer for the separate-salt two-tenant pilot."""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURES = ("R2", "T1", "T2", "RT")


def load(folder):
    trials = [json.loads(s) for s in (folder / "trials.jsonl").read_text().splitlines()]
    proxy = [json.loads(s) for s in (folder / "proxy.jsonl").read_text().splitlines()]
    return trials, proxy


def client_features(row, feature):
    order = row["send_order"]
    probes = row["probes"]
    receive = {label: probes[label]["received_ns"] for label in order}
    ranked = sorted(order, key=receive.get)
    ranks = [ranked.index(label) for label in order]
    matrix = [int(ranks[i] == j) for i in range(4) for j in range(4)]
    t0 = min(probes[label]["sent_ns"] for label in order)
    times = [(receive[label] - t0) / 1e6 for label in order]
    return {"R2": matrix, "T1": [min(times)], "T2": times,
            "RT": matrix + times}[feature]


def first_time(row):
    return client_features(row, "T1")[0]


def integrity(trials, proxy):
    errors = []
    by_id = {p["request_id"]: p for p in proxy if "request_id" in p}
    if len(proxy) != len(by_id) or len(proxy) != 4 * len(trials):
        errors.append("proxy response count/IDs")
    if len({r["a_salt"] for r in trials}) != len(trials) or len({r["b_salt"] for r in trials}) != len(trials):
        errors.append("reused salt")
    for r in trials:
        if r["a_salt"] == r["b_salt"] or len(r["a_salt"]) != 64 or len(r["b_salt"]) != 64:
            errors.append(f"{r['trial']} salt separation")
        prep = r["preparation"]
        if prep["http_status"] != 200 or prep["prompt_tokens"] != 548 or prep["completion_tokens"] != 1:
            errors.append(f"{r['trial']} preparation")
        victim = r["victim_target"]
        if r["condition"] == "absent":
            if victim is not None:
                errors.append(f"{r['trial']} absent victim")
        elif victim is None or (victim["http_status"], victim["prompt_tokens"],
               victim["completion_tokens"], victim["cached_tokens_reported"]) != (
               200, 548, 16, 544 if r["condition"] == "warm" else None):
            errors.append(f"{r['trial']} victim target/cache")
        for label in r["send_order"]:
            q = r["probes"][label]
            p = by_id.get(q["request_id"])
            if (q["http_status"], q["prompt_tokens"], q["completion_tokens"],
                q["cached_tokens_reported"]) != (200, 548, 16, None):
                errors.append(f"{r['trial']} {label} client response")
            expected_batch = 4 if r["mode"] == "bos4" else 1
            if p is None or (p["group"], p["label"], p["mode"], p["batch_size"],
                             p["cached_tokens_reported"], p["cache_details_removed"]) != (
                             r["group"], label, r["mode"], expected_batch, None, True):
                errors.append(f"{r['trial']} {label} proxy/cache")
        if r["mode"] == "bos4":
            items = [by_id.get(r["probes"][label]["request_id"]) for label in r["send_order"]]
            if any(p is None or p["flush_reason"] != "full" for p in items) or sorted(
                    p["release_position"] for p in items if p is not None) != [1, 2, 3, 4]:
                errors.append(f"{r['trial']} incomplete BOS block")
    pairs = {}
    for r in trials:
        if r["pair"] is not None:
            pairs.setdefault(r["pair"], []).append(r)
    if any(len(rows) != 2 or {r["condition"] for r in rows} != {"warm", "cold"}
           or rows[0]["send_order"] != rows[1]["send_order"] for rows in pairs.values()):
        errors.append("unmatched or unbalanced pair")
    return {"groups": len(trials), "responses": len(proxy),
            "conditions": dict(Counter(r["condition"] for r in trials)),
            "pairs": len(pairs), "error_count": len(errors), "errors": errors[:20]}


def score(y, predicted):
    hits = int(np.sum(y == predicted))
    ci = binomtest(hits, len(y)).proportion_ci(confidence_level=.95, method="wilson")
    return {"hits": hits, "n": len(y), "accuracy": round(hits / len(y), 4),
            "wilson95": [round(ci.low, 4), round(ci.high, 4)],
            "one_sided_p_vs_half": round(float(binomtest(hits, len(y), .5, alternative="greater").pvalue), 6),
            "confusion_cold_warm": confusion_matrix(y, predicted, labels=[0, 1]).tolist()}


def main(root, output):
    dev, dev_proxy = load(root / "dev")
    test, test_proxy = load(root / "holdout")
    train = [r for r in dev if r["condition"] != "absent"]
    hold = [r for r in test if r["condition"] != "absent"]
    ytr = np.array([int(r["condition"] == "warm") for r in train])
    yte = np.array([int(r["condition"] == "warm") for r in hold])
    result = {"development_integrity": integrity(dev, dev_proxy),
              "holdout_integrity": integrity(test, test_proxy)}
    dev_warm = np.array([first_time(r) for r in train if r["condition"] == "warm"])
    dev_cold = np.array([first_time(r) for r in train if r["condition"] == "cold"])
    direction = 1 if np.median(dev_warm) >= np.median(dev_cold) else -1
    warm = np.array([first_time(r) * direction for r in hold if r["condition"] == "warm"])
    cold = np.array([first_time(r) * direction for r in hold if r["condition"] == "cold"])
    auc = float(mannwhitneyu(warm, cold).statistic / (len(warm) * len(cold)))
    rng = np.random.default_rng(202611032603)
    boot = []
    for _ in range(4000):
        a, b = rng.choice(warm, len(warm))[:, None], rng.choice(cold, len(cold))[None, :]
        boot.append(float(np.mean((a > b) + .5 * (a == b))))
    result["T1_rank_test"] = {"direction_from_development": "warm_later" if direction == 1 else "warm_earlier",
                              "auc": round(auc, 4),
                              "bootstrap95": [round(v, 4) for v in np.quantile(boot, [.025, .975])],
                              "median_ms": {condition: round(float(np.median([first_time(r) for r in test if r["condition"] == condition])), 3)
                                            for condition in ("warm", "cold", "absent")}}
    pair_delta = []
    for pair in sorted({r["pair"] for r in hold}):
        rows = {r["condition"]: r for r in hold if r["pair"] == pair}
        pair_delta.append(direction * (first_time(rows["warm"]) - first_time(rows["cold"])))
    consistent = sum(x > 0 for x in pair_delta)
    result["matched_test_pairs"] = {"n": len(pair_delta), "direction_consistent": consistent,
                                    "median_signed_warm_minus_cold_ms": round(float(np.median(pair_delta)), 3),
                                    "one_sided_sign_p": round(float(binomtest(consistent, len(pair_delta), .5,
                                                                           alternative="greater").pvalue), 6)}
    result["R1_first_b_send_position"] = {condition: dict(sorted(Counter(r["send_order"].index(
        min(r["send_order"], key=lambda label: r["probes"][label]["received_ns"])) + 1
        for r in hold if r["condition"] == condition).items())) for condition in ("warm", "cold")}
    result["proxy_added_wait_ms"] = {
        "median": round(float(np.median([p["added_wait_ms"] for p in test_proxy])), 3),
        "p95": round(float(np.quantile([p["added_wait_ms"] for p in test_proxy], .95)), 3)}
    result["victim_target_e2e_median_ms"] = {condition: round(float(np.median([
        (r["victim_target"]["received_ns"] - r["victim_target"]["sent_ns"]) / 1e6
        for r in hold if r["condition"] == condition])), 3) for condition in ("warm", "cold")}
    for feature in FEATURES:
        xtr = np.array([client_features(r, feature) for r in train])
        xte = np.array([client_features(r, feature) for r in hold])
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
        model.fit(xtr, ytr)
        result[feature] = score(yte, model.predict(xte))
    result["decision_guide_met"] = (result["development_integrity"]["error_count"] == 0 and
        result["holdout_integrity"]["error_count"] == 0 and
        (hold[0]["mode"] == "bos4" or consistent >= 12) and
        (auc >= .75 or result["T2"]["hits"] >= 24))
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("integrity",result["holdout_integrity"]["error_count"],"AUC",auc,
          "pairs",consistent,"/",len(pair_delta),"T2",result["T2"]["hits"],"/",len(yte),
          "decision",result["decision_guide_met"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
