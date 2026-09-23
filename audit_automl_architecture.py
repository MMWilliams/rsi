"""Independent replay audit for the V22 AutoML architecture run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.automl_architecture import factorial_candidates, promotion_order, select_admission
from rsi.architecture_evolution import run_architecture
from rsi.common import canonical, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.common import ROOT


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def replay_row(architecture, task, stored, macros):
    first = run_architecture(architecture, task, macros)
    second = run_architecture(architecture, task, macros)
    expected = {"program": first["program"],
                "oracle_correct": published_correct(first["program"], task["visible"] + task["hidden"]),
                "cost": first["cost"], "replay_sha256": first["replay_sha256"]}
    if canonical(first) != canonical(second):
        raise AssertionError(f"non-deterministic replay: {task['id']}")
    if any(stored[key] != value for key, value in expected.items()):
        raise AssertionError(f"stored result mismatch: {task['id']}")
    return expected


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    bank_manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    candidates = load(root / "candidates.json")
    evaluations = load(root / "evaluations.json")
    result = load(root / "results.json")
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    if candidates != factorial_candidates() or events[2]["payload"]["sha256"] != digest(candidates):
        raise AssertionError("candidate-space provenance mismatch")
    task_map = {task["id"]: task for rows in banks.values() for task in rows}
    for name, rows in banks.items():
        if bank_manifest[name]["sha256"] != digest(rows) or bank_manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")

    replayed = 0
    by_stage = {}
    for record in evaluations:
        by_stage.setdefault(record["stage"], []).append(record)
        correct = 0
        for stored in record["tasks"]:
            row = replay_row(record["architecture"], task_map[stored["task_id"]], stored, macros)
            correct += int(row["oracle_correct"])
            replayed += 1
        if correct != record["correct"] or len(record["tasks"]) != record["n"]:
            raise AssertionError(f"aggregate mismatch: {record['stage']} {record['architecture']['id']}")

    stage_counts = {name: len(rows) for name, rows in by_stage.items()}
    if stage_counts != result["promotions"]:
        raise AssertionError(f"promotion counts mismatch: {stage_counts}")
    baseline_id = result["baseline"]["architecture"]["id"]
    baseline_screen = next(row for row in by_stage["screen"] if row["architecture"]["id"] == baseline_id)
    expected_dev_arch = promotion_order(by_stage["screen"], config["development_pool"], {baseline_id})
    if [row["architecture"]["id"] for row in expected_dev_arch] != [row["architecture"]["id"] for row in by_stage["development"]]:
        raise AssertionError("development promotion mismatch")
    expected_admission_arch = promotion_order(by_stage["development"], config["admission_pool"], {baseline_id})
    if [row["architecture"]["id"] for row in expected_admission_arch] != [row["architecture"]["id"] for row in by_stage["admission"]]:
        raise AssertionError("admission promotion mismatch")
    baseline_dev = next(row for row in by_stage["development"] if row["architecture"]["id"] == baseline_id)
    baseline_admission = next(row for row in by_stage["admission"] if row["architecture"]["id"] == baseline_id)
    paired = []
    for row in by_stage["development"]:
        admission = next((candidate for candidate in by_stage["admission"]
                          if candidate["architecture"]["id"] == row["architecture"]["id"]), None)
        if admission is not None:
            paired.append({"architecture": row["architecture"], "development": row, "admission": admission})
    expected_selection = select_admission(paired, {"architecture": result["baseline"]["architecture"],
                                                    "development": baseline_dev, "admission": baseline_admission},
                                          config["development_tolerance"])
    if expected_selection != result["selection"]:
        raise AssertionError("admission selection mismatch")
    expected_final_arch = promotion_order(by_stage["admission"], config["final_pool"],
                                           {baseline_id, result["champion"]["architecture"]["id"]})
    if [row["architecture"]["id"] for row in expected_final_arch] != [row["architecture"]["id"] for row in by_stage["final"]]:
        raise AssertionError("final promotion mismatch")
    for label, aggregate in (("baseline", result["baseline"]["final"]), ("champion", result["champion"]["final"])):
        stored = next(row for row in by_stage["final"] if row["architecture"]["id"] == aggregate["architecture"]["id"])
        if stored != aggregate:
            raise AssertionError(f"{label} final result mismatch")

    manifest = load(root / "artifact_manifest.json")
    for relative, metadata in manifest.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    audit_result = {"status": "passed", "run_id": root.name, "journal_events": len(events),
                    "candidate_count": len(candidates), "evaluated_rows_replayed": replayed,
                    "stage_counts": stage_counts, "baseline_final": {"correct": result["baseline"]["final"]["correct"], "n": result["baseline"]["final"]["n"]},
                    "champion_final": {"correct": result["champion"]["final"]["correct"], "n": result["champion"]["final"]["n"]},
                    "sealed_artifacts_checked": len(manifest), "results_sha256": digest(result),
                    "limitations": result["limitations"]}
    write_json(root / "audit.json", audit_result)
    return audit_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/automl-architecture-v22-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
