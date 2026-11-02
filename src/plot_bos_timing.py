"""Plot the client-visible batch release time against cached send position."""

import json
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "results" / "tmp" / "mpl"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DATA = ROOT / "results" / "bos-sanitized-20261102"


def first_reply_by_position(mode: str) -> list[list[float]]:
    groups = [[] for _ in range(4)]
    for line in (DATA / "trials.jsonl").read_text(encoding="utf-8").splitlines():
        trial = json.loads(line)
        if trial["mode"] != mode or trial["warm"] is None:
            continue
        probes = trial["probes"]
        sent = sorted(probes, key=lambda label: probes[label]["sent_ns"])
        position = sent.index(trial["warm"])
        elapsed_ms = (
            min(item["received_ns"] for item in probes.values())
            - min(item["sent_ns"] for item in probes.values())
        ) / 1e6
        groups[position].append(elapsed_ms)
    return groups


def main() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5), constrained_layout=True)
    styles = (
        ("bos4", "BOS W=4", "#2563eb"),
        ("d250", "BOS W=4, Ziel 250 ms", "#f97316"),
        ("slot1050", "Fester Freigabezeitpunkt", "#059669"),
    )
    for mode, label, color in styles:
        groups = first_reply_by_position(mode)
        medians = [statistics.median(group) for group in groups]
        lows = [median - min(group) for median, group in zip(medians, groups)]
        highs = [max(group) - median for median, group in zip(medians, groups)]
        ax.errorbar(
            range(1, 5), medians, yerr=[lows, highs], marker="o",
            capsize=3, linewidth=2, color=color, label=label,
        )
    ax.set_xticks(range(1, 5))
    ax.set_xlabel("Sendeposition des vorbereiteten Präfixes")
    ax.set_ylabel("Erste Clientantwort ab erstem Versand (ms)")
    ax.set_title("Vollständige 16-Token-Antworten, 16 Versuche je Position")
    ax.grid(axis="y", color="#dddddd")
    ax.legend()
    fig.savefig(DATA / "timingvergleich.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
