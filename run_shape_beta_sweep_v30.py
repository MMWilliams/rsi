"""V30: admission-gated beta sweep for the hierarchical shape prior."""

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
from rsi.grammar_library import instantiate_templates, mine_templates
from rsi.retention_run import file_hash, seal_artifacts
from rsi.shape_prior import choose as shape_choose, program_shape_bonus, score as shape_score
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


def evaluate(tasks, macros, library, config, beta: float | None):
    learned = beta is not None
    rows = []
    for task in tasks:
        proposals = [] if not learned else instantiate_templates(
            library, task["visible"], macros, max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
        candidates = enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
            proposals=proposals, synthesize_constants=True, max_atoms=config["max_atoms"],
            limit=config["candidate_limit"], budget=config["candidate_budget"])
        selected = (shape_choose(candidates, library, beta) if learned else
                    generator_choose(candidates, config["generator_max_atoms"])) or {"program": "", "cost": 0.0}
        lp = program_log_probability(selected["program"], config["generator_max_atoms"])
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
               "shape_bonus": program_shape_bonus(selected["program"], library) if learned else 0.0,
               "selection_score": shape_score(selected, library, beta) if learned else lp}
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
    source_names = ["run_shape_beta_sweep_v30.py", "rsi/shape_prior.py", "rsi/grammar_library.py",
                    "rsi/generative_prior.py", "rsi/version_space.py", "rsi/cegis_search.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "admission-gated beta sweep over hierarchical shape priors"})
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
    library = mine_templates([task["reference"] for task in banks["development"]],
                             max_library=config["library_size"], max_length=config["library_max_length"],
                             min_frequency=config["library_min_frequency"])
    write_json(output / "shape_library.json", library)
    journal.append("shape_library_fitted", {"library_sha256": digest(library), "templates": len(library["templates"])})
    arms = {"control": None}
    for beta in config["betas"]:
        arms["beta_" + str(beta).replace(".", "p")] = float(beta)
    scores = {}
    for name, beta in arms.items():
        scores[name] = {split: evaluate(banks[split], macros, library, config, beta)
                        for split in ("development", "admission", "final")}
        journal.append("arm_evaluated", {"arm": name, "beta": beta,
                                         "development_correct": scores[name]["development"]["correct"],
                                         "admission_correct": scores[name]["admission"]["correct"]})
    control = scores["control"]
    eligible = [name for name in scores if name != "control"
                and scores[name]["admission"]["correct"] >= control["admission"]["correct"]
                and scores[name]["development"]["correct"] >= control["development"]["correct"] - config["development_tolerance"]]
    if eligible:
        selected = max(eligible, key=lambda name: (scores[name]["admission"]["correct"],
                                                    scores[name]["development"]["correct"],
                                                    -float(arms[name])))
    else:
        selected = "control"
    result = {"status": "completed", "scores": scores, "arms": arms, "eligible": eligible,
              "selected": selected, "shape_library": library,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["development references used for shape learning", "fixed DSL and grammar",
                              "beta grid is bounded and researcher-authored", "small fresh banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091866)
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
    parser.add_argument("--max-proposals", type=int, default=64)
    parser.add_argument("--slot-limit", type=int, default=8)
    parser.add_argument("--betas", type=float, nargs="+", default=[0.0, 1.0, 2.0, 3.0, 4.0])
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "candidate_limit": args.candidate_limit, "candidate_budget": args.candidate_budget,
              "max_atoms": args.max_atoms, "generator_max_atoms": args.generator_max_atoms,
              "development_tolerance": args.development_tolerance, "library_size": args.library_size,
              "library_max_length": args.library_max_length, "library_min_frequency": args.library_min_frequency,
              "max_proposals": args.max_proposals, "slot_limit": args.slot_limit, "betas": args.betas,
              "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
