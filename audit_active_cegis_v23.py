"""Independent replay audit for the V23 interactive CEGIS run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.architecture_evolution import run_architecture
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.retention_run import file_hash


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    bank_manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    result = load(root / "results.json")
    evaluations = load(root / "evaluations.json")
    architecture = result["architecture"]
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    for name, rows in banks.items():
        if bank_manifest[name]["sha256"] != digest(rows) or bank_manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    replayed = 0
    task_map = {name: {task["id"]: task for task in rows} for name, rows in banks.items()}
    for evaluation in evaluations:
        q = evaluation["development"]["query_budget"]
        for split in ("development", "admission", "final"):
            aggregate = evaluation[split]
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[split][stored["task_id"]]
                public = {"id": task["id"], "visible": task["visible"]}
                if q == 0:
                    first = run_architecture(architecture, task, macros)
                else:
                    first = counterexample_guided_solve(public, task["hidden"], budget=architecture["budget"],
                                                        max_atoms=architecture["max_atoms"], macros=macros,
                                                        synthesize_constants=True, max_queries=q)
                if stored["program"] != first["program"] or stored["queries"] != first.get("queries", 0) or \
                        stored["examples_used"] != first.get("examples_used", len(task["visible"])) or \
                        stored["cost"] != first["cost"] or stored["replay_sha256"] != first["replay_sha256"]:
                    raise AssertionError(f"stored interactive result mismatch: {split} {task['id']}")
                correct += int(published_correct(first["program"], task["visible"] + task["hidden"]))
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: q={q} {split}")
    baseline_admission = result["scores"]["0"]["admission"]["correct"]
    eligible = [int(q) for q in config["query_budgets"] if result["scores"][str(q)]["admission"]["correct"] >= baseline_admission]
    expected_q = min(eligible, key=lambda q: (-result["scores"][str(q)]["admission"]["correct"], q))
    if expected_q != result["selected_query_budget"]:
        raise AssertionError("query-budget selection mismatch")
    manifest = load(root / "artifact_manifest.json")
    for relative, metadata in manifest.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    audit_result = {"status": "passed", "run_id": root.name, "journal_events": len(events),
                    "query_budgets": config["query_budgets"], "evaluated_rows_replayed": replayed,
                    "selected_query_budget": result["selected_query_budget"],
                    "final_scores": {q: result["scores"][str(q)]["final"]["correct"] for q in config["query_budgets"]},
                    "sealed_artifacts_checked": len(manifest), "results_sha256": digest(result),
                    "limitations": result["limitations"]}
    write_json(root / "audit.json", audit_result)
    return audit_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/active-cegis-v23-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
