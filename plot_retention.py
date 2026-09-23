"""Standalone scientific figure from an audited retention experiment."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    root = Path(args.run)
    audit = json.loads((root / "audit.json").read_text())
    if audit["status"] != "passed":
        raise RuntimeError("Audit required before plotting")
    result = json.loads((root / "results.json").read_text())
    scores = result["scores"]
    colors = {"initial": "#505866", "fresh": "#cc553b", "replay": "#2979b8", "replay_gated": "#27865d"}
    labels = {"initial": "Initial", "fresh": "Fresh only", "replay": "Cumulative replay", "replay_gated": "Replay + gate"}
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.7))
    for arm in colors:
        score = scores["initial" if arm == "initial" else arm + "_selected"]
        ks = list(map(int, score["pass_at_k"]))
        axes[0].plot(ks, [100 * score["pass_at_k"][str(k)] for k in ks], marker="o", lw=2,
                     color=colors[arm], label=labels[arm], alpha=.85)
    axes[0].set(xscale="log", xlabel="Samples, k", ylabel="Estimated pass@k (%)", title="Selected models on fresh final tasks")
    axes[0].set_xticks([1, 4, 8, 16, 32, 64], [1, 4, 8, 16, 32, 64])
    axes[0].legend(fontsize=8)
    for arm in ("fresh", "replay", "replay_gated"):
        selected = ["initial"] + [r["selected_checkpoint"] for r in result["changes"] if r["change_id"].startswith(arm + "_round")]
        axes[1].plot([0, 1, 2], [scores[name]["mean_distinct_parseable_programs"] for name in selected],
                     marker="o", lw=2, color=colors[arm], label=labels[arm], alpha=.85)
    axes[1].set(xlabel="Round", ylabel="Distinct parseable programs / 64 samples", title="Syntactic diversity of selected models")
    axes[1].set_xticks([0, 1, 2])
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(alpha=.18)
        ax.set_ylim(bottom=0)
    fig.suptitle("Retention ablation: Qwen3-0.6B", fontsize=15, y=.98)
    fig.text(.5, .015, "One training seed; 24 final tasks. Frozen harvest diagnostic. Diversity is a proxy; RSI is not established.", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .05, 1, .93])
    destination = Path("analysis") / root.name
    destination.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination / "retention.png", dpi=180)
    fig.savefig(destination / "retention.svg")
    print(destination / "retention.png")


if __name__ == "__main__":
    main()
