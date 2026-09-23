"""V34: evolve the candidate-ranking program from verified development feedback."""

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
from rsi.generative_prior import choose as generator_choose, program_log_probability
from rsi.genetic_ranker import choose, evolve, vector
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


def make_dataset(tasks, macros, config):
    dataset = []
    for task in tasks:
        candidates = enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                          synthesize_constants=True, max_atoms=config["max_atoms"],
                                          limit=config["candidate_limit"], budget=config["candidate_budget"])
        labels = {candidate["program"]: published_correct(candidate["program"], task["visible"] + task["hidden"])
                  for candidate in candidates}
        dataset.append({"task_id": task["id"], "reference": task["reference"], "candidates": candidates,
                        "oracle_labels": labels})
    return dataset


def evaluate(dataset, tasks_by_id, weights, mode):
    rows = []
    for item in dataset:
        selected = generator_choose(item["candidates"], 4) if mode == "generator" else choose(weights, item["candidates"])
        selected = selected or {"program": "", "cost": 0.0}
        lp = program_log_probability(selected["program"])
        row = {"task_id": item["task_id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(item["candidates"]),
               "bayesian_log_probability": lp if math.isfinite(lp) else None,
               "selection_score": None if mode == "generator" else sum(
                   left * right for left, right in zip(weights, vector(selected))),
               "mode": mode}
        row["replay_sha256"] = digest(row)
        task = tasks_by_id[item["task_id"]]
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
    source_names = ["run_genetic_ranker_v34.py", "rsi/genetic_ranker.py", "rsi/generative_prior.py",
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
                                       "protocol": "evolutionary synthesis of candidate-ranking weights"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"], "admission": config["admission_tasks"],
                                   "final": config["final_tasks"]}, "visible_examples": 3, "hidden_examples": 13,
                   "max_atoms": config["max_atoms"]}
    banks, metadata = create_banks(bank_config, exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
    datasets = {split: make_dataset(banks[split], macros, config) for split in ("development", "admission", "final")}
    weights, training = evolve(datasets["development"], population_size=config["population_size"],
                               generations=config["generations"], elite_size=config["elite_size"],
                               sigma=config["sigma"], seed=config["evolution_seed"])
    write_json(output / "ranker.json", {"weights": list(weights), "training": training})
    journal.append("ranker_evolved", {"best_development_correct": training["best_correct"],
                                       "weights_sha256": digest(list(weights))})
    by_id = {split: {task["id"]: task for task in banks[split]} for split in datasets}
    baseline = {split: evaluate(datasets[split], by_id[split], weights, "generator") for split in datasets}
    evolved = {split: evaluate(datasets[split], by_id[split], weights, "evolved") for split in datasets}
    accepted = evolved["admission"]["correct"] >= baseline["admission"]["correct"] and \
        evolved["development"]["correct"] >= baseline["development"]["correct"] - config["development_tolerance"]
    result = {"status": "completed", "baseline": baseline, "evolved": evolved, "accepted": accepted,
              "selected": "evolved" if accepted else "baseline", "training": training,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["development correctness labels drive evolution", "fixed candidate DSL and features",
                              "bounded population and generations", "small fresh banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091872)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--population-size", type=int, default=32)
    parser.add_argument("--generations", type=int, default=24)
    parser.add_argument("--elite-size", type=int, default=8)
    parser.add_argument("--sigma", type=float, default=0.35)
    parser.add_argument("--evolution-seed", type=int, default=2026091873)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
