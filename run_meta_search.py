"""Run a fresh visible-only portfolio experiment before hidden grading."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path

from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.meta_search import cost_frontier, map_elites_frontier, novelty_cost_frontier
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve


def _summary(rows: list[dict]) -> dict:
    metrics = {}
    for policy in sorted({row["policy"] for row in rows}):
        selected = [row for row in rows if row["policy"] == policy]
        metrics[policy] = {
            "tasks": len(selected),
            "selected_correct": sum(row["selected_correct"] for row in selected),
            "coverage_at_k": {str(k): sum(any(item["oracle_correct"] for item in row["frontier"][:k]) for row in selected) for k in (1, 4, 16, 64)},
            "verified_programs": sum(item["oracle_correct"] for row in selected for item in row["frontier"]),
            "distinct_programs": sum(len({item["program"] for item in row["frontier"]}) for row in selected),
        }
    base = metrics["cost"]
    contrasts = {}
    for policy, value in metrics.items():
        if policy == "cost":
            continue
        contrasts[policy + "_minus_cost"] = {key: value[key] for key in ("selected_correct", "verified_programs", "distinct_programs")}
        contrasts[policy + "_minus_cost"]["coverage64_delta"] = value["coverage_at_k"]["64"] - base["coverage_at_k"]["64"]
    return {"metrics": metrics, "contrasts": contrasts,
            "scope": "Fresh-task visible-only portfolio selector; no neural training; exploratory evidence, not RSI proof"}


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    journal = Journal(output / "events.jsonl")
    started = time.perf_counter()
    source_names = ["run_meta_search.py", "rsi/meta_search.py", "rsi/search_diagnostic.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes, "python": sys.version, "platform": platform.platform(), "solver_config": BASE_CONFIG})
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        exclusions.update(template(task["reference"]) for rows in banks.values() for task in rows)
    bank_config = {"bank_seed": config["bank_seed"], "bank_counts": {"final": config["tasks"]},
                   "visible_examples": config["visible_examples"], "hidden_examples": config["hidden_examples"], "max_atoms": config["max_atoms"]}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})
    raw, selected_rows = [], []
    for task in banks["final"]:
        public = public_task(task)
        arms = {}
        for mode in ("baseline", "partial_empty"):
            details = {}
            result = solve(public, BASE_CONFIG, config["budget"], config["max_atoms"], macros, [], diagnostics=details, pool_mode=mode)
            arms[mode] = details["frontier"]
            raw.append({"task_id": task["id"], "mode": mode, "result": result, "frontier": details["frontier"], "details_sha256": digest(details)})
        candidates = arms["baseline"] + arms["partial_empty"]
        policies = {"cost": cost_frontier(candidates, config["frontier_limit"]),
                    "map_elites": map_elites_frontier(candidates, config["frontier_limit"]),
                    "novelty_cost": novelty_cost_frontier(candidates, config["frontier_limit"])}
        for policy, frontier in policies.items():
            graded = [{**candidate, "oracle_correct": correct(candidate["program"], task["visible"] + task["hidden"])} for candidate in frontier]
            row = {"task_id": task["id"], "policy": policy, "frontier": graded,
                   "selected_correct": bool(graded and graded[0]["oracle_correct"]),
                   "candidate_pool": len(candidates), "selected_program": graded[0]["program"] if graded else ""}
            selected_rows.append(row)
            journal.append("portfolio_graded", row)
    result = _summary(selected_rows)
    result.update({"status": "completed", "config": config, "raw_searches": len(raw), "elapsed_seconds": time.perf_counter() - started,
                   "search_cost": {"expansions": sum(row["result"]["cost"]["expansions"] for row in raw),
                                   "generated_nodes": sum(row["result"]["cost"]["generated_nodes"] for row in raw),
                                   "primitive_executions": sum(row["result"]["cost"]["primitive_executions"] for row in raw)},
                   "limitations": ["single fresh bank", "bounded DSL", "finite hidden examples", "same-host execution", "portfolio is not recursive model improvement"]})
    write_json(output / "searches.json", raw)
    write_json(output / "graded.json", selected_rows)
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091701)
    parser.add_argument("--tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=128)
    parser.add_argument("--frontier-limit", type=int, default=64)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    configuration = {"bank_seed": args.bank_seed, "tasks": args.tasks, "budget": args.budget,
                     "frontier_limit": args.frontier_limit, "visible_examples": 3, "hidden_examples": 13,
                     "max_atoms": 4, "macro_source": args.macro_source}
    print(json.dumps(run(configuration, ROOT / args.output), indent=2))
