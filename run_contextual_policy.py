"""Train a visible-feature policy selector on development tasks and freeze it."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.contextual_policy import select_policy
from rsi.retention_run import file_hash, seal_artifacts
from run_policy_evolution import evaluate


def run(source_run: Path, output: Path, bank_seed: int, development_tasks: int, final_tasks: int, budget: int) -> dict:
    if output.exists():
        raise FileExistsError(output)
    source = json.loads((source_run / "results.json").read_text(encoding="utf-8"))
    source_config = json.loads((source_run / "config.json").read_text(encoding="utf-8"))
    policies = {"base": source["base_policy"], "evolved": source["champion_policy"]}
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_contextual_policy.py", "run_policy_evolution.py", "rsi/contextual_policy.py", "rsi/search_diagnostic.py",
                    "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    config = {"source_run": str(source_run.relative_to(ROOT)), "bank_seed": bank_seed, "development_tasks": development_tasks,
              "final_tasks": final_tasks, "budget": budget, "policies": list(policies), "neighbors": 7, "selection_closed": False}
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "selection_rule": "visible-feature weighted k-nearest development accuracy"})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    bank_config = {"bank_seed": bank_seed, "bank_counts": {"development": development_tasks, "final": final_tasks}, "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / source_config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
    development = {policy: evaluate(search_policy, banks["development"], budget, macros) for policy, search_policy in policies.items()}
    dev_rows = {policy: {str(row["task_id"]): bool(row["selected_correct"]) for row in score["rows"]} for policy, score in development.items()}
    final = {policy: evaluate(search_policy, banks["final"], budget, macros) for policy, search_policy in policies.items()}
    chosen_rows = []
    for task in banks["final"]:
        chosen = select_policy(banks["development"], dev_rows, task, list(policies), config["neighbors"])
        row_by_policy = {policy: next(row for row in final[policy]["rows"] if row["task_id"] == task["id"]) for policy in policies}
        chosen_rows.append({"task_id": task["id"], "chosen_policy": chosen, "selected_correct": row_by_policy[chosen]["selected_correct"],
                            "coverage64": row_by_policy[chosen]["coverage64"], "selected_program": row_by_policy[chosen]["selected_program"]})
    config["selection_closed"] = True
    result = {"status": "completed", "selection_closed": True, "development": {policy: {key: value for key, value in score.items() if key != "rows"} for policy, score in development.items()},
              "fixed_final": {policy: {key: value for key, value in score.items() if key != "rows"} for policy, score in final.items()},
              "contextual_final": {"selected_correct": sum(row["selected_correct"] for row in chosen_rows), "coverage64": sum(row["coverage64"] for row in chosen_rows), "tasks": len(chosen_rows)},
              "chosen_rows": chosen_rows, "dev_rows": dev_rows, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["two candidate policies", "single development/final bank pair", "finite hidden examples", "same-host oracle", "not unrestricted RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("selection_closed", {"selected": len(chosen_rows), "rule": "visible-only contextual nearest neighbors"})
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run")
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091721)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=128)
    args = parser.parse_args()
    result = run(ROOT / args.source_run, ROOT / args.output, args.bank_seed, args.development_tasks, args.final_tasks, args.budget)
    print(json.dumps(result, indent=2))
