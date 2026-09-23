"""V68: evolve the AST proposer's executable grammar architecture."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.ast_synthesis import synthesize_general_ast
from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.meta_grammar import (annotate_candidates, choose_architecture_candidate, evolve,
                              initial_population)
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from run_ast_v66 import _direct_ast_candidates
from run_induced_signature_v54 import bank_config


def build_pools(banks):
    pools = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task in banks[split]:
            predicates = synthesize_general_ast(task["visible"])
            candidates = _direct_ast_candidates(task, predicates)
            candidates = [{"program": candidate["program"], "cost": candidate["cost"],
                           "semantic_atoms": candidate["semantic_atoms"],
                           "oracle_correct": evaluate_program(candidate["program"],
                                                               task["visible"] + task["hidden"])}
                          for candidate in candidates]
            rows.append({"task_id": task["id"], "candidates": annotate_candidates(candidates)})
    
        pools[split] = rows
    return pools


def score_architectures(pools, banks, architecture, arm_id):
    result = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task, pool in zip(banks[split], pools[split]):
            candidate = choose_architecture_candidate(pool["candidates"], architecture)
            selected = candidate or {"program": "", "cost": 0.0, "semantic_atoms": 0,
                                     "grammar_ops": [], "grammar_complexity": 999,
                                     "oracle_correct": False}
            row = {"task_id": task["id"], "program": selected["program"],
                   "cost": selected["cost"], "candidate_count": len(pool["candidates"]),
                   "eligible_candidate_count": sum(1 for item in pool["candidates"]
                                                    if item.get("grammar_ops", [])
                                                    and set(item["grammar_ops"]) <= set(architecture["enabled_ops"])
                                                    and item.get("grammar_complexity", 999) <= architecture["max_complexity"]),
                   "semantic_atoms": selected.get("semantic_atoms", 0),
                   "grammar_ops": selected.get("grammar_ops", []),
                   "grammar_complexity": selected.get("grammar_complexity", 999),
                   "arm": arm_id, "oracle_correct": selected["oracle_correct"]}
            row["replay_sha256"] = digest({key: row[key] for key in row
                                            if key not in ("replay_sha256", "oracle_correct")})
            rows.append(row)
        correct = sum(row["oracle_correct"] for row in rows)
        result[split] = {"correct": correct, "n": len(rows),
                         "accuracy": correct / max(1, len(rows)), "tasks": rows}
    return result


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_meta_grammar_v68.py", "run_ast_v66.py", "run_induced_signature_v54.py",
                    "rsi/meta_grammar.py", "rsi/ast_synthesis.py", "rsi/semantic_invention.py",
                    "rsi/evolving_domain.py", "rsi/invented_space.py", "rsi/common.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "evolution of typed AST grammar architecture with held-out admission",
        "source_sha256": hashes})
    banks, metadata = create_evolving_banks(bank_config(config))
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    pools = build_pools(banks)
    write_json(output / "candidate_pools.json", pools)
    frozen = {"enabled_ops": ["add", "sub", "mul", "div", "mod", "xor", "shr", "mask", "not"],
              "max_complexity": 999, "rank_mode": "frozen"}
    population = initial_population(config["meta_seed"], size=config["population_size"])
    evolved, trace = evolve(population, pools["development"], generations=config["generations"],
                            elite_count=config["elite_count"], seed=config["meta_seed"])
    scores = {"frozen": {split: None for split in ("development", "admission", "final")},
              "evolved": {split: None for split in ("development", "admission", "final")}}
    scores = {"frozen": score_architectures(pools, banks, frozen, "frozen"),
              "evolved": score_architectures(pools, banks, evolved, "evolved")}
    eligible = ["frozen"]
    if scores["evolved"]["admission"]["correct"] >= scores["frozen"]["admission"]["correct"]:
        eligible.append("evolved")
    selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm))
    result = {"status": "completed", "scores": scores, "eligible": eligible, "selected": selected,
              "frozen_architecture": frozen, "evolved_architecture": evolved,
              "evolution_trace": trace, "training_family": config["train_family"],
              "eval_family": config["eval_family"], "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["candidate-bank superset grammar and mutation operators remain researcher-authored",
                              "oracle-labeled development/admission selection remains bounded",
                              "synthetic affine-transform domain", "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091943)
    parser.add_argument("--meta-seed", type=int, default=2026091943)
    parser.add_argument("--population-size", type=int, default=24)
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--elite-count", type=int, default=5)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--train-family", default="delimiter")
    parser.add_argument("--eval-family", default="ast_transition")
    args = parser.parse_args()
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
