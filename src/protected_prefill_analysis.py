"""Checks the implemented phase boundary and reports bounded pilot costs.

No new attacker/model: first B completion and paired timing differences
are the project's existing diagnostic. Small sample sizes stay explicit.
"""

import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def stats(values):
    a=np.asarray(values,dtype=float)
    return dict(n=len(a),median=float(np.median(a)),mean=float(np.mean(a)),
                minimum=float(a.min()),maximum=float(a.max()))


def canonical(row):
    state=copy.deepcopy(row["protected"]["normalization_result"]["pool_state"])
    state.pop("canonical_generation")
    ids=[r["request_id"] for r in row["protected"]["join_snapshot"]["requests"]]
    names={rid:f"{rid[0]}:{i}" for i,rid in enumerate(ids)}
    for tenant in state["tenants"].values():
        for field in ("request_blocks","request_cached_blocks"):
            tenant[field]={names[rid]:v for rid,v in tenant[field].items()}
    return state


def analyze(folder):
    path=folder/"trials.jsonl"
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    protected=[r for r in rows if r["mode"] in ("protected","protected_block512")]
    references={r["mode"]:canonical(r) for r in protected}
    errors=[]
    for row in protected:
        p=row["protected"];state=p["join_snapshot"]
        if not p["joined"] or not p["physical_normalizer_applied"]:
            errors.append("missing physical join")
        if state["waiting"] or state["inflight"]:
            errors.append("nonempty waiting/inflight")
        if (state.get("scheduled_token_budget",256)!=256 or
            state.get("prefill_chunk_threshold",64)!=64):
            errors.append("private scheduling limits escaped into shared decode")
        config=next(e for e in p["trace"] if e["event"]=="configure")
        join_event=next(e for e in p["trace"] if e["event"]=="join")
        normal_end=next(e for e in p["trace"] if e["event"]=="normalization_end")
        if join_event["elapsed_ms"]<config["join_ms"] or normal_end["elapsed_ms"]>config["join_ms"]:
            errors.append("shared join preceded public time or normalization missed deadline")
        if any(r["computed_tokens"]!=548 or r["output_tokens"]!=1 or r["preemptions"]
               for r in state["requests"]):
            errors.append("wrong first-token frontier")
        if canonical(row)!=references[row["mode"]]:
            errors.append("canonical metadata differs")
        schedule=[e for e in p["trace"] if e["event"]=="schedule"]
        for step in schedule:
            if step["phase"]=="prefill" and any(not rid.startswith(step["owner"]+":")
                                               for rid in step["scheduled_tokens"]):
                errors.append("foreign prefill execution")
        shared=[e for e in schedule if e["phase"]=="shared_decode"]
        if len(shared)!=15 or any(len(s["scheduled_tokens"])!=5 or
            set(s["scheduled_tokens"].values())!={1} for s in shared):
            errors.append("shared decode does not contain full five-request fixed cohort")
        if len(shared[0]["remapped_ids"])!=5:
            errors.append("worker block-table transport missing")
        expected=512 if row["condition"]=="warm" else 0
        if row["requests"][0]["cached_tokens"]!=expected:
            errors.append("wrong private A hit")
        if row["mode"]=="protected_block512":
            for owner in "AB":
                steps=[s for s in schedule if s["phase"]=="prefill" and s["owner"]==owner]
                expected_chunks=[36] if owner=="A" and row["condition"]=="warm" else [512,36]
                if [set(s["scheduled_tokens"].values()) for s in steps]!=[{n} for n in expected_chunks]:
                    errors.append("structural block recipe differs")
    for row in rows:
        if any(len(r["token_ids"])!=16 or r["prompt_tokens"]!=548 for r in row["requests"]):
            errors.append("incomplete/incorrectly shaped response")
        if any(r["cached_tokens"] for r in row["requests"] if r["tenant"]=="B"):
            errors.append("B unexpectedly reused cache")
    result=dict(status="functional exploratory pilot, no privacy guarantee or confirmed cost dominance",
        input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        groups=len(rows),responses=sum(len(r["requests"]) for r in rows),
        phase_checks=dict(errors=errors,canonical_metadata_equal=not errors,
                          protected_groups=len(protected)),policies={})
    for mode in sorted({r["mode"] for r in rows}):
        selected=[r for r in rows if r["mode"]==mode]
        costs={}
        for condition in ("cold","warm"):
            chosen=[r for r in selected if r["condition"]==condition]
            first=[]
            for row in chosen:
                b=[r for r in row["requests"] if r["tenant"]=="B"]
                first.append((min(r["released_ns"] for r in b)-min(r["sent_ns"] for r in b))/1e6)
            costs[condition]=dict(groups=len(chosen),
                A_e2e_ms=stats([r["e2e_ms"] for row in chosen for r in row["requests"] if r["tenant"]=="A"]),
                B_e2e_ms=stats([r["e2e_ms"] for row in chosen for r in row["requests"] if r["tenant"]=="B"]),
                first_B_ms=stats(first),
                scheduled_model_tokens=stats([r["model_tokens_scheduled"] for r in chosen]) if "model_tokens_scheduled" in chosen[0] else None,
                inference_cuda_ms=stats([r["inference_cuda_intervals_ms"] for r in chosen]) if "inference_cuda_intervals_ms" in chosen[0] else None,
                late_B=sum(bool(r.get("late")) for row in chosen for r in row["requests"] if r["tenant"]=="B"))
            if mode in ("protected","protected_block512"):
                costs[condition]["normalization_wall_ms"]=stats([r["protected"]["normalization_result"]["elapsed_ms"] for r in chosen])
                if "cuda_copy_interval_ms" in chosen[0]["protected"]["normalization_result"]:
                    costs[condition]["normalization_cuda_ms"]=stats([r["protected"]["normalization_result"]["cuda_copy_interval_ms"] for r in chosen])
        costs["first_B_median_cold_minus_warm_ms"]=costs["cold"]["first_B_ms"]["median"]-costs["warm"]["first_B_ms"]["median"]
        costs["B_tokens_identical_across_states"]=all(
            len({tuple(r["token_ids"]) for row in selected for r in row["requests"] if r["tenant"]=="B" and r["label"]==label})==1
            for label in "ABCD")
        costs["all_five_token_sequences_identical_across_states"]=all(
            len({tuple(r["token_ids"]) for row in selected for r in row["requests"]
                 if r["tenant"]==tenant and r["label"]==label})==1
            for tenant,label in [("A","A")]+[("B",label) for label in "ABCD"])
        if mode in ("protected","protected_block512"):
            digests=[r["protected"]["normalization_result"].get("canonical_kv_sha256") for r in selected]
            costs["active_KV_hash_equal_across_states"]=(len(set(digests))==1 if all(digests) else None)
        result["policies"][mode]=costs
    with (folder/"analysis.json").open("x") as fp:
        json.dump(result,fp,indent=2);fp.write("\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    analyze(Path(sys.argv[1]))
