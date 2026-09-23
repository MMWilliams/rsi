"""V28: retain active CEGIS epsilon transitions for passive later tasks."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.epsilon_library import mine_epsilon_macros
from rsi.generative_prior import choose, program_log_probability
from rsi.retention_run import file_hash, seal_artifacts
from rsi.version_space import enumerate_candidates


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


def exclusions():
    result = set()
    for path in sorted((ROOT / "runs").glob("**/protected_banks.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        result.update(template(task["reference"]) for task in all_task_rows(rows))
    return result


def candidate_pool(task, macros, epsilon_macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"],
                                epsilon_macros=epsilon_macros)


def evaluate(tasks, macros, epsilon_macros, config):
    rows = []
    for task in tasks:
        candidates = candidate_pool(task, macros, epsilon_macros, config)
        selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
        lp = program_log_probability(selected["program"], config["generator_max_atoms"])
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None}
        row["replay_sha256"] = digest(row)
        row["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
        rows.append(row)
    correct = sum(row["oracle_correct"] for row in rows)
    return {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_epsilon_retention_v28.py", "rsi/epsilon_library.py", "rsi/active_cegis.py",
                    "rsi/version_space.py", "rsi/cegis_search.py", "rsi/generative_prior.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "active development epsilon transitions retained for passive evaluation"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"], "admission": config["admission_tasks"],
                                   "final": config["final_tasks"]}, "visible_examples": 3, "hidden_examples": 13,
                   "max_atoms": config["generator_max_atoms"]}
    banks, metadata = create_banks(bank_config, exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
    active_rows = []
    for task in banks["development"]:
        active = counterexample_guided_solve({"id": task["id"], "visible": task["visible"]}, task["hidden"],
                                             budget=config["active_budget"], max_atoms=config["max_atoms"],
                                             macros=macros, synthesize_constants=True, max_queries=config["active_queries"])
        active_rows.append({"task_id": task["id"], "program": active["program"], "queries": active["queries"],
                            "counterexamples": active["counterexamples"], "replay_sha256": active["replay_sha256"]})
    write_json(output / "active_training.json", active_rows)
    training_triples = [(row["program"], task["visible"], task["hidden"])
                        for row, task in zip(active_rows, banks["development"])]
    epsilon = mine_epsilon_macros(training_triples, max_library=config["epsilon_library_size"],
                                  max_length=config["epsilon_max_length"], min_frequency=config["epsilon_min_frequency"])
    write_json(output / "epsilon_library.json", epsilon)
    journal.append("epsilon_library_fitted", {"library_sha256": digest(epsilon), "macros": len(epsilon["macros"]),
                                                "candidate_macros": epsilon["candidate_macros"]})
    baseline = {split: evaluate(banks[split], macros, [], config) for split in ("development", "admission", "final")}
    learned = {split: evaluate(banks[split], macros, epsilon["macros"], config)
               for split in ("development", "admission", "final")}
    accepted = learned["admission"]["correct"] >= baseline["admission"]["correct"] and \
        learned["development"]["correct"] >= baseline["development"]["correct"] - config["development_tolerance"]
    result = {"status": "completed", "baseline": baseline, "learned": learned, "accepted": accepted,
              "selected": "learned" if accepted else "baseline", "epsilon_library": epsilon,
              "active_training_tasks": len(active_rows), "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["oracle feedback used during development", "fixed DSL and grammar",
                              "small fresh banks", "bounded epsilon library", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091863)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--active-budget", type=int, default=512)
    parser.add_argument("--active-queries", type=int, default=2)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--generator-max-atoms", type=int, default=4)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--epsilon-library-size", type=int, default=32)
    parser.add_argument("--epsilon-max-length", type=int, default=3)
    parser.add_argument("--epsilon-min-frequency", type=int, default=1)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "active_budget": args.active_budget, "active_queries": args.active_queries,
              "candidate_limit": args.candidate_limit, "candidate_budget": args.candidate_budget,
              "max_atoms": args.max_atoms, "generator_max_atoms": args.generator_max_atoms,
              "development_tolerance": args.development_tolerance, "epsilon_library_size": args.epsilon_library_size,
              "epsilon_max_length": args.epsilon_max_length, "epsilon_min_frequency": args.epsilon_min_frequency,
              "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
