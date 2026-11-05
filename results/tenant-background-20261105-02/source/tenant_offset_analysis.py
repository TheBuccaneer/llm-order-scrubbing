"""Frozen B-only attack transfer to hidden victim-start offsets."""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, mannwhitneyu
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from tenant_scheduler_analysis import client_features, first_time, score


FEATURES = ("R2", "T1", "T2", "RT")


def load_old_development(root):
    path = root / "results/tenant-scheduler-20261103/dev/trials.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()
            if json.loads(line)["condition"] in ("warm", "cold")]


def load_cases(folder):
    plan = json.loads((folder / "cases.json").read_text())["cases"]
    rows = []
    for case in plan:
        run = folder / f"case-{case['index']:02d}"
        row = json.loads((run / "trial.json").read_text())
        proxy = [json.loads(line) for line in (run / "proxy.jsonl").read_text().splitlines()]
        rows.append((case, row, proxy))
    return rows


def integrity(folder, runs):
    salts = json.loads((folder / "salts.json").read_text())
    errors = []
    if len(runs) != 24 or salts["tenant_A"] == salts["tenant_B"]:
        errors.append("plan count or tenant salts")
    overlaps = Counter()
    actual_offsets = {}
    for case, row, proxy in runs:
        i = case["index"]
        if any(row[key] != case[key] for key in ("index", "pair", "condition",
                                                "victim_offset_ms", "send_order")):
            errors.append(f"{i} case plan mismatch")
        if row["a_salt"] != salts["tenant_A"] or row["b_salt"] != salts["tenant_B"]:
            errors.append(f"{i} salt mismatch")
        prep = row["preparation"]
        if (prep["http_status"], prep["prompt_tokens"], prep["completion_tokens"],
            prep["cached_tokens_reported"]) != (200, 548, 1, None):
            errors.append(f"{i} preparation")
        target = row["victim_target"]
        condition = case["condition"]
        if condition == "absent":
            if target is not None:
                errors.append(f"{i} absent target")
        else:
            expected_cache = 544 if condition == "warm" else None
            if target is None or (target["http_status"], target["prompt_tokens"],
                                  target["completion_tokens"], target["cached_tokens_reported"]) != (
                                  200, 548, 16, expected_cache):
                errors.append(f"{i} target/cache")
            else:
                b_intervals = [(p["sent_ns"], p["received_ns"]) for p in row["probes"].values()]
                overlap = any(target["sent_ns"] < end and target["received_ns"] > start
                              for start, end in b_intervals)
                overlaps[condition] += int(overlap)
                actual_offsets[str(i)] = round((target["sent_ns"] - min(start for start, _ in b_intervals)) / 1e6, 3)
        by_id = {p.get("request_id"): p for p in proxy}
        if len(proxy) != 4 or len(by_id) != 4:
            errors.append(f"{i} proxy count")
        for label in row["send_order"]:
            b = row["probes"][label]
            p = by_id.get(b["request_id"])
            if (b["http_status"], b["prompt_tokens"], b["completion_tokens"],
                b["cached_tokens_reported"]) != (200, 548, 16, None):
                errors.append(f"{i} {label} B response")
            if p is None or (p["group"], p["label"], p["mode"], p["batch_size"],
                             p["cached_tokens_reported"], p["cache_details_removed"]) != (
                             row["group"], label, "direct", 1, None, True):
                errors.append(f"{i} {label} B proxy/cache")
    return {"cases": len(runs), "errors": errors, "error_count": len(errors),
            "victim_B_request_interval_overlap": dict(overlaps),
            "actual_victim_start_offset_ms_by_case": actual_offsets}


def main(root, folder, output):
    old = load_old_development(root)
    runs = load_cases(folder)
    audit = integrity(folder, runs)
    primary = [r for _, r, _ in runs if r["condition"] in ("warm", "cold")]
    controls = [r for _, r, _ in runs if r["condition"] in ("absent", "other_cold")]
    ytr = np.array([int(r["condition"] == "warm") for r in old])
    y = np.array([int(r["condition"] == "warm") for r in primary])
    result = {"training": "results/tenant-scheduler-20261103/dev/trials.jsonl (16 groups, frozen before this pilot)",
              "integrity": audit,
              "condition_counts": dict(Counter(r["condition"] for _, r, _ in runs)),
              "attacker": {}}
    predictions = {}
    for feature in FEATURES:
        model = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000))
        model.fit(np.array([client_features(r, feature) for r in old]), ytr)
        pred = model.predict(np.array([client_features(r, feature) for r in primary]))
        result["attacker"][feature] = score(y, pred)
        predictions[feature] = {r["index"]: int(p) for r, p in zip(primary, pred)}
        control_pred = model.predict(np.array([client_features(r, feature) for r in controls]))
        result["attacker"][feature]["control_predictions_warm"] = {
            condition: int(sum(p for r, p in zip(controls, control_pred) if r["condition"] == condition))
            for condition in ("absent", "other_cold")}
    old_warm = [first_time(r) for r in old if r["condition"] == "warm"]
    old_cold = [first_time(r) for r in old if r["condition"] == "cold"]
    direction = 1 if np.median(old_warm) >= np.median(old_cold) else -1
    warm = [direction * first_time(r) for r in primary if r["condition"] == "warm"]
    cold = [direction * first_time(r) for r in primary if r["condition"] == "cold"]
    mw = mannwhitneyu(warm, cold, alternative="greater", method="exact")
    result["T1_rank"] = {"direction_from_prior_development": "warm_later" if direction == 1 else "warm_earlier",
                         "auc": round(float(mw.statistic / (len(warm) * len(cold))), 4),
                         "one_sided_exact_p": round(float(mw.pvalue), 7),
                         "median_ms_by_condition": {condition: round(float(np.median([first_time(r) for _, r, _ in runs
                             if r["condition"] == condition])), 3)
                             for condition in ("warm", "cold", "absent", "other_cold")}}
    pairs = []
    for pair in range(8):
        r = {row["condition"]: row for row in primary if row["pair"] == pair}
        assert set(r) == {"warm", "cold"}
        assert r["warm"]["victim_offset_ms"] == r["cold"]["victim_offset_ms"]
        assert r["warm"]["send_order"] == r["cold"]["send_order"]
        pairs.append({"pair": pair, "offset_ms": r["warm"]["victim_offset_ms"],
                      "signed_warm_minus_cold_ms": round(direction * (first_time(r["warm"]) -
                                                              first_time(r["cold"])), 3),
                      "T1_both_correct": (predictions["T1"][r["warm"]["index"]] == 1 and
                                          predictions["T1"][r["cold"]["index"]] == 0)})
    consistent = sum(p["signed_warm_minus_cold_ms"] > 0 for p in pairs)
    ci = binomtest(consistent, len(pairs)).proportion_ci(confidence_level=.95, method="wilson")
    result["pairs"] = {"rows": pairs, "consistent": consistent, "n": len(pairs),
                       "wilson95_consistent_fraction": [round(ci.low, 4), round(ci.high, 4)],
                       "one_sided_sign_p": round(float(binomtest(consistent, len(pairs), .5,
                                                                 alternative="greater").pvalue), 6)}
    result["decision_guide_met"] = (audit["error_count"] == 0 and
        audit["victim_B_request_interval_overlap"].get("warm") == 8 and
        audit["victim_B_request_interval_overlap"].get("cold") == 8 and
        (consistent >= 7 or (result["T1_rank"]["auc"] >= .75 and
                             result["attacker"]["T1"]["hits"] >= 12)))
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("integrity",audit["error_count"],"T1",result["attacker"]["T1"]["hits"],
          "T2",result["attacker"]["T2"]["hits"],"AUC",result["T1_rank"]["auc"],
          "pairs",consistent,"/8","decision",result["decision_guide_met"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
