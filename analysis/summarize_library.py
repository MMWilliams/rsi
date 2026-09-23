"""Post-run descriptive analysis; does not feed back into the v7 experiment."""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    args = parser.parse_args()
    root = Path(args.run)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    assert read("audit.json")["status"] == "passed"
    result = read("results.json")
    trajectories = read("trajectories.json")
    evaluations, selections = {}, {}
    for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["kind"] == "evaluation":
            evaluations[event["payload"]["label"]] = event["payload"]
        elif event["kind"] == "fragment_proposals":
            selections[event["payload"]["label"]] = event["payload"]
    summaries = []
    for item in trajectories:
        trajectory = item["trajectory"]
        label = trajectory["label"]
        counts = collections.Counter()
        accepted_labels, rejected_positive, provenance = [], [], []
        for decision in trajectory["decisions"]:
            prefix = decision["label"]
            harvested = evaluations[prefix + "/harvest"]
            counts["harvest_correct"] += harvested["correct"]
            counts["harvest_tasks"] += harvested["n"]
            ranking = selections[prefix]["rankings"]
            counts["generations_with_compatible_fragments"] += any(r["compatible_tasks"] for r in ranking)
            memory = trajectory["snapshots"][str(decision["generation"])]["memory"]
            for attempt in decision["attempts"]:
                parent_rows = evaluations[prefix + "/parent"]["results"]
                child_rows = evaluations[prefix + f"/p{attempt['index']}"]["results"]
                if attempt["proposal"]["kind"] == "add_fragment":
                    counts["fragment_task_evaluations"] += len(parent_rows)
                    counts["fragment_changed_program"] += sum(a["program"] != b["program"] for a, b in zip(parent_rows, child_rows))
                    counts["fragment_changed_trace"] += sum(a["trace_sha256"] != b["trace_sha256"] for a, b in zip(parent_rows, child_rows))
                counts[attempt["proposal"]["kind"] + "_attempts"] += 1
                counts["positive_development"] += attempt["development_gain"] > 0
                counts["negative_development"] += attempt["development_gain"] < 0
                counts["zero_development"] += attempt["development_gain"] == 0
                counts["development_task_wins"] += len(attempt["development_delta"]["wins"])
                counts["development_task_losses"] += len(attempt["development_delta"]["losses"])
                if attempt["reason"] == "admission_regression":
                    rejected_positive.append({"label": prefix, "index": attempt["index"]})
                if attempt["accepted"]:
                    counts["accepted"] += 1
                    accepted_labels.append({"label": prefix, "index": attempt["index"], "kind": attempt["proposal"]["kind"]})
                    if attempt["proposal"]["kind"] == "add_fragment":
                        evidence = memory[attempt["proposal"]["name"]]
                        provenance.append({"label": prefix, "fragment": attempt["proposal"]["name"],
                                           "has_source_evidence": any(c["label"].startswith("source/") and "scrambled_from" not in c for c in evidence),
                                           "has_local_evidence": any(c["label"].startswith(label + "/") for c in evidence),
                                           "has_scrambled_evidence": any("scrambled_from" in c for c in evidence)})
        summaries.append({"phase": item["phase"], "seed": item["seed"], "condition": item["condition"],
                          "counts": dict(counts), "accepted": accepted_labels, "admission_rejections": rejected_positive,
                          "accepted_fragment_provenance": provenance,
                          "memory_sizes": {g: len(trajectory["snapshots"][g]["memory"]) for g in ("0", "3", "6")},
                          "stored_library_sizes": {g: len(trajectory["snapshots"][g]["macros"]) for g in ("0", "3", "6")},
                          "compute": item["compute"], "ranking_primitive_upper_bound": trajectory["ranking_primitive_upper_bound"]})
    grouped = {}
    for row in summaries:
        key = row["phase"] + "/" + row["condition"]
        target = grouped.setdefault(key, collections.Counter())
        target.update(row["counts"])
    source_costs = {a["seed"]: a for a in result["source_acquisition"]}
    charged_costs = {}
    for row in summaries:
        if row["phase"] != "transfer":
            continue
        target = charged_costs.setdefault(row["condition"], collections.Counter())
        source = source_costs[row["seed"]]
        for key in row["compute"]:
            target[key] += row["compute"][key] + source["compute"][key]
        target["ranking_primitive_upper_bound"] += row["ranking_primitive_upper_bound"] + source["ranking_primitive_upper_bound"]
    output = {"run_id": root.name, "scope": "descriptive post-run analysis, no new oracle queries; certificates show provenance, not the causal search route",
              "grouped_counts": {k: dict(v) for k, v in grouped.items()}, "trajectories": summaries,
              "source_plus_transfer_charges": {k: dict(v) for k, v in charged_costs.items()},
              "charge_note": "Totals over six sources include the same full source workload per arm, exclude final scoring and historical common-library acquisition, and are not all independently executed source work.",
              "primary_screen": result["screen"], "provenance": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                  for name in ("audit.json", "events.jsonl", "trajectories.json", "results.json")},
              "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    target = Path(__file__).parent / (root.name + "-diagnostics.json")
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"grouped_counts": output["grouped_counts"], "saved": str(target)}, indent=2))


if __name__ == "__main__":
    main()
