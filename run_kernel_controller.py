"""Visible-feature controller over complementary symbolic search kernels."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.contextual_policy import select_policy
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve as diagnostic_solve
from rsi.search_reopen import solve as reopen_solve


POLICIES = ("base", "partial", "reopen")


def run_kernel(policy: str, task: dict, macros: list[str], budget: int) -> dict:
    if policy == "base":
        return diagnostic_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [], pool_mode="baseline")
    if policy == "partial":
        return diagnostic_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [], pool_mode="partial_empty")
    if policy == "reopen":
        return reopen_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [])
    raise ValueError(policy)


def evaluate(policy: str, tasks: list[dict], macros: list[str], budget: int) -> dict:
    rows = []
    for task in tasks:
        first = run_kernel(policy, task, macros, budget)
        second = run_kernel(policy, task, macros, budget)
        if canonical(first) != canonical(second):
            raise RuntimeError("kernel replay mismatch")
        correct = published_correct(first["program"], task["visible"] + task["hidden"])
        rows.append({"task_id": task["id"], "program": first["program"], "oracle_correct": correct,
                     "cost": first["cost"], "kernel": first["kernel"], "replay_sha256": first["replay_sha256"]})
    return {"policy": policy, "tasks": rows, "correct": sum(row["oracle_correct"] for row in rows), "n": len(rows),
            "accuracy": sum(row["oracle_correct"] for row in rows) / max(1, len(rows))}


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_kernel_controller.py", "rsi/contextual_policy.py", "rsi/search_diagnostic.py", "rsi/search_reopen.py",
                    "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "protocol": "kernel portfolio + visible-feature controller"})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks_seen = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks_seen.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    bank_config = {"bank_seed": config["bank_seed"], "bank_counts": {"development": config["development_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    dev_scores = {policy: evaluate(policy, banks["development"], macros, config["search_budget"]) for policy in POLICIES}
    final_scores = {policy: evaluate(policy, banks["final"], macros, config["search_budget"]) for policy in POLICIES}
    dev_rows = {policy: {row["task_id"]: row["oracle_correct"] for row in score["tasks"]} for policy, score in dev_scores.items()}
    selected_rows, choices = {}, []
    by_policy = {policy: {row["task_id"]: row for row in score["tasks"]} for policy, score in final_scores.items()}
    for task in banks["final"]:
        choice = select_policy(banks["development"], dev_rows, task, list(POLICIES), neighbors=config["neighbors"])
        selected_rows[task["id"]] = by_policy[choice][task["id"]]["program"]
        choices.append({"task_id": task["id"], "policy": choice})
    controller = {"tasks": [{"task_id": task["id"], "program": selected_rows[task["id"]],
                              "oracle_correct": published_correct(selected_rows[task["id"]], task["visible"] + task["hidden"])} for task in banks["final"]]}
    controller.update(correct=sum(row["oracle_correct"] for row in controller["tasks"]), n=len(controller["tasks"]))
    controller["accuracy"] = controller["correct"] / controller["n"]
    write_json(output / "choices.json", choices)
    write_json(output / "controller_final.json", controller)
    write_json(output / "development_scores.json", dev_scores)
    write_json(output / "final_scores.json", final_scores)
    result = {"status": "completed", "development": dev_scores, "final": final_scores, "controller": controller,
              "choices": choices, "ledger": {"kernels": list(POLICIES), "neighbors": config["neighbors"]},
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["small banks", "three fixed kernels", "visible-feature controller", "finite hidden examples", "same-host oracle", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091781)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--neighbors", type=int, default=7)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks, "final_tasks": args.final_tasks,
              "neighbors": args.neighbors, "macro_source": args.macro_source, "search_budget": 128}
    print(json.dumps(run(config, ROOT / args.output), indent=2))
