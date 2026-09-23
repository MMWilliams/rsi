"""V22: multi-fidelity AutoML over the solver architecture space."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.architecture_evolution import run_architecture
from rsi.automl_architecture import factorial_candidates, promotion_order, select_admission
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


def historical_exclusions() -> set[str]:
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("**/protected_banks.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        exclusions.update(template(task["reference"]) for task in all_task_rows(rows))
    return exclusions


def evaluate(architecture: dict, tasks: list[dict], macros: list[str]) -> dict:
    rows = []
    for task in tasks:
        first = run_architecture(architecture, task, macros)
        second = run_architecture(architecture, task, macros)
        if canonical(first) != canonical(second):
            raise RuntimeError("architecture replay mismatch")
        rows.append({"task_id": task["id"], "program": first["program"],
                     "oracle_correct": published_correct(first["program"], task["visible"] + task["hidden"]),
                     "cost": first["cost"], "replay_sha256": first["replay_sha256"]})
    correct = sum(row["oracle_correct"] for row in rows)
    return {"architecture": architecture, "correct": correct, "n": len(rows),
            "accuracy": correct / max(1, len(rows)), "tasks": rows}


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_automl_architecture.py", "rsi/automl_architecture.py", "rsi/architecture_evolution.py",
                    "rsi/cegis_search.py", "rsi/search_diagnostic.py", "rsi/search.py", "rsi/atom_pool_partial.py",
                    "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "rsi/research_frameworks.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        target = output / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "factorial AutoML with Pareto successive halving and admission gate"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"],
                                   "admission": config["admission_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, historical_exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    candidates = factorial_candidates()
    write_json(output / "candidates.json", candidates)
    journal.append("candidate_space_frozen", {"count": len(candidates), "sha256": digest(candidates),
                                              "factors": ["engine", "budget", "max_atoms", "synthesize_constants",
                                                          "progress_weight", "widening"]})
    all_evaluations = []

    def stage(name, architectures, tasks):
        records = []
        for architecture in architectures:
            score = evaluate(architecture, tasks, macros)
            record = {"stage": name, **score}
            records.append(record)
            all_evaluations.append(record)
            journal.append("architecture_evaluated", {"stage": name, "architecture": architecture,
                                                       "correct": score["correct"], "n": score["n"]})
        write_json(output / (name + ".json"), records)
        return records

    screen_tasks = banks["development"][:config["screen_tasks"]]
    screen = stage("screen", candidates, screen_tasks)
    baseline_arch = next(row for row in candidates if row["engine"] == "baseline" and row["budget"] == 128
                         and row["max_atoms"] == 4 and row["progress_weight"] == 1.0 and row["widening"] == 0.5)
    dev_architectures = [row["architecture"] for row in promotion_order(screen, config["development_pool"],
                                                                         {baseline_arch["id"]})]
    development = stage("development", dev_architectures, banks["development"])
    baseline_dev_arch = baseline_arch["id"]
    baseline_dev = next(row for row in development if row["architecture"]["id"] == baseline_dev_arch)
    admission_architectures = [row["architecture"] for row in promotion_order(development, config["admission_pool"],
                                                                                {baseline_dev_arch})]
    admission = stage("admission", admission_architectures, banks["admission"])
    baseline_admission = next(row for row in admission if row["architecture"]["id"] == baseline_dev_arch)
    paired = []
    for row in development:
        matching = next((candidate for candidate in admission if candidate["architecture"]["id"] == row["architecture"]["id"]), None)
        if matching is not None:
            paired.append({"architecture": row["architecture"], "development": row, "admission": matching})
    selection = select_admission(paired, {"architecture": baseline_arch, "development": baseline_dev,
                                          "admission": baseline_admission}, config["development_tolerance"])
    selected_arch = selection["architecture"]
    final_architectures = [row["architecture"] for row in promotion_order(admission, config["final_pool"],
                                                                          {baseline_arch["id"], selected_arch["id"]})]
    final = stage("final", final_architectures, banks["final"])
    baseline_final = next(row for row in final if row["architecture"]["id"] == baseline_arch["id"])
    champion_final = next(row for row in final if row["architecture"]["id"] == selected_arch["id"])
    result = {"status": "completed", "candidate_count": len(candidates), "evaluations": len(all_evaluations),
              "selection": selection, "promotions": {"screen": len(screen), "development": len(development),
              "admission": len(admission), "final": len(final)},
              "baseline": {"architecture": baseline_arch, "development": baseline_dev,
                           "admission": baseline_admission, "final": baseline_final},
              "champion": {"architecture": selected_arch, "final": champion_final},
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["bounded declarative architecture space", "small fresh banks", "fixed DSL",
                              "same-host oracle", "successive-halving selection can miss low-fidelity winners",
                              "not proof of RSI"]}
    write_json(output / "evaluations.json", all_evaluations)
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091852)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--screen-tasks", type=int, default=8)
    parser.add_argument("--development-pool", type=int, default=32)
    parser.add_argument("--admission-pool", type=int, default=12)
    parser.add_argument("--final-pool", type=int, default=4)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "screen_tasks": args.screen_tasks, "development_pool": args.development_pool,
              "admission_pool": args.admission_pool, "final_pool": args.final_pool,
              "development_tolerance": args.development_tolerance, "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
