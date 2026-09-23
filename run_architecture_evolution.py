"""V21: evolve the search architecture with development/admission gates."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.architecture_evolution import architecture_id, base_architecture, mutate, run_architecture
from rsi.banks import create_banks, public_task, template
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
    return {"architecture": architecture, "correct": sum(row["oracle_correct"] for row in rows),
            "n": len(rows), "accuracy": sum(row["oracle_correct"] for row in rows) / max(1, len(rows)),
            "tasks": rows}


def choose(parent: dict, candidates: list[dict], tolerance: int) -> dict:
    parent_admission = parent["admission"]["correct"]
    eligible = [candidate for candidate in candidates
                if candidate["admission"]["correct"] >= parent_admission and
                candidate["development"]["correct"] >= parent["development"]["correct"] - tolerance]
    if not eligible:
        return {"accepted": False, "architecture": parent["architecture"], "reason": "no_candidate_passed_gate"}
    champion = max(eligible, key=lambda candidate: (candidate["admission"]["correct"],
                                                     candidate["development"]["correct"],
                                                     -candidate["architecture"]["budget"],
                                                     candidate["architecture"]["id"]))
    improved = (champion["admission"]["correct"] > parent_admission or
                champion["development"]["correct"] > parent["development"]["correct"])
    if not improved:
        return {"accepted": False, "architecture": parent["architecture"], "reason": "no_strict_gain"}
    return {"accepted": True, "architecture": champion["architecture"],
            "parent": parent["architecture"], "development": champion["development"],
            "admission": champion["admission"]}


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_architecture_evolution.py", "rsi/architecture_evolution.py", "rsi/cegis_search.py",
                    "rsi/search_diagnostic.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py",
                    "rsi/oracle.py", "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        target = output / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "two-stage architecture mutation with admission-priority gate"})
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

    parent_arch = base_architecture()
    parent_arch["id"] = architecture_id(parent_arch)
    all_evaluations = []
    generations = []
    for generation in range(config["generations"]):
        candidates = [parent_arch] if generation == 0 else [parent_arch] + mutate(parent_arch)
        records = []
        for architecture in candidates:
            development = evaluate(architecture, banks["development"], macros)
            admission = evaluate(architecture, banks["admission"], macros)
            record = {"generation": generation, "architecture": architecture,
                      "development": development, "admission": admission}
            records.append(record)
            all_evaluations.append(record)
            journal.append("architecture_evaluated", {"generation": generation, "architecture": architecture,
                                                       "development_correct": development["correct"],
                                                       "admission_correct": admission["correct"]})
        if generation == 0:
            parent_record = records[0]
            generations.append({"generation": generation, "parent": parent_record, "candidates": records,
                                "selection": {"accepted": True, "architecture": parent_arch, "reason": "initial"}})
        else:
            parent_record = next(record for record in records if record["architecture"] == parent_arch)
            selection = choose(parent_record, records, config["development_tolerance"])
            generations.append({"generation": generation, "parent": parent_record, "candidates": records,
                                "selection": selection})
            if selection["accepted"]:
                parent_arch = selection["architecture"]
            else:
                break

    baseline = next(record for record in all_evaluations if record["generation"] == 0)
    champion_arch = parent_arch
    champion_final = evaluate(champion_arch, banks["final"], macros)
    baseline_final = evaluate(baseline["architecture"], banks["final"], macros)
    result = {"status": "completed", "generations": generations, "evaluations": len(all_evaluations),
              "baseline": {"development": baseline["development"], "admission": baseline["admission"],
                           "final": baseline_final},
              "champion": {"architecture": champion_arch, "final": champion_final},
              "ledger": {"evaluations": len(all_evaluations), "generation_count": len(generations),
                         "development_tolerance": config["development_tolerance"]},
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["bounded architecture catalog", "small fresh banks", "fixed DSL", "same-host oracle", "not proof of RSI"]}
    write_json(output / "architectures.json", [record["architecture"] for record in all_evaluations])
    write_json(output / "evaluations.json", all_evaluations)
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091851)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--generations", type=int, default=2)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "generations": args.generations, "development_tolerance": args.development_tolerance,
              "macro_source": args.macro_source, "search_budget": 128}
    print(json.dumps(run(config, Path(args.output)), indent=2))
