"""V48: quality-diversity population for recursive macro learning."""

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
from rsi.compressed_space import enumerate_compressed
from rsi.generative_prior import choose, program_log_probability
from rsi.grammar_library import atom_shape, instantiate_templates, mine_templates
from rsi.retention_run import file_hash, seal_artifacts
from run_recursive_macro_v42 import all_task_rows, exclusions


def evaluate(tasks, macros, library, config, arm):
    rows = []
    for task in tasks:
        proposals = [] if library is None else instantiate_templates(library, task["visible"], macros,
            max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
        candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
            compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
            limit=config["candidate_limit"], budget=config["candidate_budget"])
        selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
        lp = program_log_probability(selected["program"], config["generator_max_atoms"])
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
               "search_width": config["search_width"], "arm": arm}
        row["replay_sha256"] = digest(row)
        row["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
        rows.append(row)
    correct = sum(row["oracle_correct"] for row in rows)
    return {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}


def verified_population(tasks, macros, library, config):
    population = []
    for task in tasks:
        proposals = instantiate_templates(library, task["visible"], macros,
            max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
        candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
            compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
            limit=config["candidate_limit"], budget=config["candidate_budget"])
        ranked = []
        for candidate in candidates:
            program = candidate["program"]
            if not published_correct(program, task["visible"] + task["hidden"]):
                continue
            try:
                from parse import parse
                signature = json.dumps([atom_shape(atom) for atom in parse(program).atoms], sort_keys=True, separators=(",", ":"))
            except Exception:
                signature = program
            ranked.append((signature, candidate))
        selected = []
        used = set()
        for signature, candidate in ranked:
            if signature in used:
                continue
            used.add(signature)
            selected.append(candidate["program"])
            if len(selected) >= config["population_size"]:
                break
        if len(selected) < config["population_size"]:
            for _signature, candidate in ranked:
                if candidate["program"] not in selected:
                    selected.append(candidate["program"])
                if len(selected) >= config["population_size"]:
                    break
        population.append({"task_id": task["id"], "programs": selected, "candidates_checked": len(candidates)})
    return population


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_diverse_recursive_v48.py", "run_recursive_macro_v42.py", "rsi/compressed_space.py",
                    "rsi/active_cegis.py", "rsi/grammar_library.py", "rsi/generative_prior.py", "rsi/cegis_search.py",
                    "rsi/version_space.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py",
                    "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py",
                    "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "recursive macro learning with verified quality-diversity population"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"], "admission": config["admission_tasks"],
                                   "final": config["final_tasks"]}, "visible_examples": 3, "hidden_examples": 13,
                   "max_atoms": config["reference_max_atoms"]}
    banks, metadata = create_banks(bank_config, exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    gen0 = []
    for task in banks["development"]:
        item = counterexample_guided_solve({"id": task["id"], "visible": task["visible"]}, task["hidden"],
            budget=config["training_budget"], max_atoms=config["training_max_atoms"], macros=macros,
            synthesize_constants=True, max_queries=config["training_queries"])
        if published_correct(item["program"], task["visible"] + task["hidden"]):
            gen0.append({"task_id": task["id"], "program": item["program"], "queries": item["queries"],
                         "replay_sha256": item["replay_sha256"]})
    library1 = mine_templates([row["program"] for row in gen0], max_library=config["library_size"],
        max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    population = verified_population(banks["development"], macros, library1, config)
    population_programs = [program for row in population for program in row["programs"]]
    library2 = mine_templates([row["program"] for row in gen0] + population_programs,
        max_library=config["library_size"], max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    write_json(output / "generation0.json", gen0)
    write_json(output / "library1.json", library1)
    write_json(output / "generation1_population.json", population)
    write_json(output / "library2.json", library2)
    journal.append("population_fitted", {"gen0_programs": len(gen0), "population_programs": len(population_programs),
        "library1_sha256": digest(library1), "library2_sha256": digest(library2)})
    scores = {}
    for split in ("development", "admission", "final"):
        scores[split] = {"baseline": evaluate(banks[split], macros, None, config, "baseline"),
                         "generation1": evaluate(banks[split], macros, library1, config, "generation1"),
                         "generation2": evaluate(banks[split], macros, library2, config, "generation2")}
    baseline_admission = scores["admission"]["baseline"]["correct"]
    eligible = [arm for arm in ("generation1", "generation2") if scores["admission"][arm]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda arm: (scores["admission"][arm]["correct"], scores["development"][arm]["correct"], arm)) if eligible else "baseline"
    result = {"status": "completed", "scores": scores, "eligible": eligible, "selected": selected,
              "generation0_programs": len(gen0), "population_programs": len(population_programs),
              "population": population, "library1": library1, "library2": library2,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["active oracle feedback used in generation zero and population verification",
                              "fixed DSL and macro schema", "population size is researcher-bounded", "small fresh banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091896)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--reference-max-atoms", type=int, default=6)
    parser.add_argument("--training-max-atoms", type=int, default=6)
    parser.add_argument("--training-budget", type=int, default=512)
    parser.add_argument("--training-queries", type=int, default=2)
    parser.add_argument("--search-width", type=int, default=2)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--generator-max-atoms", type=int, default=4)
    parser.add_argument("--library-size", type=int, default=32)
    parser.add_argument("--library-max-length", type=int, default=3)
    parser.add_argument("--library-min-frequency", type=int, default=2)
    parser.add_argument("--max-proposals", type=int, default=256)
    parser.add_argument("--slot-limit", type=int, default=16)
    parser.add_argument("--population-size", type=int, default=4)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
