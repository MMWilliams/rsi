"""Visible-only ensemble of several evolved search policies."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from collections import defaultdict
from pathlib import Path

from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from run_policy_evolution import evaluate, rank


def select_by_vote(rows: list[dict]) -> str:
    votes = defaultdict(float)
    for row in rows:
        for position, program in enumerate(row["frontier_programs"]):
            votes[program] += 1.0 / (position + 1)
    if not votes:
        return ""
    return max(votes, key=lambda program: (votes[program], -len(program), program))


def run(source_run: Path, output: Path, bank_seed: int, tasks: int, budget: int) -> dict:
    if output.exists():
        raise FileExistsError(output)
    source = json.loads((source_run / "results.json").read_text(encoding="utf-8"))
    source_config = json.loads((source_run / "config.json").read_text(encoding="utf-8"))
    candidates = [("base", source["base_policy"], {"coverage64": 0, "selected_correct": 0})]
    candidates.append(("champion", source["champion_policy"], {"coverage64": 0, "selected_correct": 0}))
    seen = {json.dumps(policy, sort_keys=True) for _, policy, _ in candidates}
    for item in sorted(source["history"], key=lambda row: rank(row["score"]), reverse=True):
        key = json.dumps(item["policy"], sort_keys=True)
        if key not in seen:
            candidates.append((f"evolved_{len(candidates)}", item["policy"], item["score"]))
            seen.add(key)
        if len(candidates) == 5:
            break
    output.mkdir(parents=True)
    started = time.perf_counter()
    source_names = ["run_policy_ensemble.py", "run_policy_evolution.py", "rsi/search_diagnostic.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    config = {"source_run": str(source_run.relative_to(ROOT)), "bank_seed": bank_seed, "tasks": tasks, "budget": budget,
              "policies": [name for name, _, _ in candidates], "selection_rule": "rank-discounted frontier voting", "selection_closed": False}
    write_json(output / "config.json", config)
    journal = Journal(output / "events.jsonl")
    journal.append("preregistration", {"config": config, "source_sha256": hashes})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    bank_config = {"bank_seed": bank_seed, "bank_counts": {"final": tasks}, "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / source_config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
    all_scores = {name: evaluate(policy, banks["final"], budget, macros) for name, policy, _ in candidates}
    fixed = {}
    for name, score in all_scores.items():
        fixed[name] = {"selected_correct": score["selected_correct"], "coverage64": score["coverage64"], "tasks": score["tasks"]}
    ensemble_rows = []
    for task in banks["final"]:
        rows = [next(row for row in all_scores[name]["rows"] if row["task_id"] == task["id"]) for name, _, _ in candidates]
        program = select_by_vote(rows)
        correct_flag = bool(program and correct(program, task["visible"] + task["hidden"]))
        ensemble_rows.append({"task_id": task["id"], "selected_program": program, "selected_correct": correct_flag, "source_rows": rows})
    result = {"status": "completed", "selection_closed": True, "fixed": fixed,
              "ensemble": {"selected_correct": sum(row["selected_correct"] for row in ensemble_rows), "tasks": len(ensemble_rows)},
              "ensemble_rows": ensemble_rows, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["single fresh bank", "bounded DSL", "finite hidden examples", "same-host oracle", "no final-label policy selection"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("selection_closed", {"rows": len(ensemble_rows), "rule": config["selection_rule"]})
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run")
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091731)
    parser.add_argument("--tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(run(ROOT / args.source_run, ROOT / args.output, args.bank_seed, args.tasks, args.budget), indent=2))
