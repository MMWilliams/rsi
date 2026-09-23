"""Replicate a frozen evolved search policy on independent fresh banks."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import time
from pathlib import Path

from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.retention_run import file_hash, seal_artifacts
from run_policy_evolution import evaluate


def run(source_run: Path, output: Path, seeds: list[int], tasks: int, budget: int) -> dict:
    if output.exists():
        raise FileExistsError(output)
    source = json.loads((source_run / "results.json").read_text(encoding="utf-8"))
    config = json.loads((source_run / "config.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True)
    journal = Journal(output / "events.jsonl")
    source_names = ["run_policy_replication.py", "run_policy_evolution.py", "rsi/search_diagnostic.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    replication_config = {"source_run": str(source_run.relative_to(ROOT)), "seeds": seeds, "tasks": tasks, "budget": budget,
                          "champion_policy": source["champion_policy"], "base_policy": source["base_policy"]}
    write_json(output / "config.json", replication_config)
    journal.append("preregistration", {"config": replication_config, "source_sha256": hashes, "selection_closed": True,
                                       "python": sys.version, "platform": platform.platform()})
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    banks_by_seed, scores = {}, []
    for seed in seeds:
        bank_config = {"bank_seed": seed, "bank_counts": {"final": tasks}, "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
        banks, metadata = create_banks(bank_config, exclusions)
        exclusions.update(template(task["reference"]) for rows in banks.values() for task in rows)
        banks_by_seed[str(seed)] = {"tasks": banks["final"], "metadata": metadata["final"]}
        base = evaluate(source["base_policy"], banks["final"], budget, macros)
        champion = evaluate(source["champion_policy"], banks["final"], budget, macros)
        row = {"seed": seed, "base": {key: value for key, value in base.items() if key != "rows"},
               "champion": {key: value for key, value in champion.items() if key != "rows"},
               "base_rows": base["rows"], "champion_rows": champion["rows"]}
        scores.append(row)
        journal.append("replication_scored", row)
    aggregate = {}
    for policy in ("base", "champion"):
        aggregate[policy] = {metric: sum(row[policy][metric] for row in scores) for metric in ("selected_correct", "coverage64", "expansions", "generated_nodes", "tasks")}
    result = {"status": "completed", "selection_closed": True, "scores": scores, "aggregate": aggregate,
              "delta_champion_minus_base": {metric: aggregate["champion"][metric] - aggregate["base"][metric] for metric in aggregate["base"]},
              "limitations": ["three replication banks", "bounded DSL", "finite hidden examples", "same-host oracle", "no retuning during replication"]}
    write_json(output / "replication_banks.json", banks_by_seed)
    write_json(output / "protected_banks.json", {f"seed_{seed}": value["tasks"] for seed, value in banks_by_seed.items()})
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_run")
    parser.add_argument("output")
    parser.add_argument("--seeds", default="2026091711,2026091712,2026091713")
    parser.add_argument("--tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=128)
    args = parser.parse_args()
    result = run(ROOT / args.source_run, ROOT / args.output, [int(value) for value in args.seeds.split(",")], args.tasks, args.budget)
    print(json.dumps(result, indent=2))
