"""V45: adversarial curriculum selection for verified macro learning."""

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
from rsi.grammar_library import instantiate_templates, mine_templates
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


def visible_diagnostic(task, config, macros):
    candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
        synthesize_constants=True, search_width=config["search_width"], limit=config["candidate_limit"],
        budget=config["candidate_budget"])
    selected = choose(candidates, config["generator_max_atoms"])
    return {"task_id": task["id"], "candidate_count": len(candidates),
            "program": selected["program"] if selected else "", "cost": selected.get("cost", 0.0) if selected else 0.0}


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


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_adversarial_curriculum_v45.py", "rsi/active_cegis.py", "rsi/compressed_space.py",
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
    journal.append("preregistration", {"config": config, "protocol": "visible-hardness curriculum with size-matched active controls",
                                       "source_sha256": hashes})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"train": config["training_tasks"], "development": config["development_tasks"],
                                   "admission": config["admission_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": config["reference_max_atoms"]}
    banks, metadata = create_banks(bank_config, exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    diagnostics = [visible_diagnostic(task, config, macros) for task in banks["train"]]
    write_json(output / "training_visible_diagnostics.json", diagnostics)
    verified = []
    for task in banks["train"]:
        public = {"id": task["id"], "visible": task["visible"]}
        first = counterexample_guided_solve(public, task["hidden"], budget=config["training_budget"],
            max_atoms=config["training_max_atoms"], macros=macros, synthesize_constants=True,
            max_queries=config["training_queries"])
        second = counterexample_guided_solve(public, task["hidden"], budget=config["training_budget"],
            max_atoms=config["training_max_atoms"], macros=macros, synthesize_constants=True,
            max_queries=config["training_queries"])
        if first != second:
            raise RuntimeError("active training replay mismatch")
        if published_correct(first["program"], task["visible"] + task["hidden"]):
            verified.append({"task_id": task["id"], "program": first["program"], "queries": first["queries"],
                             "replay_sha256": first["replay_sha256"]})
    write_json(output / "active_training.json", verified)
    verified_by_id = {row["task_id"]: row for row in verified}
    diagnostic_by_id = {row["task_id"]: row for row in diagnostics}
    verified_ids = [row["task_id"] for row in verified]
    size = config["curriculum_size"]
    uniform_ids = verified_ids[:size]
    hard_sorted = sorted(verified_ids, key=lambda task_id: (diagnostic_by_id[task_id]["candidate_count"], task_id))
    hard_low_ids = hard_sorted[:size]
    empty_ids = [task_id for task_id in hard_sorted if diagnostic_by_id[task_id]["candidate_count"] == 0]
    policies = {"uniform_17": uniform_ids[:min(17, len(uniform_ids))],
                "uniform_24": uniform_ids,
                "hard_low_24": hard_low_ids,
                "hard_empty": empty_ids,
                "hard_empty_padded_24": (empty_ids + [task_id for task_id in hard_sorted if task_id not in empty_ids])[:size]}
    write_json(output / "curriculum_selection.json", policies)
    libraries = {name: mine_templates([verified_by_id[task_id]["program"] for task_id in ids],
                                       max_library=config["library_size"], max_length=config["library_max_length"],
                                       min_frequency=config["library_min_frequency"])
                 for name, ids in policies.items()}
    write_json(output / "shape_libraries.json", libraries)
    journal.append("curriculum_fitted", {"verified_training_programs": len(verified),
        "policy_sizes": {name: len(ids) for name, ids in policies.items()},
        "empty_visible_tasks": len(empty_ids),
        "library_sha256": {name: digest(value) for name, value in libraries.items()}})
    scores = {"baseline": {split: evaluate(banks[split], macros, None, config, "baseline")
                            for split in ("development", "admission", "final")}}
    for name, library in libraries.items():
        scores[name] = {split: evaluate(banks[split], macros, library, config, name)
                        for split in ("development", "admission", "final")}
    baseline_admission = scores["baseline"]["admission"]["correct"]
    eligible = [name for name in policies if scores[name]["admission"]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda name: (scores[name]["development"]["correct"], -len(policies[name]), name)) if eligible else "baseline"
    result = {"status": "completed", "policies": policies, "scores": scores, "eligible": eligible,
              "selected": selected, "verified_training_programs": len(verified),
              "empty_visible_tasks": len(empty_ids), "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["active oracle feedback used in training", "curriculum policies use researcher-defined hardness features",
                              "fixed DSL and macro schema", "small synthetic banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091892)
    parser.add_argument("--training-tasks", type=int, default=72)
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
    parser.add_argument("--curriculum-size", type=int, default=24)
    parser.add_argument("--library-size", type=int, default=32)
    parser.add_argument("--library-max-length", type=int, default=3)
    parser.add_argument("--library-min-frequency", type=int, default=2)
    parser.add_argument("--max-proposals", type=int, default=256)
    parser.add_argument("--slot-limit", type=int, default=16)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
