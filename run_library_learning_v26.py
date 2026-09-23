"""V26: DreamCoder-style library induction plus a Bayesian selector."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.generative_prior import choose, program_log_probability
from rsi.library_learning import mine_library
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


def pool(task, macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def score(task, rows, mode, config):
    selected = rows[0] if mode.endswith("cost") and rows else choose(rows, config["generator_max_atoms"])
    selected = selected or {"program": "", "cost": 0.0}
    log_probability = program_log_probability(selected["program"], config["generator_max_atoms"])
    payload = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(rows), "bayesian_log_probability": log_probability if math.isfinite(log_probability) else None}
    payload["replay_sha256"] = digest(payload)
    payload["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
    return payload


def evaluate(tasks, macros, config, mode):
    rows = [score(task, pool(task, macros, config), mode, config) for task in tasks]
    correct = sum(row["oracle_correct"] for row in rows)
    return {"mode": mode, "correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_library_learning_v26.py", "rsi/library_learning.py", "rsi/generative_prior.py",
                    "rsi/version_space.py", "rsi/cegis_search.py", "rsi/search.py", "rsi/atom_pool_partial.py",
                    "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "development-trained reusable fragment library with Bayesian selection"})
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

    library = mine_library([task["reference"] for task in banks["development"]],
                           max_library=config["library_size"], max_length=config["library_max_length"],
                           min_frequency=config["library_min_frequency"])
    write_json(output / "learned_library.json", library)
    journal.append("library_fitted", {"library_sha256": digest(library), "macros": len(library["macros"]),
                                       "eligible_fragments": library["eligible_fragments"]})

    arms = {
        "baseline_cost": (macros, "baseline_cost"),
        "generator_prior": (macros, "generator_prior"),
        "library_cost": ([*macros, *library["macros"]], "library_cost"),
        "library_bayesian": ([*macros, *library["macros"]], "library_bayesian"),
    }
    scores = {}
    for name, (arm_macros, mode) in arms.items():
        scores[name] = {split: evaluate(banks[split], arm_macros, config, mode)
                        for split in ("development", "admission", "final")}
        journal.append("arm_evaluated", {"arm": name, "development_correct": scores[name]["development"]["correct"],
                                         "admission_correct": scores[name]["admission"]["correct"]})

    base = scores["generator_prior"]
    candidate = scores["library_bayesian"]
    accepted = candidate["admission"]["correct"] >= base["admission"]["correct"] and \
        candidate["development"]["correct"] >= base["development"]["correct"] - config["development_tolerance"]
    selected = "library_bayesian" if accepted else "generator_prior"
    result = {"status": "completed", "scores": scores, "accepted": accepted, "selected": selected,
              "library": library, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["development references used for library induction", "fixed DSL and grammar",
                              "small fresh banks", "library miner is bounded and hand-specified", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091858)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--generator-max-atoms", type=int, default=4)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--library-size", type=int, default=32)
    parser.add_argument("--library-max-length", type=int, default=3)
    parser.add_argument("--library-min-frequency", type=int, default=2)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "candidate_limit": args.candidate_limit, "candidate_budget": args.candidate_budget,
              "max_atoms": args.max_atoms, "generator_max_atoms": args.generator_max_atoms,
              "development_tolerance": args.development_tolerance, "library_size": args.library_size,
              "library_max_length": args.library_max_length, "library_min_frequency": args.library_min_frequency,
              "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
