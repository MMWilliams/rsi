"""V44: contextual resource allocation for variable-width synthesis."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.invented_space import enumerate_invented, invented_correct
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


def exclusions():
    result = set()
    for path in sorted((ROOT / "runs").glob("**/protected_banks.json")):
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        result.update(template(task["reference"]) for task in all_task_rows(rows))
    return result


def options_for(task, config, macros):
    options = {}
    for width in (2, 3):
        candidates = enumerate_invented({"id": task["id"], "visible": task["visible"]}, config=BASE_CONFIG,
            search_width=width, families=[], invented_cost=99.0, limit=config["candidate_limit"],
            state_beam=config["state_beam"], budget=config["candidate_budget"], macros=macros,
            synthesize_constants=True)
        selected = candidates[0] if candidates else {"program": "", "cost": 0.0, "invented_atoms": 0}
        options[f"w{width}"] = {"program": selected["program"], "cost": selected["cost"],
                                 "candidate_count": len(candidates), "invented_atoms": selected.get("invented_atoms", 0),
                                 "correct": invented_correct(selected["program"], task["visible"] + task["hidden"])}
    options["context"] = {"empty": options["w2"]["candidate_count"] == 0,
                           "candidate_count": options["w2"]["candidate_count"],
                           "cost": options["w2"]["cost"]}
    return options


def use_policy(options, policy):
    context = options["context"]
    if policy == "width2":
        return "w2"
    if policy == "width3":
        return "w3"
    if policy == "fallback_empty":
        return "w3" if context["empty"] else "w2"
    if policy.startswith("fallback_count_"):
        threshold = int(policy.rsplit("_", 1)[1])
        return "w3" if context["candidate_count"] <= threshold else "w2"
    if policy.startswith("fallback_cost_"):
        threshold = float(policy.rsplit("_", 1)[1])
        return "w3" if context["cost"] >= threshold else "w2"
    raise ValueError(policy)


def score(options_by_id, tasks, policy, policy_id):
    rows = []
    for task in tasks:
        options = options_by_id[task["id"]]
        choice = use_policy(options, policy)
        selected = options[choice]
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected["cost"],
               "candidate_count": selected["candidate_count"], "search_width": int(choice[1:]),
               "policy": policy_id, "oracle_correct": selected["correct"]}
        row["replay_sha256"] = digest({key: row[key] for key in row if key not in ("replay_sha256", "oracle_correct")})
        rows.append(row)
    correct = sum(row["oracle_correct"] for row in rows)
    mean_width = sum(row["search_width"] for row in rows) / max(1, len(rows))
    return {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)),
            "mean_width": mean_width, "tasks": rows}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_adaptive_width_v44.py", "rsi/invented_space.py", "rsi/atom_pool_partial.py",
                    "rsi/cegis_search.py", "rsi/search.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py",
                    "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    policies = ["width2", "width3", "fallback_empty", "fallback_count_1", "fallback_count_2",
                "fallback_count_4", "fallback_cost_1.15", "fallback_cost_1.65", "fallback_cost_2.3"]
    journal.append("preregistration", {"config": config, "policies": policies,
                                       "protocol": "visible-context resource policy sweep with fixed width-2/width-3 options",
                                       "source_sha256": hashes})
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
    option_tables = {split: {task["id"]: options_for(task, config, macros) for task in banks[split]}
                     for split in ("development", "admission", "final")}
    write_json(output / "visible_option_tables.json", option_tables)
    scores = {policy: {split: score(option_tables[split], banks[split], policy, policy)
                       for split in ("development", "admission", "final")} for policy in policies}
    for policy in policies:
        journal.append("policy_evaluated", {"policy": policy,
            "development": scores[policy]["development"]["correct"],
            "admission": scores[policy]["admission"]["correct"],
            "final": scores[policy]["final"]["correct"],
            "mean_width_final": scores[policy]["final"]["mean_width"]})
    baseline_admission = scores["width2"]["admission"]["correct"]
    eligible = [policy for policy in policies if policy != "width2" and
                scores[policy]["admission"]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda policy: (scores[policy]["development"]["correct"],
                                                  -scores[policy]["development"]["mean_width"], policy)) if eligible else "width2"
    result = {"status": "completed", "policies": policies, "scores": scores, "eligible": eligible,
              "selected": selected, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["policy candidates are researcher-specified", "hidden feedback used for development/admission gating",
                              "fixed DSL and two resource widths", "small synthetic banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091890)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--reference-max-atoms", type=int, default=4)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--state-beam", type=int, default=8)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
