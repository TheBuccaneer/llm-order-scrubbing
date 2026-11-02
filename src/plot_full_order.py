"""Plot observed response rank against send position in the four-probe pilot."""

import json
import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "results" / "tmp" / "mpl")
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "full-order-20261102"


def counts(path: Path) -> list[list[int]]:
    grid = [[0] * 4 for _ in range(4)]
    for line in path.read_text(encoding="utf-8").splitlines():
        trial = json.loads(line)
        if trial["warm"] is None:
            continue
        probes = trial["probes"]
        sent = sorted(probes, key=lambda label: probes[label]["sent_ns"])
        received = sorted(probes, key=lambda label: probes[label]["received_ns"])
        x = sent.index(trial["warm"])
        y = received.index(trial["warm"])
        grid[y][x] += 1
    return grid


def main() -> None:
    grids = [counts(DATA / "trials.jsonl"), counts(DATA / "trials-no-cache.jsonl")]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.3), constrained_layout=True)
    for ax, grid, title in zip(
        axes,
        grids,
        ("Prefix-Cache an", "Prefix-Cache aus"),
    ):
        ax.imshow(grid, cmap="Blues", vmin=0, vmax=8)
        for y in range(4):
            for x in range(4):
                ax.text(
                    x,
                    y,
                    str(grid[y][x]),
                    ha="center",
                    va="center",
                    color="white" if grid[y][x] >= 5 else "#1f2937",
                    fontsize=12,
                    fontweight="bold",
                )
        ax.set_title(title, fontsize=13)
        ax.set_xticks(range(4), range(1, 5))
        ax.set_yticks(range(4), range(1, 5))
        ax.set_xlabel("Sendeposition der markierten Probe")
        ax.set_ylabel("Empfangsrang der markierten Probe")
        ax.set_aspect("equal")
    fig.suptitle("Qwen/vLLM: 32 vorgewärmte Durchläufe je Cachezustand", fontsize=13)
    fig.savefig(DATA / "rangvergleich.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
