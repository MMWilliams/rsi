"""Inspect source-calibration feedback, retaining task-level wins and losses.

Descriptive only: reads archived source outcomes, never final tasks or new scores.
"""
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
    assert read("audit.json")["status"] == "passed"
    sources = read("source_trajectories.json")
    evaluations = {}
    for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["kind"] == "evaluation" and event["payload"]["label"].startswith("balanced_source/"):
            payload = event["payload"]
            scores = {row["task_id"]: int(row["oracle_correct"]) for row in payload["results"]}
            key = payload["request_sha256"]
            if key in evaluations:
                assert evaluations[key] == scores
            evaluations[key] = scores
    records, by_operator = [], {}
    for source in sources:
        for decision in source["decisions"]:
            for attempt in decision["attempts"]:
                parent = evaluations[attempt["parent_evaluation_request_sha256"]]
                child = evaluations[attempt["candidate_evaluation_request_sha256"]]
                assert parent.keys() == child.keys()
                wins = [task for task in parent if child[task] > parent[task]]
                losses = [task for task in parent if child[task] < parent[task]]
                assert (len(wins) - len(losses)) / len(parent) == attempt["development_gain"]
                row = {"change_id": attempt["change_id"], "source_seed": source["seed"],
                       "operator": attempt["operator"]["name"], "tasks": len(parent),
                       "wins": len(wins), "losses": len(losses), "win_ids": wins, "loss_ids": losses,
                       "net_zero": len(wins) == len(losses), "changed_any_task": bool(wins or losses)}
                records.append(row)
                stats = by_operator.setdefault(row["operator"], {"trials": 0, "wins": 0, "losses": 0, "tasks": 0})
                for key, value in (("trials", 1), ("wins", len(wins)), ("losses", len(losses)), ("tasks", len(parent))):
                    stats[key] += value
    summary = {"trials": len(records), "net_zero_trials": sum(r["net_zero"] for r in records),
               "net_zero_with_churn": sum(r["net_zero"] and r["changed_any_task"] for r in records),
               "trials_with_task_changes": sum(r["changed_any_task"] for r in records),
               "task_edit_observations": sum(r["tasks"] for r in records),
               "task_wins": sum(r["wins"] for r in records), "task_losses": sum(r["losses"] for r in records)}
    output = {"run_id": root.name, "scope": "post hoc source calibration only; repeated tasks within a generation are not independent",
              "summary": summary, "by_operator": by_operator, "records": records,
              "provenance": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                             for name in ("audit.json", "events.jsonl", "source_trajectories.json")},
              "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path = Path(__file__).parent / (root.name + "-edit-signal.json")
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "by_operator": by_operator, "saved": str(path)}, indent=2))


if __name__ == "__main__":
    main()
