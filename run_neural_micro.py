"""Small executable neural self-improvement loop for rapid hypothesis testing."""

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
from rsi.neural import LocalModel
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def pass_metrics(samples: dict[str, list[str]], tasks: list[dict]) -> dict:
    rows = []
    for task in tasks:
        outputs = samples[task["id"]]
        flags = [published_correct(text, task["visible"] + task["hidden"]) for text in outputs]
        rows.append({"task_id": task["id"], "n": len(outputs), "correct": sum(flags),
                     "pass_at_1": float(flags[0]) if flags else 0.0,
                     "pass_at_8": float(any(flags[:8])), "pass_at_16": float(any(flags[:16]))})
    return {"tasks": rows, "pass_at_k": {str(k): sum(row[f"pass_at_{k}"] for row in rows) / len(rows) for k in (1, 8, 16)}}


def verified_rows_from_samples(samples: dict[str, list[str]], tasks: list[dict], limit: int) -> list[dict]:
    task_map = {task["id"]: task for task in tasks}
    rows, seen = [], set()
    for task_id, outputs in samples.items():
        task = task_map[task_id]
        for raw in outputs:
            program = raw.strip().splitlines()[0] if raw.strip() else ""
            key = (task_id, program)
            if key in seen:
                continue
            if correct(program, task["visible"] + task["hidden"]):
                rows.append({"task_id": task_id, "program": program, "oracle_correct": True, "stratum": "harvest"})
                seen.add(key)
    rows.sort(key=lambda row: (row["task_id"], row["program"]))
    return rows[:limit]


def symbolic_bootstrap(tasks: list[dict], macros: list, budget: int) -> list[dict]:
    rows = []
    for task in tasks:
        details = {}
        solve(public_task(task), BASE_CONFIG, budget, 4, macros, [], diagnostics=details, pool_mode="baseline")
        for candidate in details["frontier"]:
            if correct(candidate["program"], task["visible"] + task["hidden"]):
                rows.append({"task_id": task["id"], "program": candidate["program"], "oracle_correct": True, "stratum": "anchor"})
                break
    return rows


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_neural_micro.py", "rsi/neural.py", "rsi/search_diagnostic.py", "rsi/search.py", "rsi/atom_pool_partial.py",
                    "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "python": sys.version, "platform": platform.platform()})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    bank_config = {"bank_seed": config["bank_seed"], "bank_counts": {"train": config["train_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    model = LocalModel(config, journal)
    task_map = {task["id"]: task for task in banks["train"]}
    bootstrap = symbolic_bootstrap(banks["train"], macros, config["search_budget"])
    write_json(output / "bootstrap_rows.json", bootstrap)
    bootstrap_train = model.distill(bootstrap, task_map, "search", output / "adapters" / "bootstrap", config["neural_seed"], steps=config["bootstrap_steps"])
    model.activate("search")
    final_base = model.sample([public_task(task) for task in banks["final"]], config["samples_per_task"], config["neural_seed"] + 100)
    write_json(output / "final_samples_after_bootstrap.json", final_base)
    base_metrics = pass_metrics(final_base, banks["final"])
    train_round1 = model.sample([public_task(task) for task in banks["train"]], config["samples_per_task"], config["neural_seed"] + 200)
    write_json(output / "train_samples_round1.json", train_round1)
    verified_round1 = verified_rows_from_samples(train_round1, banks["train"], config["max_verified_rows"])
    write_json(output / "round1_verified_rows.json", verified_round1)
    round1_train = model.distill(verified_round1, task_map, "search", output / "adapters" / "round1", config["neural_seed"] + 1, steps=config["selftrain_steps"])
    model.activate("search")
    final_round1 = model.sample([public_task(task) for task in banks["final"]], config["samples_per_task"], config["neural_seed"] + 300)
    write_json(output / "final_samples_after_round1.json", final_round1)
    round1_metrics = pass_metrics(final_round1, banks["final"])
    train_round2 = model.sample([public_task(task) for task in banks["train"]], config["samples_per_task"], config["neural_seed"] + 400)
    verified_round2 = verified_rows_from_samples(train_round2, banks["train"], config["max_verified_rows"])
    write_json(output / "round2_verified_rows.json", verified_round2)
    round2_train = model.distill(verified_round2, task_map, "search", output / "adapters" / "round2", config["neural_seed"] + 2, steps=config["selftrain_steps"])
    model.activate("search")
    final_round2 = model.sample([public_task(task) for task in banks["final"]], config["samples_per_task"], config["neural_seed"] + 500)
    write_json(output / "final_samples_after_round2.json", final_round2)
    round2_metrics = pass_metrics(final_round2, banks["final"])
    result = {"status": "completed", "bootstrap": bootstrap_train, "round1": round1_train, "round2": round2_train,
              "verified_rows": {"bootstrap": len(bootstrap), "round1": len(verified_round1), "round2": len(verified_round2)},
              "final_scores": {"after_bootstrap": base_metrics, "after_round1": round1_metrics, "after_round2": round2_metrics},
              "ledger": model.ledger, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["one neural seed", "small task bank", "bounded DSL", "finite hidden examples", "same-host oracle", "micro study is not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091741)
    parser.add_argument("--train-tasks", type=int, default=16)
    parser.add_argument("--final-tasks", type=int, default=16)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--bootstrap-steps", type=int, default=8)
    parser.add_argument("--selftrain-steps", type=int, default=8)
    parser.add_argument("--max-verified-rows", type=int, default=32)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "train_tasks": args.train_tasks, "final_tasks": args.final_tasks,
              "samples_per_task": args.samples_per_task, "bootstrap_steps": args.bootstrap_steps, "selftrain_steps": args.selftrain_steps,
              "max_verified_rows": args.max_verified_rows, "macro_source": args.macro_source, "model_id": "Qwen/Qwen3-0.6B",
              "model_revision": "c1899de289a04d12100db370d81485cdf75e47ca", "neural_seed": 17, "generation_batch_size": 8,
              "max_new_tokens": 96, "lora_steps": 8, "lora_batch_size": 4, "lora_learning_rate": 0.0002, "search_budget": 128, "device": "cuda:1"}
    print(json.dumps(run(config, ROOT / args.output), indent=2))
