"""Neural fragment-macro hybrid experiment."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.neural import LocalModel
from rsi.neural_macro_search import solve as fragment_solve, fragment_programs
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve as base_solve
from run_neural_micro import pass_metrics, symbolic_bootstrap


def fragment_one(task, macros, proposal, budget):
    first = fragment_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal])
    second = fragment_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal])
    if canonical(first) != canonical(second):
        raise RuntimeError("fragment search replay mismatch")
    return first


def fragment_samples(tasks, raw, macros, budget):
    samples, ranked, counts = {}, {}, {}
    for task in tasks:
        samples[task["id"]] = [fragment_one(task, macros, proposal, budget)["program"] for proposal in raw[task["id"]]]
        all_result = fragment_solve(public_task(task), BASE_CONFIG, budget, 4, macros, raw[task["id"]])
        ranked[task["id"]] = all_result["program"]
        counts[task["id"]] = all_result["neural_fragment_count"]
    return samples, ranked, counts


def selected_score(rows, tasks):
    scored = [{"task_id": task["id"], "program": rows[task["id"]],
               "oracle_correct": published_correct(rows[task["id"]], task["visible"] + task["hidden"])} for task in tasks]
    return {"tasks": scored, "correct": sum(row["oracle_correct"] for row in scored), "n": len(scored),
            "accuracy": sum(row["oracle_correct"] for row in scored) / max(1, len(scored))}


def collect_rows(tasks, raw, macros, budget, limit):
    rows, seen = [], set()
    for task in tasks:
        for proposal in raw[task["id"]]:
            result = fragment_one(task, macros, proposal, budget)
            program = result["program"]
            if correct(program, task["visible"] + task["hidden"]) and (task["id"], program) not in seen:
                seen.add((task["id"], program))
                rows.append({"task_id": task["id"], "program": program, "oracle_correct": True, "stratum": "fragment_hybrid"})
    rows.sort(key=lambda row: (row["task_id"], row["program"]))
    return rows[:limit]


def run(config: dict, output: Path):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_fragment_hybrid.py", "run_neural_micro.py", "rsi/neural_macro_search.py", "rsi/neural.py",
                    "rsi/search_diagnostic.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py",
                    "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "protocol": "neural contiguous fragments as symbolic macros"})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        prior = json.loads(path.read_text(encoding="utf-8"))
        for rows in prior.values():
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
    anchors = symbolic_bootstrap(banks["train"], macros, config["search_budget"])
    write_json(output / "anchor_rows.json", anchors)
    bootstrap = model.distill(anchors, task_map, "search", output / "adapters" / "bootstrap", config["neural_seed"], steps=config["bootstrap_steps"])
    model.activate("search")
    base_rows = {task["id"]: base_solve(public_task(task), BASE_CONFIG, config["search_budget"], 4, macros, [], pool_mode="baseline")["program"] for task in banks["final"]}
    base_final = selected_score(base_rows, banks["final"])
    write_json(output / "base_final.json", base_final)

    public_final = [public_task(task) for task in banks["final"]]
    pre_raw = model.sample(public_final, config["samples_per_task"], config["neural_seed"] + 100)
    pre_frag, pre_ranked, pre_counts = fragment_samples(banks["final"], pre_raw, macros, config["search_budget"])
    write_json(output / "raw_final_pre.json", pre_raw)
    write_json(output / "fragment_samples_pre.json", pre_frag)
    write_json(output / "fragment_ranked_pre.json", pre_ranked)
    write_json(output / "fragment_counts_pre.json", pre_counts)

    raw_train = model.sample([public_task(task) for task in banks["train"]], config["samples_per_task"], config["neural_seed"] + 200)
    verified = collect_rows(banks["train"], raw_train, macros, config["search_budget"], config["max_verified_rows"])
    write_json(output / "raw_train.json", raw_train)
    write_json(output / "verified_fragment_rows.json", verified)
    journal.append("fragment_harvest", {"rows": verified, "samples": config["train_tasks"] * config["samples_per_task"]})
    training = model.distill(verified, task_map, "search", output / "adapters" / "fragment_round1", config["neural_seed"] + 1, steps=config["fragment_steps"])
    model.activate("search")
    post_raw = model.sample(public_final, config["samples_per_task"], config["neural_seed"] + 300)
    post_frag, post_ranked, post_counts = fragment_samples(banks["final"], post_raw, macros, config["search_budget"])
    write_json(output / "raw_final_post.json", post_raw)
    write_json(output / "fragment_samples_post.json", post_frag)
    write_json(output / "fragment_ranked_post.json", post_ranked)
    write_json(output / "fragment_counts_post.json", post_counts)
    scores = {"base": base_final,
              "raw_pre": pass_metrics(pre_raw, banks["final"]), "fragment_pre": pass_metrics(pre_frag, banks["final"]),
              "ranked_pre": selected_score(pre_ranked, banks["final"]),
              "raw_post": pass_metrics(post_raw, banks["final"]), "fragment_post": pass_metrics(post_frag, banks["final"]),
              "ranked_post": selected_score(post_ranked, banks["final"])}
    result = {"status": "completed", "anchors": len(anchors), "bootstrap": bootstrap, "training": training,
              "verified_fragment_rows": len(verified), "scores": scores, "pre_fragment_counts": pre_counts,
              "post_fragment_counts": post_counts, "ledger": model.ledger,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["one neural seed", "small task banks", "fixed DSL", "finite hidden examples", "same-host oracle", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091791)
    parser.add_argument("--neural-seed", type=int, default=17)
    parser.add_argument("--train-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=16)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--bootstrap-steps", type=int, default=8)
    parser.add_argument("--fragment-steps", type=int, default=8)
    parser.add_argument("--max-verified-rows", type=int, default=48)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "neural_seed": args.neural_seed, "train_tasks": args.train_tasks, "final_tasks": args.final_tasks,
              "samples_per_task": args.samples_per_task, "bootstrap_steps": args.bootstrap_steps, "fragment_steps": args.fragment_steps,
              "max_verified_rows": args.max_verified_rows, "macro_source": args.macro_source, "model_id": "Qwen/Qwen3-0.6B",
              "model_revision": "c1899de289a04d12100db370d81485cdf75e47ca", "generation_batch_size": 8,
              "max_new_tokens": 96, "lora_steps": 8, "lora_batch_size": 4, "lora_learning_rate": 0.0002,
              "search_budget": 128, "device": "cuda:1"}
    print(json.dumps(run(config, ROOT / args.output), indent=2))
