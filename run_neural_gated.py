"""Replay-and-gate neural self-improvement loop with exact rollback."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.neural import LocalModel, adapter_hash
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve
from run_neural_micro import pass_metrics, verified_rows_from_samples


def symbolic_bootstrap(tasks, macros, budget):
    rows = []
    for task in tasks:
        details = {}
        solve(public_task(task), BASE_CONFIG, budget, 4, macros, [], diagnostics=details, pool_mode="baseline")
        for candidate in details["frontier"]:
            if correct(candidate["program"], task["visible"] + task["hidden"]):
                rows.append({"task_id": task["id"], "program": candidate["program"], "oracle_correct": True, "stratum": "anchor"})
                break
    return rows


def merge_rows(*groups):
    merged, seen = [], set()
    for group in groups:
        for row in group:
            key = (row["task_id"], row["program"])
            if key not in seen:
                merged.append(row)
                seen.add(key)
    return merged


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_neural_gated.py", "run_neural_micro.py", "rsi/neural.py", "rsi/search_diagnostic.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "gate": "fresh validation pass@1 and pass@16, exact tensor rollback"})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    bank_config = {"bank_seed": config["bank_seed"], "bank_counts": {"train": config["train_tasks"], "validation": config["validation_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    model = LocalModel(config, journal)
    train_map = {task["id"]: task for task in banks["train"]}
    public_final = [public_task(task) for task in banks["final"]]
    public_validation = [public_task(task) for task in banks["validation"]]
    model.activate(None)
    unadapted_final = model.sample(public_final, config["samples_per_task"], config["neural_seed"] + 10)
    write_json(output / "final_samples_unadapted.json", unadapted_final)
    unadapted_score = pass_metrics(unadapted_final, banks["final"])

    anchors = symbolic_bootstrap(banks["train"], macros, config["search_budget"])
    write_json(output / "anchor_rows.json", anchors)
    bootstrap = model.distill(anchors, train_map, "search", output / "adapters" / "bootstrap", config["neural_seed"], steps=config["bootstrap_steps"])
    model.activate("search")
    states = {"bootstrap": {"training": bootstrap, "accepted": True, "score": None}}
    current_rows = anchors
    for round_index in (1, 2):
        harvest = model.sample([public_task(task) for task in banks["train"]], config["samples_per_task"], config["neural_seed"] + 100 * round_index)
        write_json(output / f"train_samples_round{round_index}.json", harvest)
        verified = verified_rows_from_samples(harvest, banks["train"], config["max_verified_rows"])
        write_json(output / f"verified_rows_round{round_index}.json", verified)
        parent_state = model.snapshot("search")
        parent_hash = adapter_hash(parent_state)
        parent_validation = model.sample(public_validation, config["samples_per_task"], config["neural_seed"] + 700 + round_index)
        write_json(output / f"validation_parent_round{round_index}.json", parent_validation)
        parent_score = pass_metrics(parent_validation, banks["validation"])
        pool = merge_rows(anchors, current_rows, verified)
        candidate_training = model.distill(pool, train_map, "search", output / "adapters" / f"round{round_index}", config["neural_seed"] + round_index, steps=config["selftrain_steps"])
        candidate_validation = model.sample(public_validation, config["samples_per_task"], config["neural_seed"] + 700 + round_index)
        write_json(output / f"validation_candidate_round{round_index}.json", candidate_validation)
        candidate_score = pass_metrics(candidate_validation, banks["validation"])
        p1_gain = candidate_score["pass_at_k"]["1"] - parent_score["pass_at_k"]["1"]
        p16_gain = candidate_score["pass_at_k"]["16"] - parent_score["pass_at_k"]["16"]
        accepted = p1_gain >= 0 and p16_gain >= 0 and (p1_gain > 0 or p16_gain > 0)
        if not accepted:
            restored = model.restore("search", parent_state)
            assert restored == adapter_hash(parent_state)
            current_rows = current_rows
        else:
            current_rows = pool
        states[f"round{round_index}"] = {"training": candidate_training, "accepted": accepted, "parent_hash": parent_hash,
                                          "verified_rows": len(verified), "parent_score": parent_score, "candidate_score": candidate_score,
                                          "p1_gain": p1_gain, "p16_gain": p16_gain}
        journal.append("gate_resolved", states[f"round{round_index}"])
        model.activate("search")
        final_samples = model.sample(public_final, config["samples_per_task"], config["neural_seed"] + 900 + round_index)
        write_json(output / f"final_samples_round{round_index}.json", final_samples)
        states[f"round{round_index}"]["final_score"] = pass_metrics(final_samples, banks["final"])
    result = {"status": "completed", "states": states, "unadapted_final": unadapted_score,
              "ledger": model.ledger, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["one neural seed", "small task banks", "bounded DSL", "finite hidden examples", "same-host oracle", "not proof of general RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091751)
    parser.add_argument("--train-tasks", type=int, default=16)
    parser.add_argument("--validation-tasks", type=int, default=8)
    parser.add_argument("--final-tasks", type=int, default=16)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--bootstrap-steps", type=int, default=8)
    parser.add_argument("--selftrain-steps", type=int, default=8)
    parser.add_argument("--max-verified-rows", type=int, default=32)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "train_tasks": args.train_tasks, "validation_tasks": args.validation_tasks, "final_tasks": args.final_tasks,
              "samples_per_task": args.samples_per_task, "bootstrap_steps": args.bootstrap_steps, "selftrain_steps": args.selftrain_steps,
              "max_verified_rows": args.max_verified_rows, "macro_source": args.macro_source, "model_id": "Qwen/Qwen3-0.6B",
              "model_revision": "c1899de289a04d12100db370d81485cdf75e47ca", "neural_seed": 17, "generation_batch_size": 8,
              "max_new_tokens": 96, "lora_steps": 8, "lora_batch_size": 4, "lora_learning_rate": 0.0002, "search_budget": 128, "device": "cuda:1"}
    print(json.dumps(run(config, ROOT / args.output), indent=2))
