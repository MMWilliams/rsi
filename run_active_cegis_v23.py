"""V23: interactive counterexample-guided synthesis with query budgeting."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.architecture_evolution import run_architecture
from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.retention_run import file_hash, seal_artifacts


def all_task_rows(node):
    if isinstance(node, dict):
        if {"id", "reference", "visible", "hidden"}.issubset(node):
            yield node
        else:
            for value in node.values():
                yield from all_task_rows(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_task_rows(value)


def historical_exclusions():
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("**/protected_banks.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        exclusions.update(template(task["reference"]) for task in all_task_rows(rows))
    return exclusions


def evaluate(architecture, tasks, macros, query_budget):
    rows = []
    for task in tasks:
        public = {"id": task["id"], "visible": task["visible"]}
        if query_budget == 0:
            first = run_architecture(architecture, task, macros)
        else:
            first = counterexample_guided_solve(public, task["hidden"], budget=architecture["budget"],
                                                max_atoms=architecture["max_atoms"], macros=macros,
                                                synthesize_constants=architecture["synthesize_constants"],
                                                max_queries=query_budget)
        if query_budget == 0:
            second = run_architecture(architecture, task, macros)
        else:
            second = counterexample_guided_solve(public, task["hidden"], budget=architecture["budget"],
                                                 max_atoms=architecture["max_atoms"], macros=macros,
                                                 synthesize_constants=architecture["synthesize_constants"],
                                                 max_queries=query_budget)
        if canonical(first) != canonical(second):
            raise RuntimeError("interactive replay mismatch")
        rows.append({"task_id": task["id"], "program": first["program"],
                     "oracle_correct": published_correct(first["program"], task["visible"] + task["hidden"]),
                     "queries": first.get("queries", 0), "examples_used": first.get("examples_used", len(task["visible"])),
                     "cost": first["cost"], "replay_sha256": first["replay_sha256"]})
    correct = sum(row["oracle_correct"] for row in rows)
    return {"query_budget": query_budget, "architecture": architecture, "correct": correct,
            "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows,
            "mean_queries": sum(row["queries"] for row in rows) / max(1, len(rows))}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_active_cegis_v23.py", "rsi/active_cegis.py", "rsi/cegis_search.py", "rsi/version_space.py",
                    "rsi/architecture_evolution.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py",
                    "rsi/oracle.py", "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "interactive CEGIS with deterministic counterexample queries"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"], "admission": config["admission_tasks"],
                                   "final": config["final_tasks"]}, "visible_examples": 3, "hidden_examples": 13,
                   "max_atoms": 4}
    banks, metadata = create_banks(bank_config, historical_exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
    architecture = {"engine": "cegis", "budget": config["budget"], "max_atoms": config["max_atoms"],
                    "synthesize_constants": True, "progress_weight": 1.0, "widening": 0.5, "id": "interactive_cegis"}
    scores = {}
    all_evaluations = []
    for query_budget in config["query_budgets"]:
        row = {"development": evaluate(architecture, banks["development"], macros, query_budget),
               "admission": evaluate(architecture, banks["admission"], macros, query_budget),
               "final": evaluate(architecture, banks["final"], macros, query_budget)}
        scores[str(query_budget)] = row
        all_evaluations.append(row)
        journal.append("query_budget_evaluated", {"query_budget": query_budget,
                                                  "development_correct": row["development"]["correct"],
                                                  "admission_correct": row["admission"]["correct"],
                                                  "final_correct": row["final"]["correct"]})
    baseline = scores["0"]
    eligible = [int(q) for q in config["query_budgets"] if scores[str(q)]["admission"]["correct"] >= baseline["admission"]["correct"]]
    selected_q = min(eligible, key=lambda q: (-scores[str(q)]["admission"]["correct"], q))
    result = {"status": "completed", "architecture": architecture, "selected_query_budget": selected_q,
              "scores": scores, "evaluations": len(all_evaluations), "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["oracle feedback is required", "fixed DSL and candidate grammar", "small fresh banks",
                              "same-host oracle", "interactive result is not passive RSI evidence"]}
    write_json(output / "evaluations.json", all_evaluations)
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091853)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=512)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--query-budgets", type=int, nargs="+", default=[0, 1, 2, 4])
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "budget": args.budget, "max_atoms": args.max_atoms, "query_budgets": args.query_budgets,
              "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
