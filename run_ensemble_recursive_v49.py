"""V49: consensus ensemble over independently mined recursive libraries."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.banks import create_banks
from rsi.common import ROOT, Journal, digest, write_json
from rsi.compressed_space import enumerate_compressed
from rsi.generative_prior import choose, program_log_probability
from rsi.grammar_library import atom_shape, instantiate_templates, mine_templates
from rsi.retention_run import file_hash, seal_artifacts
from run_recursive_macro_v42 import exclusions
from run_diverse_recursive_v48 import verified_population


def shape_signature(program):
    try:
        from parse import parse
        return json.dumps([atom_shape(atom) for atom in parse(program).atoms], sort_keys=True, separators=(",", ":"))
    except Exception:
        return program


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


def evaluate_ensemble(tasks, macros, libraries, config, arm):
    rows = []
    for task in tasks:
        candidates = []
        for expert, library in enumerate(libraries):
            proposals = instantiate_templates(library, task["visible"], macros,
                max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
            generated = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
                compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
                limit=config["candidate_limit"], budget=config["candidate_budget"])
            for candidate in generated[:config["ensemble_candidates"]]:
                candidates.append({"expert": expert, "shape": shape_signature(candidate["program"]), "row": candidate})
        groups = {}
        for candidate in candidates:
            groups.setdefault(candidate["shape"], []).append(candidate)
        ranked_groups = []
        for shape, group in groups.items():
            experts = len({item["expert"] for item in group})
            best = choose([item["row"] for item in group], config["generator_max_atoms"])
            ranked_groups.append((experts, program_log_probability(best["program"], config["generator_max_atoms"]),
                                  -best.get("cost", 0.0), shape, best))
        selected = max(ranked_groups, key=lambda item: (item[0], item[1], item[2], item[3]))[-1] if ranked_groups else {"program": "", "cost": 0.0}
        lp = program_log_probability(selected["program"], config["generator_max_atoms"])
        winning = max(ranked_groups, key=lambda item: (item[0], item[1], item[2], item[3])) if ranked_groups else (0, -math.inf, 0, "", selected)
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(candidates), "expert_votes": winning[0],
               "bayesian_log_probability": lp if math.isfinite(lp) else None,
               "search_width": config["search_width"], "arm": arm}
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
    source_names = ["run_ensemble_recursive_v49.py", "run_diverse_recursive_v48.py", "run_recursive_macro_v42.py",
                    "rsi/compressed_space.py", "rsi/active_cegis.py", "rsi/grammar_library.py", "rsi/generative_prior.py",
                    "rsi/cegis_search.py", "rsi/version_space.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py",
                    "rsi/oracle.py", "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "recursive verified population plus structural consensus ensemble"})
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
    all_library = mine_templates([row["program"] for row in gen0] + population_programs,
        max_library=config["library_size"], max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    # Deterministic task-block bootstrap; each expert sees a different verified
    # population slice, and no hidden labels enter the ensemble vote.
    blocks = []
    for block in range(config["ensemble_size"]):
        selected = [program for index, program in enumerate(population_programs) if index % config["ensemble_size"] == block]
        blocks.append(mine_templates([row["program"] for row in gen0] + selected,
            max_library=config["library_size"], max_length=config["library_max_length"], min_frequency=config["library_min_frequency"]))
    write_json(output / "generation0.json", gen0)
    write_json(output / "library1.json", library1)
    write_json(output / "generation1_population.json", population)
    write_json(output / "library_all.json", all_library)
    write_json(output / "ensemble_libraries.json", blocks)
    scores = {}
    for split in ("development", "admission", "final"):
        scores[split] = {"baseline": evaluate(banks[split], macros, None, config, "baseline"),
                         "generation1": evaluate(banks[split], macros, library1, config, "generation1"),
                         "generation2": evaluate(banks[split], macros, all_library, config, "generation2"),
                         "ensemble": evaluate_ensemble(banks[split], macros, blocks, config, "ensemble")}
    baseline_admission = scores["admission"]["baseline"]["correct"]
    eligible = [arm for arm in ("generation1", "generation2", "ensemble") if scores["admission"][arm]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda arm: (scores["admission"][arm]["correct"], scores["development"][arm]["correct"], arm)) if eligible else "baseline"
    result = {"status": "completed", "scores": scores, "eligible": eligible, "selected": selected,
              "generation0_programs": len(gen0), "population_programs": len(population_programs),
              "ensemble_size": len(blocks), "library1": library1, "library_all": all_library,
              "ensemble_libraries": blocks, "generation1_population": population,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["active oracle feedback used for training and population verification",
                              "ensemble experts share a fixed DSL and macro schema", "small synthetic banks",
                              "consensus is structural rather than semantic equivalence proof", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091899)
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
    parser.add_argument("--ensemble-size", type=int, default=4)
    parser.add_argument("--ensemble-candidates", type=int, default=8)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
