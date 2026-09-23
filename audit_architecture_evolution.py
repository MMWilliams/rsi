"""Independent replay audit for the V21 architecture-evolution run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.architecture_evolution import run_architecture
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from run_architecture_evolution import choose


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_task_result(architecture, task, stored, macros):
    first = run_architecture(architecture, task, macros)
    second = run_architecture(architecture, task, macros)
    expected = {
        "program": first["program"],
        "oracle_correct": published_correct(first["program"], task["visible"] + task["hidden"]),
        "cost": first["cost"],
        "replay_sha256": first["replay_sha256"],
    }
    if canonical(first) != canonical(second):
        raise AssertionError(f"non-deterministic replay: {task['id']}")
    if any(stored[key] != expected[key] for key in expected):
        raise AssertionError(f"stored result mismatch: {task['id']}")
    return expected


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    bank_manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    result = load(root / "results.json")
    evaluations = load(root / "evaluations.json")
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    for name, rows in banks.items():
        if bank_manifest[name]["sha256"] != digest(rows) or bank_manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    task_map = {task["id"]: task for rows in banks.values() for task in rows}
    replayed = 0
    for evaluation in evaluations:
        for split in ("development", "admission"):
            aggregate = evaluation[split]
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                row = check_task_result(evaluation["architecture"], task, stored, macros)
                correct += int(row["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {evaluation['architecture']['id']} {split}")

    generations = result["generations"]
    current = generations[0]["parent"]["architecture"]
    if generations[0]["selection"]["architecture"] != current:
        raise AssertionError("generation zero selection mismatch")
    for generation in generations[1:]:
        parent = generation["parent"]
        if parent["architecture"] != current:
            raise AssertionError("parent architecture chain mismatch")
        expected = choose(parent, generation["candidates"], config["development_tolerance"])
        actual = generation["selection"]
        if actual["accepted"] != expected["accepted"] or actual["architecture"] != expected["architecture"]:
            raise AssertionError(f"selection mismatch in generation {generation['generation']}")
        if actual["accepted"]:
            current = actual["architecture"]
    if result["champion"]["architecture"] != current:
        raise AssertionError("champion does not match accepted architecture chain")

    final_task_map = {task["id"]: task for task in banks["final"]}
    final_checks = {}
    for label, aggregate in (("baseline", result["baseline"]["final"]), ("champion", result["champion"]["final"])):
        correct = 0
        for stored in aggregate["tasks"]:
            row = check_task_result(
                result["baseline"]["final"]["architecture"] if label == "baseline" else result["champion"]["architecture"],
                final_task_map[stored["task_id"]], stored, macros)
            correct += int(row["oracle_correct"])
        if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
            raise AssertionError(f"final aggregate mismatch: {label}")
        final_checks[label] = {"correct": correct, "n": aggregate["n"]}

    manifest = load(root / "artifact_manifest.json")
    checked_files = 0
    for relative, metadata in manifest.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
        checked_files += 1
    audit_result = {
        "status": "passed",
        "run_id": root.name,
        "journal_events": len(events),
        "evaluated_rows_replayed": replayed,
        "final_checks": final_checks,
        "sealed_artifacts_checked": checked_files,
        "results_sha256": digest(result),
        "limitations": result["limitations"],
    }
    write_json(root / "audit.json", audit_result)
    return audit_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/architecture-evolution-v21-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
