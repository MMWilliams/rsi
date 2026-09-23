"""V51: generic boundary-span invention without named Before/After operators."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.extended_banks import create_extended_banks
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import enumerate_semantic, evaluate_program, parse_span
from run_semantic_domain_v50 import evaluate


def infer_span_catalog(tasks, config):
    verified = []
    for task in tasks:
        candidates = enumerate_semantic({"id": task["id"], "visible": task["visible"]}, search_width=2,
            operators=("span",), semantic_cost=1.0, limit=config["candidate_limit"],
            state_beam=config["state_beam"], budget=config["candidate_budget"])
        for candidate in candidates:
            if candidate.get("semantic_atoms", 0) and evaluate_program(candidate["program"], task["visible"] + task["hidden"]):
                verified.append({"task_id": task["id"], "program": candidate["program"]})
                break
    return {"schema": "Slice(boundary,boundary)", "verified": verified}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_generic_span_v51.py", "run_semantic_domain_v50.py", "rsi/semantic_invention.py",
                    "rsi/extended_banks.py", "rsi/invented_space.py", "rsi/atom_pool_partial.py", "rsi/cegis_search.py",
                    "rsi/compressed_space.py", "rsi/search.py", "rsi/common.py", "rsi/generative_prior.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "protocol": "generic boundary-algebra induction in shifted domain", "source_sha256": hashes})
    banks, metadata = create_extended_banks({"bank_seed": config["bank_seed"],
        "bank_counts": {"train": config["training_tasks"], "development": config["development_tasks"],
                         "admission": config["admission_tasks"], "final": config["final_tasks"]},
        "visible_examples": config["visible_examples"], "hidden_examples": config["hidden_examples"]})
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    catalog = infer_span_catalog(banks["train"], config)
    write_json(output / "inferred_span_catalog.json", catalog)
    arms = [{"id": "baseline", "kind": "baseline", "search_width": 2, "semantic_cost": 99.0},
            {"id": "generic_c05", "kind": "invented", "search_width": 2, "semantic_cost": 0.5},
            {"id": "generic_c10", "kind": "invented", "search_width": 2, "semantic_cost": 1.0},
            {"id": "generic_c15", "kind": "invented", "search_width": 2, "semantic_cost": 1.5}]
    scores = {arm["id"]: {split: evaluate(banks[split], config, arm, ("span",))
                           for split in ("development", "admission", "final")} for arm in arms}
    baseline_admission = scores["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in arms if arm["id"] != "baseline" and scores[arm["id"]]["admission"]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda arm_id: (scores[arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    result = {"status": "completed", "arms": arms, "scores": scores, "eligible": eligible, "selected": selected,
              "schema": catalog["schema"], "training_verified": len(catalog["verified"]),
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["boundary algebra is researcher-bounded", "schema discovery uses synthetic training tasks",
                              "small shifted-domain banks", "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091902)
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
