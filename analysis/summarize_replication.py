"""Apply the v5 protocol's declared screen to a completed, audited archive."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    root = Path(args.run)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    config, result, audit = (read(name) for name in ("config.json", "results.json", "audit.json"))
    assert config["name"] == "inheritance-replication-v5" and audit["status"] == "passed"
    assert result["status"] == "completed" and len(config["seeds"]) == 6
    controls = ("g0", "g3", "scrambled_g6", "random")
    rows = {seed: {m["condition"]: m for m in result["measurements"] if m["source_seed"] == seed} for seed in config["seeds"]}
    paired = [{"seed": seed, **{c: (r["g6"]["correct"] - r[c]["correct"]) for c in controls}} for seed, r in rows.items()]
    joint_wins = [r["seed"] for r in paired if r["g0"] > 0 and r["scrambled_g6"] > 0]
    means = {c: result["contrasts"]["g6_minus_" + c]["mean"] for c in controls}
    screen = all(value > 0 for value in means.values()) and len(joint_wins) > len(rows) / 2
    output = {"run_id": root.name, "declared_screen_passed": screen,
              "screen_meaning": "Exploratory criterion for another experiment; not statistical certification or demonstrated RSI",
              "all_four_means_positive": all(value > 0 for value in means.values()),
              "sources_beating_both_empty_and_scrambled": joint_wins,
              "majority_required": len(rows) // 2 + 1, "paired_task_count_differences": paired,
              "mean_percentage_point_differences": {k: 100 * v for k, v in means.items()},
              "condition_mean_percent": {c: 100 * sum(r[c]["accuracy"] for r in rows.values()) / len(rows) for c in config["conditions"]},
              "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "input_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                               for name in ("config.json", "results.json", "audit.json")}}
    path = Path(__file__).parent / (root.name + "-replication-screen.json")
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
