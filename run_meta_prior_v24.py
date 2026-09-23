"""V24: distill interactive CEGIS feedback into a passive synthesis prior."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.meta_ranker import PairwisePrior
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


def historical_exclusions():
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("**/protected_banks.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        exclusions.update(template(task["reference"]) for task in all_task_rows(rows))
    return exclusions


def candidates(task, macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def passive_score(task, rows, prior=None):
    chosen = (prior.choose(rows) if prior else (rows[0] if rows else None))
    chosen = chosen or {"program": "", "cost": 0.0}
    payload = {"task_id": task["id"], "program": chosen["program"], "cost": chosen.get("cost", 0.0),
               "candidate_count": len(rows), "rank_score": prior.score(chosen) if prior else None}
    payload["replay_sha256"] = digest(payload)
    return {**payload, "oracle_correct": published_correct(chosen["program"], task["visible"] + task["hidden"])}


def evaluate(tasks, macros, config, prior=None):
    rows = []
    for task in tasks:
        rows.append(passive_score(task, candidates(task, macros, config), prior))
    correct = sum(row["oracle_correct"] for row in rows)
    return {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_meta_prior_v24.py", "rsi/meta_ranker.py", "rsi/active_cegis.py", "rsi/version_space.py",
                    "rsi/cegis_search.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py",
                    "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py",
                    "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "active development feedback distilled into passive pairwise prior"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"], "admission": config["admission_tasks"],
                                   "final": config["final_tasks"]}, "visible_examples": 3, "hidden_examples": 13,
                   "max_atoms": 4}
    banks, metadata = create_banks(bank_config, historical_exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    prior = PairwisePrior(config["learning_rate"], config["margin"])
    training_rows = []
    for task in banks["development"]:
        pool = candidates(task, macros, config)
        active = counterexample_guided_solve({"id": task["id"], "visible": task["visible"]}, task["hidden"],
                                             budget=config["active_budget"], max_atoms=config["max_atoms"],
                                             macros=macros, max_queries=config["active_queries"])
        positive = next((row for row in pool if row["program"] == active["program"]), None)
        if positive is not None:
            training_rows.append({"task_id": task["id"], "positive": positive, "candidates": pool,
                                  "queries": active["queries"], "active_program": active["program"]})
    fit_rows = [(row["positive"], row["candidates"]) for row in training_rows]
    fit = prior.fit(fit_rows, epochs=config["epochs"])
    write_json(output / "training.json", training_rows)
    write_json(output / "prior.json", fit)
    journal.append("prior_fitted", {"training_tasks": len(training_rows), "updates": fit["updates"],
                                    "prior_sha256": digest(fit)})

    baseline_admission = evaluate(banks["admission"], macros, config, None)
    learned_admission = evaluate(banks["admission"], macros, config, prior)
    baseline_final = evaluate(banks["final"], macros, config, None)
    learned_final = evaluate(banks["final"], macros, config, prior)
    accepted = learned_admission["correct"] >= baseline_admission["correct"]
    selected = learned_final if accepted else baseline_final
    selected_name = "learned_prior" if accepted else "baseline"
    result = {"status": "completed", "training_tasks": len(training_rows), "prior_updates": fit["updates"],
              "admission": {"baseline": baseline_admission, "learned_prior": learned_admission},
              "final": {"baseline": baseline_final, "learned_prior": learned_final, "selected": selected,
                        "selected_name": selected_name}, "accepted": accepted,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["oracle feedback used during development", "fixed DSL and candidate grammar",
                              "small fresh banks", "pairwise prior is bounded and hand-featured", "not proof of RSI"]}
    write_json(output / "evaluations.json", {"admission": result["admission"], "final": result["final"]})
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091855)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--candidate-limit", type=int, default=128)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--active-budget", type=int, default=512)
    parser.add_argument("--active-queries", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--margin", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks,
              "candidate_limit": args.candidate_limit, "candidate_budget": args.candidate_budget,
              "max_atoms": args.max_atoms, "active_budget": args.active_budget, "active_queries": args.active_queries,
              "learning_rate": args.learning_rate, "margin": args.margin, "epochs": args.epochs,
              "macro_source": args.macro_source}
    print(json.dumps(run(config, Path(args.output)), indent=2))
