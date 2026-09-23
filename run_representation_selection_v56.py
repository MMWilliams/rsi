"""V56: select an observation language on a disjoint-alphabet domain."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import (enumerate_semantic, evaluate_program,
                                    induce_ord_range_predicates, induce_signature_predicates)
from run_induced_signature_v54 import bank_config, score


def verify_catalog(tasks, predicates, config):
    verified = []
    for task in tasks:
        candidates = enumerate_semantic({"id": task["id"], "visible": task["visible"]}, search_width=2,
            operators=("span",), semantic_cost=1.0, limit=config["candidate_limit"],
            state_beam=config["state_beam"], budget=config["candidate_budget"], induced_predicates=predicates)
        for candidate in candidates:
            if candidate.get("semantic_atoms", 0) and evaluate_program(candidate["program"], task["visible"] + task["hidden"]):
                verified.append({"task_id": task["id"], "program": candidate["program"]})
                break
    return verified


def representation_catalog(tasks, config):
    visible = [pair for task in tasks for pair in task["visible"]]
    catalogs = {
        "raw_ord": induce_ord_range_predicates(visible),
        "structural_family": induce_signature_predicates(visible),
    }
    return {name: {"predicates": predicates, "verified": verify_catalog(tasks, predicates, config)}
            for name, predicates in catalogs.items()}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_representation_selection_v56.py", "run_induced_signature_v54.py", "run_semantic_domain_v50.py",
                    "rsi/semantic_invention.py", "rsi/evolving_domain.py", "rsi/invented_space.py",
                    "rsi/atom_pool_partial.py", "rsi/cegis_search.py", "rsi/compressed_space.py", "rsi/search.py",
                    "rsi/common.py", "rsi/generative_prior.py", "rsi/retention_run.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "representation competition on disjoint Unicode alphabet; final score hidden until selection",
        "candidate_representations": ["raw_ord", "structural_family"], "source_sha256": hashes})
    banks, metadata = create_evolving_banks(bank_config(config))
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    catalogs = representation_catalog(banks["train"], config)
    write_json(output / "representation_catalogs.json", catalogs)
    arms = [{"id": "baseline", "kind": "baseline", "search_width": 2, "semantic_cost": 99.0, "representation": None},
            {"id": "raw_ord_c10", "kind": "induced", "search_width": 2, "semantic_cost": 1.0, "representation": "raw_ord"},
            {"id": "structural_family_c10", "kind": "induced", "search_width": 2, "semantic_cost": 1.0, "representation": "structural_family"}]
    scores = {}
    for arm in arms:
        predicates = catalogs[arm["representation"]]["predicates"] if arm["representation"] else []
        scores[arm["id"]] = score(banks, config, arm, predicates)
    baseline_admission = scores["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in arms if arm["id"] != "baseline" and
                scores[arm["id"]]["admission"]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda arm_id: (scores[arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    result = {"status": "completed", "arms": arms, "scores": scores, "eligible": eligible, "selected": selected,
              "training_family": config["train_family"], "eval_family": config["eval_family"],
              "representations": {name: {"predicate_count": len(value["predicates"]),
                                           "training_verified": len(value["verified"])}
                                  for name, value in catalogs.items()},
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["structural_family uses Unicode category as a candidate feature language",
                              "raw ordinal representation is ASCII/code-point biased", "synthetic disjoint domain",
                              "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091912)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=3)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--train-family", default="delimiter")
    parser.add_argument("--eval-family", default="transition_disjoint")
    parser.add_argument("--candidate-limit", type=int, default=256)
    parser.add_argument("--state-beam", type=int, default=8)
    parser.add_argument("--candidate-budget", type=int, default=4096)
    args = parser.parse_args()
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
