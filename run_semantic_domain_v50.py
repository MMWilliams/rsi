"""V50: semantic operator invention under a shifted task domain."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.extended_banks import create_extended_banks
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import enumerate_semantic, evaluate_program, parse_semantic
from rsi.invented_space import _split_atoms
from rsi.compressed_space import enumerate_compressed
from rsi.generative_prior import choose


def evaluate(tasks, config, arm, learned_ops=(), include_transitions=False, include_runs=False,
             induced_predicates=None):
    rows = []
    for task in tasks:
        if arm["kind"] == "baseline":
            candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]},
                synthesize_constants=True, search_width=arm["search_width"], limit=config["candidate_limit"], budget=config["candidate_budget"])
        else:
            candidates = enumerate_semantic({"id": task["id"], "visible": task["visible"]},
                search_width=arm["search_width"], operators=learned_ops, semantic_cost=arm["semantic_cost"],
                limit=config["candidate_limit"], state_beam=config["state_beam"], budget=config["candidate_budget"],
                include_transitions=include_transitions, include_runs=include_runs,
                induced_predicates=induced_predicates)
        selected = candidates[0] if candidates else {"program": "", "cost": 0.0, "semantic_atoms": 0}
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected["cost"],
               "candidate_count": len(candidates), "semantic_atoms": selected.get("semantic_atoms", 0),
               "search_width": arm["search_width"], "arm": arm["id"], "oracle_correct": evaluate_program(selected["program"], task["visible"] + task["hidden"])}
        row["replay_sha256"] = digest({key: row[key] for key in row if key not in ("replay_sha256", "oracle_correct")})
        rows.append(row)
    correct = sum(row["oracle_correct"] for row in rows)
    return {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}


def infer_catalog(tasks, config):
    verified = []
    operators = set()
    for task in tasks:
        candidates = enumerate_semantic({"id": task["id"], "visible": task["visible"]}, search_width=2,
            operators=("before", "after"), semantic_cost=1.0, limit=config["candidate_limit"],
            state_beam=config["state_beam"], budget=config["candidate_budget"])
        for candidate in candidates:
            if candidate.get("semantic_atoms", 0) and evaluate_program(candidate["program"], task["visible"] + task["hidden"]):
                atoms = [atom for atom in _split_atoms(candidate["program"][7:-1]) if parse_semantic(atom)]
                operators.update(parse_semantic(atom)[0] for atom in atoms if parse_semantic(atom))
                verified.append({"task_id": task["id"], "program": candidate["program"], "operators": sorted(operators)})
                break
    return {"operators": sorted(operators), "verified": verified}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_semantic_domain_v50.py", "rsi/semantic_invention.py", "rsi/extended_banks.py",
                    "rsi/invented_space.py", "rsi/atom_pool_partial.py", "rsi/cegis_search.py", "rsi/compressed_space.py",
                    "rsi/search.py", "rsi/common.py", "rsi/generative_prior.py", "rsi/retention_run.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "protocol": "shifted variable-length delimiter domain with visible-only semantic operator discovery", "source_sha256": hashes})
    banks, metadata = create_extended_banks({"bank_seed": config["bank_seed"],
        "bank_counts": {"train": config["training_tasks"], "development": config["development_tasks"],
                         "admission": config["admission_tasks"], "final": config["final_tasks"]},
        "visible_examples": config["visible_examples"], "hidden_examples": config["hidden_examples"]})
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    catalog = infer_catalog(banks["train"], config)
    write_json(output / "inferred_operator_catalog.json", catalog)
    learned_ops = tuple(catalog["operators"])
    arms = [{"id": "baseline", "kind": "baseline", "search_width": 2, "semantic_cost": 99.0}]
    for cost in (0.5, 1.0, 1.5):
        arms.append({"id": f"invented_c{str(cost).replace('.', '')}", "kind": "invented", "search_width": 2, "semantic_cost": cost})
    scores = {arm["id"]: {split: evaluate(banks[split], config, arm, learned_ops)
                           for split in ("development", "admission", "final")} for arm in arms}
    baseline_admission = scores["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in arms if arm["id"] != "baseline" and scores[arm["id"]]["admission"]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda arm_id: (scores[arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    result = {"status": "completed", "arms": arms, "scores": scores, "eligible": eligible, "selected": selected,
              "inferred_operators": learned_ops, "training_verified": len(catalog["verified"]),
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["semantic metalanguage is researcher-bounded", "operator catalog learned from synthetic training tasks",
                              "small shifted-domain banks", "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091900)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=3)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--state-beam", type=int, default=8)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    args = parser.parse_args()
    config = vars(args).copy()
    config.pop("output", None)
    print(json.dumps(run(config, Path(args.output)), indent=2))
