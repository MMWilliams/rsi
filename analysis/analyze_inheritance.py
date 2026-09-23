"""Post-run diagnostics; no new model/search queries and no promotion decisions."""
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
    audit = read("audit.json")
    if audit["status"] != "passed":
        raise ValueError("Only analyze independently audited completed runs")
    result, sources, transfers = (read(name) for name in ("results.json", "source_trajectories.json", "transfer_trajectories.json"))
    source_summary = []
    for source in sources:
        attempts = [a for d in source["decisions"] for a in d["attempts"]]
        by_operator = {}
        for name in source["table"]:
            rows = [a for a in attempts if a["operator"]["name"] == name]
            by_operator[name] = {"trials": len(rows), "positive": sum(a["development_gain"] > 0 for a in rows),
                                 "zero": sum(a["development_gain"] == 0 for a in rows),
                                 "negative": sum(a["development_gain"] < 0 for a in rows),
                                 "accepted": sum(a["accepted"] for a in rows)}
        source_summary.append({"seed": source["seed"], "trials": len(attempts),
                               "positive": sum(a["development_gain"] > 0 for a in attempts),
                               "zero": sum(a["development_gain"] == 0 for a in attempts),
                               "negative": sum(a["development_gain"] < 0 for a in attempts),
                               "accepted": sum(a["accepted"] for a in attempts), "operators": by_operator})
    comparisons = []
    for seed in [s["seed"] for s in sources]:
        runs = {r["condition"]: r["trajectory"] for r in transfers if r["source_seed"] == seed}
        scores = {r["condition"]: r for r in result["measurements"] if r["source_seed"] == seed}
        for control in ("g0", "g3", "scrambled_g6", "random"):
            choices = lambda t: [[a["operator"]["name"] for a in d["attempts"]] for d in t["decisions"]]
            comparisons.append({"seed": seed, "contrast": "g6_minus_" + control,
                                "different_proposal_generations": sum(a != b for a, b in zip(choices(runs["g6"]), choices(runs[control]))),
                                "same_final_config": runs["g6"]["config"] == runs[control]["config"],
                                "g6_only_solved": sum(a and not b for a, b in zip(scores["g6"]["task_scores"], scores[control]["task_scores"])),
                                "control_only_solved": sum(b and not a for a, b in zip(scores["g6"]["task_scores"], scores[control]["task_scores"]))})
    output = {"run_id": root.name, "analysis": "descriptive post-run diagnostics; not new preregistered contrasts",
              "source_calibration": source_summary, "transfer_comparisons": comparisons,
              "provenance": {"analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                             "results_sha256": hashlib.sha256((root / "results.json").read_bytes()).hexdigest(),
                             "audit_sha256": hashlib.sha256((root / "audit.json").read_bytes()).hexdigest(),
                             "artifact_manifest_sha256": hashlib.sha256((root / "artifact_manifest.json").read_bytes()).hexdigest()}}
    destination = Path(__file__).parent / (root.name + "-diagnostics.json")
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_calibration": [{k: v for k, v in row.items() if k != "operators"} for row in source_summary],
                      "transfer_comparisons": comparisons, "saved": str(destination)}, indent=2))


if __name__ == "__main__":
    main()
