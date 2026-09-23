"""V19: neural-proposal seeded CEGIS shortest-path synthesis."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.cegis_search import solve as cegis_solve
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.neural import LocalModel
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve as diagnostic_solve
from run_neural_micro import pass_metrics, symbolic_bootstrap


def selected_score(rows: dict[str, str], tasks: list[dict]) -> dict:
    scored = [{"task_id": task["id"], "program": rows[task["id"]],
               "oracle_correct": published_correct(rows[task["id"]], task["visible"] + task["hidden"])}
              for task in tasks]
    return {"tasks": scored, "correct": sum(row["oracle_correct"] for row in scored), "n": len(scored),
            "accuracy": sum(row["oracle_correct"] for row in scored) / max(1, len(scored))}


def _task_rows(node):
    if isinstance(node, dict):
        if {"id", "reference", "visible", "hidden"}.issubset(node):
            yield node
        else:
            for value in node.values():
                yield from _task_rows(value)
    elif isinstance(node, list):
        for value in node:
            yield from _task_rows(value)


def exclusions_from_history() -> set[str]:
    exclusions: set[str] = set()
    for path in sorted((ROOT / "runs").glob("**/protected_banks.json")):
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        exclusions.update(template(task["reference"]) for task in _task_rows(prior))
    return exclusions


def repair_one(task: dict, macros: list[str], proposal: str, budget: int, synthesize_constants: bool = False) -> dict:
    first = cegis_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal],
                        synthesize_constants=synthesize_constants)
    second = cegis_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal],
                         synthesize_constants=synthesize_constants)
    if canonical(first) != canonical(second):
        raise RuntimeError("CEGIS replay mismatch")
    return first


def repair_samples(tasks: list[dict], raw: dict[str, list[str]], macros: list[str], budget: int,
                    synthesize_constants: bool = False):
    samples, ranked, counts = {}, {}, {}
    for task in tasks:
        proposals = raw[task["id"]]
        samples[task["id"]] = [repair_one(task, macros, proposal, budget, synthesize_constants)["program"] for proposal in proposals]
        ranked_result = cegis_solve(public_task(task), BASE_CONFIG, budget, 4, macros, proposals,
                                    synthesize_constants=synthesize_constants)
        ranked[task["id"]] = ranked_result["program"]
        counts[task["id"]] = {"transitions": ranked_result["transition_count"],
                               "neural_transitions": ranked_result["neural_transition_count"]}
    return samples, ranked, counts


def collect_verified(tasks: list[dict], raw: dict[str, list[str]], macros: list[str], budget: int, limit: int,
                     synthesize_constants: bool = False):
    rows, seen = [], set()
    for task in tasks:
        for proposal in raw[task["id"]]:
            program = repair_one(task, macros, proposal, budget, synthesize_constants)["program"]
            key = (task["id"], program)
            if program and key not in seen and correct(program, task["visible"] + task["hidden"]):
                seen.add(key)
                rows.append({"task_id": task["id"], "program": program, "oracle_correct": True,
                             "stratum": "cegis_repair"})
    rows.sort(key=lambda row: (row["task_id"], row["program"]))
    return rows[:limit]


def run(config: dict, output: Path):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_cegis_v19.py", "run_neural_micro.py", "rsi/cegis_search.py", "rsi/neural.py",
                    "rsi/search_diagnostic.py", "rsi/search.py", "rsi/atom_pool_partial.py", "rsi/banks.py",
                    "rsi/oracle.py", "rsi/common.py", "audit_results.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                        "protocol": "visible-only CEGIS shortest path with neural typed transitions"})

    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"train": config["train_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions_from_history())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    model = LocalModel(config, journal)
    task_map = {task["id"]: task for task in banks["train"]}
    anchors = symbolic_bootstrap(banks["train"], macros, config["search_budget"])
    write_json(output / "anchor_rows.json", anchors)
    bootstrap = model.distill(anchors, task_map, "search", output / "adapters" / "bootstrap",
                              config["neural_seed"], steps=config["bootstrap_steps"])
    model.activate("search")

    base_rows, partial_rows, cegis_rows = {}, {}, {}
    for task in banks["final"]:
        public = public_task(task)
        base_rows[task["id"]] = diagnostic_solve(public, BASE_CONFIG, config["search_budget"], 4, macros, [], pool_mode="baseline")["program"]
        partial_rows[task["id"]] = diagnostic_solve(public, BASE_CONFIG, config["search_budget"], 4, macros, [], pool_mode="partial_empty")["program"]
        cegis_rows[task["id"]] = cegis_solve(public, BASE_CONFIG, config["search_budget"], 4, macros, [], None,
                                              synthesize_constants=config.get("synthesize_constants", False))["program"]
    base_score = selected_score(base_rows, banks["final"])
    partial_score = selected_score(partial_rows, banks["final"])
    cegis_score = selected_score(cegis_rows, banks["final"])
    write_json(output / "baseline_final.json", base_score)
    write_json(output / "partial_final.json", partial_score)
    write_json(output / "cegis_final.json", cegis_score)

    public_final = [public_task(task) for task in banks["final"]]
    pre_raw = model.sample(public_final, config["samples_per_task"], config["neural_seed"] + 100)
    pre_repair, pre_ranked, pre_counts = repair_samples(banks["final"], pre_raw, macros, config["search_budget"],
                                                        config.get("synthesize_constants", False))
    write_json(output / "raw_final_pre.json", pre_raw)
    write_json(output / "cegis_samples_pre.json", pre_repair)
    write_json(output / "cegis_ranked_pre.json", pre_ranked)
    write_json(output / "cegis_counts_pre.json", pre_counts)

    raw_train = model.sample([public_task(task) for task in banks["train"]], config["samples_per_task"], config["neural_seed"] + 200)
    verified = collect_verified(banks["train"], raw_train, macros, config["search_budget"], config["max_verified_rows"],
                                config.get("synthesize_constants", False))
    write_json(output / "raw_train.json", raw_train)
    write_json(output / "verified_cegis_rows.json", verified)
    journal.append("cegis_harvest", {"rows": verified, "samples": config["train_tasks"] * config["samples_per_task"]})
    training = model.distill(verified, task_map, "search", output / "adapters" / "cegis_round1",
                             config["neural_seed"] + 1, steps=config["cegis_steps"])
    model.activate("search")

    post_raw = model.sample(public_final, config["samples_per_task"], config["neural_seed"] + 300)
    post_repair, post_ranked, post_counts = repair_samples(banks["final"], post_raw, macros, config["search_budget"],
                                                           config.get("synthesize_constants", False))
    write_json(output / "raw_final_post.json", post_raw)
    write_json(output / "cegis_samples_post.json", post_repair)
    write_json(output / "cegis_ranked_post.json", post_ranked)
    write_json(output / "cegis_counts_post.json", post_counts)

    scores = {
        "baseline": base_score, "partial": partial_score, "cegis": cegis_score,
        "raw_pre": pass_metrics(pre_raw, banks["final"]),
        "cegis_pre": pass_metrics(pre_repair, banks["final"]),
        "ranked_pre": selected_score(pre_ranked, banks["final"]),
        "raw_post": pass_metrics(post_raw, banks["final"]),
        "cegis_post": pass_metrics(post_repair, banks["final"]),
        "ranked_post": selected_score(post_ranked, banks["final"]),
    }
    result = {"status": "completed", "anchors": len(anchors), "bootstrap": bootstrap, "training": training,
              "verified_cegis_rows": len(verified), "synthesize_constants": config.get("synthesize_constants", False),
              "scores": scores, "pre_cegis_counts": pre_counts,
              "post_cegis_counts": post_counts, "ledger": model.ledger,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["one neural seed", "small task banks", "fixed DSL", "finite hidden examples",
                              "same-host oracle", "visible-only solver does not prove semantic generality", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091821)
    parser.add_argument("--neural-seed", type=int, default=19)
    parser.add_argument("--train-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--samples-per-task", type=int, default=16)
    parser.add_argument("--bootstrap-steps", type=int, default=8)
    parser.add_argument("--cegis-steps", type=int, default=8)
    parser.add_argument("--max-verified-rows", type=int, default=64)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    parser.add_argument("--synthesize-constants", action="store_true")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "neural_seed": args.neural_seed, "train_tasks": args.train_tasks,
              "final_tasks": args.final_tasks, "samples_per_task": args.samples_per_task,
              "bootstrap_steps": args.bootstrap_steps, "cegis_steps": args.cegis_steps,
              "max_verified_rows": args.max_verified_rows, "macro_source": args.macro_source,
              "model_id": "Qwen/Qwen3-0.6B", "model_revision": "c1899de289a04d12100db370d81485cdf75e47ca",
              "generation_batch_size": 8, "max_new_tokens": 96, "lora_steps": 8, "lora_batch_size": 4,
              "lora_learning_rate": 0.0002, "search_budget": 128, "device": "cuda:1",
              "synthesize_constants": args.synthesize_constants}
    print(json.dumps(run(config, ROOT / args.output), indent=2))
