"""Prepare manuscript figures/tables from existing results only.

No inference, attack fitting, hypothesis search or new experiment. Existing
intervals are copied; new CSVs are descriptive views of immutable inputs.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument("output",type=Path);args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    used={}
    def read(path):
        p=ROOT/path;used[path]=hashlib.sha256(p.read_bytes()).hexdigest()
        return json.loads(p.read_text())
    def lines(path):
        p=ROOT/path;used[path]=hashlib.sha256(p.read_bytes()).hexdigest()
        return [json.loads(l) for l in p.read_text().splitlines()]
    def table(name, rows):
        with (out/f"{name}.csv").open("x",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    def save(fig,name):
        fig.savefig(out/f"{name}.pdf",bbox_inches="tight")
        fig.savefig(out/f"{name}.png",dpi=180,bbox_inches="tight");plt.close(fig)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.spines.top":False,
                         "axes.spines.right":False,"pdf.fonttype":42})
    orange,blue="#bf631b","#245880"
    q=read("results/document-bos-20261103/analysis.json")
    l=read("results/llama-reference-20261103/bos-analysis.json")
    observer_rows=[]
    for model,series in [("Qwen documents",{s:q["aggregate"][s]["bos"] for s in ["c0","c1"]}),
                         ("Llama synthetic",l)]:
        for config in ["c0","c1"]:
            for obs in ["R2","T2"]:
                a=series[config][obs]
                observer_rows.append(dict(model=model,scheduler="S64" if config=="c0" else "S0",
                    observer=obs,n=a["n"],hits=a["hits"],accuracy=a["hits"]/a["n"],
                    nominal_wilson95_lower=a["wilson95"][0],nominal_wilson95_upper=a["wilson95"][1]))
    table("c1_observers",observer_rows)
    fig,axes=plt.subplots(1,2,figsize=(7.2,2.8),sharey=True,layout="constrained")
    for ax,model in zip(axes,["Qwen documents","Llama synthetic"]):
        for j,(obs,color) in enumerate([("R2",blue),("T2",orange)]):
            selected=[r for r in observer_rows if r["model"]==model and r["observer"]==obs]
            x=np.arange(2)+(j-.5)*.22;y=np.array([r["accuracy"] for r in selected])
            err=np.array([[r["accuracy"]-r["nominal_wilson95_lower"] for r in selected],
                          [r["nominal_wilson95_upper"]-r["accuracy"] for r in selected]])
            ax.errorbar(x,y,yerr=err,fmt="o" if obs=="R2" else "s",capsize=3,color=color,
                        label="R2: ranks" if obs=="R2" else "T2: full times")
            for xx,r in zip(x,selected):ax.annotate(f"{r['hits']}/{r['n']}",(xx,r["accuracy"]),
                xytext=(6,5),textcoords="offset points",fontsize=8,color=color)
        ax.axhline(.25,color="0.45",ls="--",lw=.8);ax.set_xticks([0,1],["S64 (256/64)","S0 (256/0)"])
        ax.set_title(model+"; held-out n=32/config");ax.set_ylim(0,1);ax.grid(axis="y",alpha=.18)
    axes[0].set_ylabel("Four-class accuracy");axes[1].legend(loc="upper right",fontsize=8)
    save(fig,"fig1_rank_and_time")

    offset=read("results/tenant-offset-20261103/analysis.json")
    assert offset["integrity"]["error_count"]==0
    timing=[]
    for i in range(24):
        r=read(f"results/tenant-offset-20261103/case-{i:02d}/trial.json")
        b=list(r["probes"].values());assert len(b)==4
        timing.append(dict(case=i,pair=r["pair"],condition=r["condition"],offset_ms=r["victim_offset_ms"],
            first_B_ms=(min(v["received_ns"] for v in b)-min(v["sent_ns"] for v in b))/1e6))
    table("c2_client_times",timing)
    table("c2_observers",[dict(observer=k,n=offset["attacker"][k]["n"],hits=offset["attacker"][k]["hits"],
        accuracy=offset["attacker"][k]["accuracy"],wilson95_lower=offset["attacker"][k]["wilson95"][0],
        wilson95_upper=offset["attacker"][k]["wilson95"][1]) for k in ["R2","T1","T2"]])
    fig,axes=plt.subplots(1,2,figsize=(7.2,2.8),sharey=True,layout="constrained")
    for pair in range(8):
        a=next(r for r in timing if r["pair"]==pair and r["condition"]=="warm")
        b=next(r for r in timing if r["pair"]==pair and r["condition"]=="cold")
        assert b["first_B_ms"]>a["first_B_ms"]
        jitter=(-10 if pair%2 else 10)
        axes[0].plot([a["offset_ms"]+jitter]*2,[a["first_B_ms"],b["first_B_ms"]],color="0.7",lw=1)
        axes[0].scatter(a["offset_ms"]+jitter,a["first_B_ms"],c=orange,marker="o",s=27)
        axes[0].scatter(b["offset_ms"]+jitter,b["first_B_ms"],c=blue,marker="^",s=29)
    axes[0].set_xticks([0,150,300,450]);axes[0].set_xlabel("A offset (experimental truth, ms)")
    axes[0].set_ylabel("First full B response (ms)");axes[0].set_title("Eight fresh warm/cold pairs")
    labels=["Warm A\nn=8","Cold A\nn=8","No A\nn=4","Other cold A\nn=4"]
    for i,c in enumerate(["warm","cold","absent","other_cold"]):
        vals=[r["first_B_ms"] for r in timing if r["condition"]==c]
        axes[1].scatter(i+np.linspace(-.09,.09,len(vals)),vals,c=orange if c in ["warm","absent"] else blue,
                        s=22,marker="o" if c in ["warm","absent"] else "^")
        axes[1].plot([i-.22,i+.22],[statistics.median(vals)]*2,color="0.15",lw=1.3)
    axes[1].set_xticks(range(4),labels,fontsize=8);axes[1].set_title("Load controls limit the inference")
    for ax in axes:ax.grid(axis="y",alpha=.18)
    save(fig,"fig2_separate_namespaces")

    gate=read("results/protected-prefill-gate-20261103-01/analysis.json")
    rows=lines("results/protected-prefill-gate-20261103-01/trials.jsonl")
    costs=[]
    for r in rows:
        if r["split"]!="test":continue
        assert r["status"]=="ok"
        a=next(v for v in r["requests"] if v["tenant"]=="A")
        b=[v for v in r["requests"] if v["tenant"]=="B"]
        cuda=r["inference_cuda_intervals_ms"]
        if r["mode"]=="protected_block512":cuda+=r["protected"]["normalization_result"]["cuda_copy_interval_ms"]
        costs.append(dict(mode=r["mode"],condition=r["condition"],pair=r["pair"],
            A_ms=a["e2e_ms"],B_cohort_median_ms=statistics.median(v["e2e_ms"] for v in b),
            CUDA_interval_plus_copy_ms=cuda,A_reused_tokens=a["cached_tokens"]))
    assert len(costs)==144
    table("c3_test_cohorts",costs)
    policies=["protected_block512","ignore_hits","release1240"]
    names=["Protected\nprefill","Ignore\nhits","Release\n1240 ms"]
    endpoints=[("A_ms","A response"),("B_cohort_median_ms","B cohort median"),
               ("CUDA_interval_plus_copy_ms","CUDA interval + copy")]
    fig,axes=plt.subplots(1,3,figsize=(8.2,2.8),layout="constrained")
    medians=[]
    for ax,(endpoint,title) in zip(axes,endpoints):
        for i,mode in enumerate(policies):
            for condition,dx,color,marker in [("warm",-.13,orange,"o"),("cold",.13,blue,"^")]:
                vals=[r[endpoint] for r in costs if r["mode"]==mode and r["condition"]==condition]
                assert len(vals)==24
                x=i+dx+np.linspace(-.045,.045,len(vals))
                ax.scatter(x,vals,c=color,marker=marker,s=7,alpha=.45)
                median=statistics.median(vals);ax.plot([i+dx-.09,i+dx+.09],[median]*2,c=color,lw=2)
                medians.append(dict(mode=mode,condition=condition,endpoint=endpoint,median_ms=median,n=24))
        ax.set_xticks(range(3),names,fontsize=8);ax.set_title(title);ax.set_ylim(0,1350 if endpoint!="CUDA_interval_plus_copy_ms" else 1100)
        ax.grid(axis="y",alpha=.18)
    axes[0].set_ylabel("Milliseconds; in-process harness")
    axes[2].scatter([],[],c=orange,s=16,label="Warm A");axes[2].scatter([],[],c=blue,marker="^",s=16,label="Cold A")
    axes[2].legend(fontsize=8,loc="lower left")
    table("c3_medians",medians);save(fig,"fig3_matched_costs")
    table("c3_existing_observers",[dict(mode=mode,observer=obs,n=gate["observers"][mode][obs]["n"],
        balanced_accuracy=gate["observers"][mode][obs]["balanced_accuracy"],auc=gate["observers"][mode][obs]["auc"],
        auc_lower=gate["observers"][mode][obs]["pair_bootstrap_auc95"][0],
        auc_upper=gate["observers"][mode][obs]["pair_bootstrap_auc95"][1])
        for mode in policies for obs in ["stump","logistic"]])
    for path,h in used.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h
    manifest=dict(status="existing-data exports only; no new measurement or observer fit",inputs_sha256=used,
        renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scheduler_aliases={"S64":"old C0: budget256 threshold64","S0":"old C1: budget256 threshold0",
                           "S512":"matched gate: budget2048 threshold512; all policies"},
        units="C1/C2 use HTTP complete client receptions; C3 uses in-process complete response availability; no cross-series latency pooling",
        uncertainty="existing Wilson/paired-bootstrap fields only; few sessions and correlated groups limit interpretation",
        C1_tasks="four-class candidate position; chance25%; Qwen document transfer and Llama synthetic holdout are distinct workloads",
        C2_task="binary known-A cache state; chance50%; controls are not part of the16-case accuracy denominator",
        C3_task="binary cache-state observers, trained before held-out24 pairs; no security conclusion from nonsignificance")
    with (out/"manifest.json").open("x") as fp:json.dump(manifest,fp,indent=2);fp.write("\n")
    print("Existing-data figures and CSVs ready:",out)


if __name__=="__main__":main()
