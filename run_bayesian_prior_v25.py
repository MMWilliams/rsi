"""V25: admission-gated Bayesian prior for passive ambiguity resolution."""

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
    if mode == "cost":
        selected = rows[0] if rows else None
    elif mode == "bayesian":
        selected = choose(rows, config["generator_max_atoms"])
    else:
        raise ValueError(mode)
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
    source_names = ["run_bayesian_prior_v25.py", "rsi/generative_prior.py", "rsi/version_space.py", "rsi/cegis_search.py",
                    "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "generator-derived Bayesian prior with admission gate"})
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
    scores = {}
    for mode in ("cost", "bayesian"):
        scores[mode] = {"development": evaluate(banks["development"], macros, config, mode),
                        "admission": evaluate(banks["admission"], macros, config, mode),
                        "final": evaluate(banks["final"], macros, config, mode)}
        journal.append("prior_evaluated", {"mode": mode, "development_correct": scores[mode]["development"]["correct"],
                                           "admission_correct": scores[mode]["admission"]["correct"]})
    baseline = scores["cost"]
    candidate = scores["bayesian"]
    accepted = candidate["admission"]["correct"] >= baseline["admission"]["correct"] and \
        candidate["development"]["correct"] >= baseline["development"]["correct"] - config["development_tolerance"]
    # Non-regression is sufficient: the Bayesian prior is the new hypothesis
    # under test, so a deterministic tie on development/admission retains it
    # for the untouched final bank.
    selected = "bayesian" if accepted else "cost"
    result = {"status": "completed", "scores": scores, "accepted": accepted, "selected": selected,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["generator prior is hand-specified", "fixed DSL and candidate grammar", "small fresh banks",
                              "same-host oracle used only for grading", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091856)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--generator-max-atoms", type=int, default=4)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "candidate_limit": args.candidate_limit, "candidate_budget": args.candidate_budget,
              "max_atoms": args.max_atoms, "generator_max_atoms": args.generator_max_atoms,
              "development_tolerance": args.development_tolerance, "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
