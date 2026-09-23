"""V78: true typed mutation of retained macro bodies."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.internal_body_mutation import synthesize_internal_mutation_predicates
from rsi.macro_library import mine_macro_library
from rsi.meta_macro import annotate_candidates, choose_candidate
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from run_ast_v66 import _direct_ast_candidates
from run_cross_family_macro_v75 import create_cross_family_banks, build_pools as build_base_pools


def build_pools(banks, library, max_variants):
    pools = build_base_pools(banks, library)
    for split in ("development", "admission", "final"):
        for task, pool in zip(banks[split], pools[split]):
            predicates = synthesize_internal_mutation_predicates(
                task["visible"], library, max_variants=max_variants)
            edited = [{**candidate, "macro_source": "internal_mutation"}
                      for candidate in _direct_ast_candidates(task, predicates)]
            for candidate in edited:
                candidate["oracle_correct"] = evaluate_program(
                    candidate["program"], task["visible"] + task["hidden"])
            pool["internal_mutation_candidate_count"] = len(edited)
            pool["candidates"].extend(annotate_candidates(edited))
    return pools


def score_arm(pools, banks, arm, arm_id):
    result = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task, pool in zip(banks[split], pools[split]):
            selected = choose_candidate(pool["candidates"], arm)
            selected = selected or {"program": "", "cost": 0.0, "macro_ids": [],
                                    "macro_source": "none", "oracle_correct": False}
            row = {"task_id": task["id"], "reference": task["reference"],
                   "program": selected["program"], "cost": selected["cost"],
                   "candidate_count": len(pool["candidates"]),
                   "legacy_candidate_count": pool["legacy_candidate_count"],
                   "direct_candidate_count": pool["direct_candidate_count"],
                   "macro_candidate_count": pool["macro_candidate_count"],
                   "internal_mutation_candidate_count": pool["internal_mutation_candidate_count"],
                   "macro_ids": selected.get("macro_ids", []),
                   "macro_source": selected.get("macro_source", "none"),
                   "arm": arm_id, "oracle_correct": selected["oracle_correct"]}
            row["replay_sha256"] = digest({key: row[key] for key in row
                                            if key not in ("replay_sha256", "oracle_correct")})
            rows.append(row)
        correct = sum(row["oracle_correct"] for row in rows)
        result[split] = {"correct": correct, "n": len(rows),
                         "accuracy": correct / max(1, len(rows)), "tasks": rows}
    return result


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_internal_body_mutation_v78.py", "run_cross_family_macro_v75.py", "run_ast_v66.py",
                    "rsi/internal_body_mutation.py", "rsi/macro_library.py", "rsi/meta_macro.py",
                    "rsi/self_editing_grammar.py", "rsi/semantic_invention.py", "rsi/stack_program.py",
                    "rsi/expression_synthesis.py", "rsi/evolving_domain.py", "rsi/common.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "development-only macro mining followed by typed internal parent-body mutation",
        "source_sha256": hashes})
    banks, metadata = create_cross_family_banks(config)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    library = mine_macro_library(banks["development"], max_macros=config["max_macros"])
    write_json(output / "macro_library.json", library)
    pools = build_pools(banks, library, config["max_variants"])
    write_json(output / "candidate_pools.json", pools)
    scores = {"legacy": score_arm(pools, banks, "legacy", "legacy"),
              "direct_grammar": score_arm(pools, banks, "direct", "direct_grammar"),
              "mined_macro": score_arm(pools, banks, "macro", "mined_macro"),
              "internal_mutation": score_arm(pools, banks, "internal_mutation", "internal_mutation")}
    eligible = ["direct_grammar"]
    for arm in ("mined_macro", "internal_mutation"):
        if scores[arm]["admission"]["correct"] >= scores["direct_grammar"]["admission"]["correct"]:
            eligible.append(arm)
    selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm))
    result = {"status": "completed", "scores": scores, "eligible": eligible, "selected": selected,
              "macro_library": library, "families": config["families"],
              "max_variants": config["max_variants"], "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["mutation vocabulary and balanced grafts are researcher-authored",
                              "development visible examples remain supervisory",
                              "cross-family relationship and admission gate remain authored",
                              "bounded mutation depth and constant bounds",
                              "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026092701)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--max-macros", type=int, default=16)
    parser.add_argument("--max-variants", type=int, default=128)
    args = parser.parse_args()
    args.families = {"train": "macro_transition", "development": "macro_transition",
                     "admission": "novel_operator_transition", "final": "novel_operator_transition"}
    args.bank_counts = {"train": args.training_tasks, "development": args.development_tasks,
                        "admission": args.admission_tasks, "final": args.final_tasks}
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
