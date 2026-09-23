"""V32: structural Bayesian confidence gating for active CEGIS."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.confidence_query import BayesianConfidence, solve as confidence_solve, trajectory
from rsi.retention_run import file_hash, seal_artifacts
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


def fixed(tasks, mode, config, macros, max_queries):
    rows = []
    for task in tasks:
        public = {"id": task["id"], "visible": task["visible"]}
        q = 0 if mode == "q0" else max_queries
        result = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                             max_atoms=config["max_atoms"], macros=macros,
                                             synthesize_constants=True, max_queries=q)
        rows.append({"task_id": task["id"], "program": result["program"],
                     "oracle_correct": published_correct(result["program"], task["visible"] + task["hidden"]),
                     "queries": result.get("queries", 0), "cost": result["cost"],
                     "replay_sha256": result["replay_sha256"]})
    return summarize(mode, rows)


def summarize(mode, rows):
    correct = sum(row["oracle_correct"] for row in rows)
    return {"mode": mode, "correct": correct, "n": len(rows),
            "accuracy": correct / max(1, len(rows)),
            "mean_queries": sum(row["queries"] for row in rows) / max(1, len(rows)),
            "tasks": rows}


def learned(tasks, model, threshold, config, macros, max_queries):
    rows = []
    for task in tasks:
        first = confidence_solve(task, model, threshold, config, macros, max_queries)
        second = confidence_solve(task, model, threshold, config, macros, max_queries)
        if first["replay_sha256"] != second["replay_sha256"]:
            raise RuntimeError("confidence replay mismatch")
        rows.append({"task_id": task["id"], "program": first["program"],
                     "oracle_correct": published_correct(first["program"], task["visible"] + task["hidden"]),
                     "queries": first["queries"], "cost": first["cost"], "trace": first["trace"],
                     "replay_sha256": first["replay_sha256"]})
    return summarize(f"confidence_{threshold:g}", rows)


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_confidence_query_v32.py", "rsi/confidence_query.py", "rsi/meta_ranker.py",
                    "rsi/active_cegis.py", "rsi/cegis_search.py", "rsi/version_space.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "audit_results.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "structural Bayesian confidence gate for active CEGIS"})
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
    model = BayesianConfidence(smoothing=config["smoothing"])
    training_rows = []
    for task in banks["development"]:
        for result, query_count in trajectory(task, search_config, macros, config["max_queries"]):
            training_rows.append((result, query_count,
                                  published_correct(result["program"], task["visible"] + task["hidden"])))
    training = model.fit(training_rows)
    write_json(output / "model.json", {"training": training, "model": model.to_dict()})
    journal.append("model_trained", training)
    scores = {}
    for split in ("development", "admission", "final"):
        scores[split] = {"q0": fixed(banks[split], "q0", search_config, macros, config["max_queries"]),
                         "q2": fixed(banks[split], "q2", search_config, macros, config["max_queries"])}
        for threshold in config["thresholds"]:
            scores[split][f"confidence_{threshold:g}"] = learned(
                banks[split], model, threshold, search_config, macros, config["max_queries"])
        journal.append("split_evaluated", {"split": split,
                                            "scores": {key: value["correct"] for key, value in scores[split].items()}})
    baseline_admission = scores["admission"]["q0"]["correct"]
    candidates = ["q2"] + [f"confidence_{threshold:g}" for threshold in config["thresholds"]]
    eligible = [name for name in candidates if scores["admission"][name]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda name: (scores["admission"][name]["correct"],
                                                scores["development"][name]["correct"],
                                                -scores["admission"][name]["mean_queries"])) if eligible else "q0"
    result = {"status": "completed", "config": config, "training": training, "scores": scores,
              "eligible": eligible, "selected": selected, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["oracle feedback is required during training and evaluation", "fixed DSL and grammar",
                              "structural naive Bayes independence assumption", "small fresh banks", "not proof of RSI"]}
    write_json(output / "evaluations.json", scores)
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091869)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--budget", type=int, default=512)
    parser.add_argument("--max-atoms", type=int, default=6)
    parser.add_argument("--max-queries", type=int, default=2)
    parser.add_argument("--smoothing", type=float, default=1.0)
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.50, 0.65, 0.80, 0.90])
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    output = Path(args.output)
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, output), indent=2))
