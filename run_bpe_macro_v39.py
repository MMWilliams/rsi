"""V39: MDL/BPE grammar induction from the improver's own verified trajectories."""

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
from rsi.bpe_library import mine_bpe_templates
from rsi.common import ROOT, Journal, digest, write_json
from rsi.compressed_space import enumerate_compressed
from rsi.generative_prior import choose, program_log_probability
from rsi.grammar_library import instantiate_templates
from rsi.retention_run import file_hash, seal_artifacts


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


def evaluate(tasks, macros, library, config, learned):
    rows = []
    for task in tasks:
        proposals = [] if not learned else instantiate_templates(library, task["visible"], macros,
            max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
        candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
            compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
            limit=config["candidate_limit"], budget=config["candidate_budget"])
        selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
        lp = program_log_probability(selected["program"], config["generator_max_atoms"])
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
               "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
               "search_width": config["search_width"], "learned": learned}
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
    source_names = ["run_bpe_macro_v39.py", "rsi/bpe_library.py", "rsi/compressed_space.py", "rsi/active_cegis.py",
                    "rsi/grammar_library.py", "rsi/generative_prior.py", "rsi/cegis_search.py", "rsi/version_space.py",
                    "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py",
                    "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "MDL byte-pair macro grammar induction from verified trajectories"})
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
    training_rows = []
    for task in banks["development"]:
        public = {"id": task["id"], "visible": task["visible"]}
        result = counterexample_guided_solve(public, task["hidden"], budget=config["training_budget"],
            max_atoms=config["training_max_atoms"], macros=macros, synthesize_constants=True,
            max_queries=config["training_queries"])
        if published_correct(result["program"], task["visible"] + task["hidden"]):
            training_rows.append({"task_id": task["id"], "program": result["program"],
                                  "queries": result["queries"], "replay_sha256": result["replay_sha256"]})
    write_json(output / "active_training.json", training_rows)
    library = mine_bpe_templates([row["program"] for row in training_rows if row["program"]],
        max_merges=config["max_merges"], max_library=config["max_library"])
    write_json(output / "bpe_library.json", library)
    journal.append("library_fitted", {"library_sha256": digest(library), "templates": len(library["templates"]),
                                       "verified_training_programs": len(training_rows)})
    baseline = {split: evaluate(banks[split], macros, library, config, False) for split in ("development", "admission", "final")}
    learned = {split: evaluate(banks[split], macros, library, config, True) for split in ("development", "admission", "final")}
    accepted = learned["admission"]["correct"] >= baseline["admission"]["correct"] and \
        learned["development"]["correct"] >= baseline["development"]["correct"] - config["development_tolerance"]
    result = {"status": "completed", "baseline": baseline, "learned": learned, "accepted": accepted,
              "selected": "learned" if accepted else "baseline", "bpe_library": library,
              "verified_training_programs": len(training_rows), "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["active oracle feedback used during development", "base AST shape vocabulary",
                              "search width is researcher-bounded", "small fresh banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091881)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--reference-max-atoms", type=int, default=4)
    parser.add_argument("--training-max-atoms", type=int, default=6)
    parser.add_argument("--training-budget", type=int, default=512)
    parser.add_argument("--training-queries", type=int, default=2)
    parser.add_argument("--search-width", type=int, default=2)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--generator-max-atoms", type=int, default=4)
    parser.add_argument("--development-tolerance", type=int, default=2)
    parser.add_argument("--max-merges", type=int, default=64)
    parser.add_argument("--max-library", type=int, default=32)
    parser.add_argument("--max-proposals", type=int, default=256)
    parser.add_argument("--slot-limit", type=int, default=16)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
