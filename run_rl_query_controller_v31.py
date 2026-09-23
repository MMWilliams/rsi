"""V31: learn when an active CEGIS controller should spend an oracle query."""

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
from rsi.retention_run import file_hash, seal_artifacts
from rsi.rl_query_policy import TabularQueryPolicy, solve as rl_solve
from rsi.search import BASE_CONFIG


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


def evaluate(tasks, mode, config, macros, policy=None, max_queries=2):
    rows = []
    for task in tasks:
        public = {"id": task["id"], "visible": task["visible"]}
        if mode == "q0":
            result = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                                 max_atoms=config["max_atoms"], macros=macros,
                                                 synthesize_constants=True, max_queries=0)
        elif mode == "q2":
            result = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                                 max_atoms=config["max_atoms"], macros=macros,
                                                 synthesize_constants=True, max_queries=max_queries)
        else:
            result = rl_solve(task, policy, config, macros, max_queries=max_queries)
        rows.append({"task_id": task["id"], "program": result["program"],
                     "oracle_correct": published_correct(result["program"], task["visible"] + task["hidden"]),
                     "queries": result.get("queries", 0), "cost": result["cost"],
                     "trace": result.get("trace", []), "replay_sha256": result["replay_sha256"]})
    correct = sum(row["oracle_correct"] for row in rows)
    return {"mode": mode, "correct": correct, "n": len(rows),
            "accuracy": correct / max(1, len(rows)), "mean_queries": sum(r["queries"] for r in rows) / max(1, len(rows)),
            "tasks": rows}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_rl_query_controller_v31.py", "rsi/rl_query_policy.py", "rsi/active_cegis.py",
                    "rsi/cegis_search.py", "rsi/version_space.py", "rsi/search.py", "rsi/atom_pool_partial.py",
                    "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "tabular Q-learning for active CEGIS query allocation"})
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
    search_config = dict(BASE_CONFIG)
    search_config.update({"budget": config["budget"], "max_atoms": config["max_atoms"]})
    policy = TabularQueryPolicy(alpha=config["alpha"], gamma=config["gamma"],
                                query_penalty=config["query_penalty"], seed=config["policy_seed"])
    training = policy.fit(banks["development"], search_config, macros,
                          episodes=config["episodes"], max_queries=config["max_queries"])
    write_json(output / "policy.json", {"training": training, "q_values": policy.to_dict()})
    journal.append("policy_trained", training)
    scores = {}
    for split in ("development", "admission", "final"):
        tasks = banks[split]
        scores[split] = {mode: evaluate(tasks, mode, search_config, macros, policy, config["max_queries"])
                         for mode in ("q0", "q2", "rl")}
        journal.append("split_evaluated", {"split": split,
                                            "scores": {mode: scores[split][mode]["correct"] for mode in scores[split]}})
    baseline_admission = scores["admission"]["q0"]["correct"]
    eligible = [mode for mode in ("q2", "rl") if scores["admission"][mode]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda mode: (scores["admission"][mode]["correct"],
                                                scores["development"][mode]["correct"],
                                                -scores["admission"][mode]["mean_queries"])) if eligible else "q0"
    result = {"status": "completed", "config": config, "training": training,
              "scores": scores, "eligible": eligible, "selected": selected,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["oracle feedback is required during training and evaluation", "fixed DSL and grammar",
                              "tabular state features", "small fresh banks", "not proof of RSI"]}
    write_json(output / "evaluations.json", scores)
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091867)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=512)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--max-queries", type=int, default=2)
    parser.add_argument("--episodes", type=int, default=24)
    parser.add_argument("--alpha", type=float, default=0.35)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--query-penalty", type=float, default=0.02)
    parser.add_argument("--policy-seed", type=int, default=2026091868)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    output = Path(args.output)
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, output), indent=2))
