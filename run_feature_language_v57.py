"""V57: synthesize and select a feature language on a disjoint alphabet."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.predicate_synthesis import synthesize_feature_languages
from rsi.retention_run import file_hash, seal_artifacts
from run_induced_signature_v54 import bank_config, score
from run_representation_selection_v56 import verify_catalog


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_feature_language_v57.py", "run_induced_signature_v54.py", "run_representation_selection_v56.py",
                    "run_semantic_domain_v50.py", "rsi/predicate_synthesis.py", "rsi/semantic_invention.py",
                    "rsi/evolving_domain.py", "rsi/invented_space.py", "rsi/atom_pool_partial.py", "rsi/cegis_search.py",
                    "rsi/compressed_space.py", "rsi/search.py", "rsi/common.py", "rsi/generative_prior.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "generated feature-language grammar with admission-gated selection on disjoint alphabet",
        "selection_rule": "maximize development among languages meeting baseline admission; complexity breaks ties",
        "source_sha256": hashes})
    banks, metadata = create_evolving_banks(bank_config(config))
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    visible = [pair for task in banks["train"] for pair in task["visible"]]
    languages = synthesize_feature_languages(visible)
    catalogs = {language["id"]: {**language, "training_verified": len(verify_catalog(banks["train"], language["predicates"], config))}
                for language in languages}
    write_json(output / "synthesized_languages.json", catalogs)
    arms = [{"id": "baseline", "kind": "baseline", "search_width": 2, "semantic_cost": 99.0,
             "language": None}]
    for language in languages:
        arms.append({"id": language["id"], "kind": "induced", "search_width": 2, "semantic_cost": 1.0,
                     "language": language["id"]})
    scores = {arm["id"]: score(banks, config, arm,
                               catalogs[arm["language"]]["predicates"] if arm["language"] else [])
              for arm in arms}
    baseline_admission = scores["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in arms if arm["id"] != "baseline" and
                scores[arm["id"]]["admission"]["correct"] >= baseline_admission]
    complexity = {language["id"]: language["complexity"] for language in languages}
    selected = max(eligible, key=lambda arm_id: (scores[arm_id]["development"]["correct"],
                                                  -complexity[arm_id], arm_id)) if eligible else "baseline"
    result = {"status": "completed", "arms": arms, "scores": scores, "eligible": eligible, "selected": selected,
              "training_family": config["train_family"], "eval_family": config["eval_family"],
              "language_summary": {name: {"complexity": value["complexity"],
                                           "predicate_count": len(value["predicates"]),
                                           "training_verified": value["training_verified"]}
                                   for name, value in catalogs.items()},
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["feature grammar is bounded to ordinal/category primitives",
                              "synthetic disjoint domain", "Unicode category remains an available primitive",
                              "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091914)
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
