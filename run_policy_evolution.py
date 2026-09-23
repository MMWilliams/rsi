"""Evolve the bounded search policy on development tasks, then freeze-test it."""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import shutil
import sys
import time
from pathlib import Path

from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG, BOUNDS
from rsi.search_diagnostic import solve


def mutate(parent: dict[str, float], rng: random.Random, scale: float) -> dict[str, float]:
    child = dict(parent)
    keys = list(BOUNDS)
    for key in keys:
        if rng.random() < 0.75:
            low, high = BOUNDS[key]
            span = high - low
            value = child[key] + rng.gauss(0.0, span * scale)
            child[key] = min(high, max(low, value))
    if child == parent:
        key = rng.choice(keys)
        low, high = BOUNDS[key]
        child[key] = low + rng.random() * (high - low)
    return child


def evaluate(policy: dict[str, float], tasks: list[dict], budget: int, macros: list) -> dict:
    rows = []
    for task in tasks:
        details = {}
        result = solve(public_task(task), policy, budget, 4, macros, [], diagnostics=details, pool_mode="baseline")
        frontier = details["frontier"]
        graded = [correct(row["program"], task["visible"] + task["hidden"]) for row in frontier[:64]]
        rows.append({"task_id": task["id"], "selected_correct": bool(graded and graded[0]),
                     "coverage64": bool(any(graded)), "frontier_size": len(frontier), "cost": result["cost"],
                     "selected_program": result["program"], "frontier_programs": [row["program"] for row in frontier[:64]]})
    return {"selected_correct": sum(row["selected_correct"] for row in rows),
            "coverage64": sum(row["coverage64"] for row in rows),
            "tasks": len(rows), "expansions": sum(row["cost"]["expansions"] for row in rows),
            "generated_nodes": sum(row["cost"]["generated_nodes"] for row in rows), "rows": rows}


def rank(score: dict) -> tuple:
    return (score["coverage64"], score["selected_correct"], -score["expansions"], -score["generated_nodes"])


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    source_names = ["run_policy_evolution.py", "rsi/search_diagnostic.py", "rsi/search.py", "rsi/atom_pool_partial.py",
                    "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "base_policy": BASE_CONFIG,
                                       "python": sys.version, "platform": platform.platform()})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        exclusions.update(template(task["reference"]) for rows in banks.values() for task in rows)
    bank_config = {"bank_seed": config["bank_seed"], "bank_counts": {"development": config["development_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    rng = random.Random(config["optimizer_seed"])
    population = [dict(BASE_CONFIG)] + [mutate(BASE_CONFIG, rng, config["initial_mutation_scale"]) for _ in range(config["population"] - 1)]
    history = []
    for generation in range(config["generations"]):
        scored = []
        scale = config["mutation_scale"] * (0.75 ** generation)
        for index, policy in enumerate(population):
            score = evaluate(policy, banks["development"], config["budget"], macros)
            row = {"generation": generation, "index": index, "policy": policy, "score": {key: value for key, value in score.items() if key != "rows"}, "rows": score["rows"]}
            scored.append(row)
            history.append(row)
            journal.append("policy_evaluated", row)
        scored.sort(key=lambda row: rank(row["score"]), reverse=True)
        elites = scored[:max(2, config["elite_count"])]
        journal.append("generation_closed", {"generation": generation, "elite_ids": [f"{row['generation']}-{row['index']}" for row in elites], "best": elites[0]})
        population = [row["policy"] for row in elites]
        while len(population) < config["population"]:
            population.append(mutate(rng.choice(population), rng, scale))
    final_scores = sorted(history, key=lambda row: rank(row["score"]), reverse=True)
    champion = final_scores[0]["policy"]
    dev_base = evaluate(BASE_CONFIG, banks["development"], config["budget"], macros)
    dev_champion = evaluate(champion, banks["development"], config["budget"], macros)
    final_base = evaluate(BASE_CONFIG, banks["final"], config["budget"], macros)
    final_champion = evaluate(champion, banks["final"], config["budget"], macros)
    result = {"status": "completed", "base_policy": BASE_CONFIG, "champion_policy": champion,
              "development": {"base": {key: value for key, value in dev_base.items() if key != "rows"}, "champion": {key: value for key, value in dev_champion.items() if key != "rows"}},
              "final": {"base": {key: value for key, value in final_base.items() if key != "rows"}, "champion": {key: value for key, value in final_champion.items() if key != "rows"}},
              "history": history, "final_rows": {"base": final_base["rows"], "champion": final_champion["rows"]},
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["bounded DSL", "single development/final bank pair", "finite hidden examples", "same-host oracle", "policy evolution is not unrestricted self-modifying intelligence"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result), "champion": champion})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091702)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--population", type=int, default=8)
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--elite-count", type=int, default=3)
    parser.add_argument("--budget", type=int, default=128)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    cfg = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks, "final_tasks": args.final_tasks,
           "population": args.population, "generations": args.generations, "elite_count": args.elite_count,
           "budget": args.budget, "optimizer_seed": 2026091703, "initial_mutation_scale": 0.25,
           "mutation_scale": 0.15, "macro_source": args.macro_source}
    print(json.dumps(run(cfg, ROOT / args.output), indent=2))
