"""Render actual measured pilot curves; requires matplotlib in the invoking environment."""
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
    result = json.loads((root / "results.json").read_text(encoding="utf-8"))
    neural = result.get("neural")
    if not neural:
        raise SystemExit("No neural measurements in this run")
    labels = {"base": "Shared initial model", "search_round1": "Adaptive search, round 1", "search_round2": "Adaptive search, round 2",
              "selftrain_round2": "Self-training, round 2", "fixed_search_round2": "Fixed search, round 2"}
    colors = {"base": "#65748b", "search_round1": "#83b7ab", "search_round2": "#007d6e", "selftrain_round2": "#bf6621", "fixed_search_round2": "#8050a5"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.13, top=0.82)
    for name, score in neural["scores"].items():
        ks = sorted(map(int, score["pass_at_k"]))
        ys = [100 * score["pass_at_k"][str(k)] for k in ks]
        ax.plot(ks, ys, marker="o", label=labels.get(name, name), color=colors.get(name), linewidth=2)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 4, 8, 16, 32, 64], [1, 4, 8, 16, 32, 64])
    ax.set_ylim(0, 100)
    ax.set_xlabel("Independent raw model samples (k)")
    ax.set_ylabel("pass@k (%)")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", frameon=False)
    fig.text(0.1, 0.94, "Raw Qwen3-0.6B coverage after verified distillation", fontsize=14, weight="bold", ha="left")
    n = len(next(iter(neural["scores"].values()))["tasks"])
    fig.text(0.1, 0.885, f"{n} held-out tasks · one training seed · total compute differs across arms", fontsize=10, color="#555555", ha="left")
    fig.savefig(root / "pass-at-k.png", dpi=180)
    fig.savefig(root / "pass-at-k.svg")
    print(root / "pass-at-k.png")


if __name__ == "__main__":
    main()
