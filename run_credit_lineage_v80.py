"""V80: multi-generation, cross-task-credit lineage evolution."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.credit_lineage import evolve_credit_lineage
from rsi.internal_body_mutation import synthesize_internal_mutation_predicates
from rsi.macro_library import mine_macro_library, synthesize_macro_predicates
from rsi.meta_macro import annotate_candidates, choose_candidate
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from rsi.expression_synthesis import synthesize_ordinal_expressions
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from run_ast_v66 import _direct_ast_candidates
from run_cross_family_macro_v75 import create_cross_family_banks


def build_pools(banks, base_library, credit_library, max_variants, reserve_grafts=False,
                reserve_rotate=False):
    pools = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task in banks[split]:
            legacy = [{**candidate, "macro_source": "legacy"}
                      for candidate in _direct_ast_candidates(task, synthesize_ordinal_expressions(task["visible"], compose=False))]
            direct = [{**candidate, "macro_source": "direct_grammar"}
                      for candidate in _direct_ast_candidates(task, synthesize_self_edit_predicates(task["visible"], SAFE_OPS))]
            base = [{**candidate, "macro_source": "mined_visible_only"}
                    for candidate in _direct_ast_candidates(task, synthesize_macro_predicates(task["visible"], base_library))]
            credit = [{**candidate, "macro_source": "credit_lineage"}
                      for candidate in _direct_ast_candidates(task, synthesize_macro_predicates(task["visible"], credit_library))]
            local = [{**candidate, "macro_source": "internal_mutation"}
                     for candidate in _direct_ast_candidates(task, synthesize_internal_mutation_predicates(
                         task["visible"], base_library, max_variants, reserve_grafts=reserve_grafts,
                         reserve_rotate=reserve_rotate))]
            candidates = legacy + direct + base + credit + local
            for candidate in candidates:
                candidate["oracle_correct"] = evaluate_program(candidate["program"], task["visible"] + task["hidden"])
            rows.append({"task_id": task["id"], "reference": task["reference"],
                         "legacy_candidate_count": len(legacy), "direct_candidate_count": len(direct),
                         "macro_candidate_count": len(base), "credit_lineage_candidate_count": len(credit),
                         "internal_mutation_candidate_count": len(local),
                         "candidates": annotate_candidates(candidates)})
        pools[split] = rows
    return pools


def score_arm(pools, banks, arm, arm_id):
    result = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task, pool in zip(banks[split], pools[split]):
            selected = choose_candidate(pool["candidates"], arm)
            selected = selected or {"program": "", "cost": 0.0, "macro_ids": [],
                                    "macro_source": "none", "oracle_correct": False}
            row = {"task_id": task["id"], "reference": task["reference"], "program": selected["program"],
                   "cost": selected["cost"], "candidate_count": len(pool["candidates"]),
                   "legacy_candidate_count": pool["legacy_candidate_count"],
                   "direct_candidate_count": pool["direct_candidate_count"],
                   "macro_candidate_count": pool["macro_candidate_count"],
                   "credit_lineage_candidate_count": pool["credit_lineage_candidate_count"],
                   "internal_mutation_candidate_count": pool["internal_mutation_candidate_count"],
                   "macro_ids": selected.get("macro_ids", []), "macro_source": selected.get("macro_source", "none"),
                   "arm": arm_id, "oracle_correct": selected["oracle_correct"]}
            row["replay_sha256"] = digest({key: row[key] for key in row if key not in ("replay_sha256", "oracle_correct")})
            rows.append(row)
        correct = sum(row["oracle_correct"] for row in rows)
        result[split] = {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}
    return result


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_credit_lineage_v80.py", "run_reserved_graft_lineage_v81.py",
                    "run_rotate_lineage_v82.py", "audit_rotate_lineage_v82.py",
                    "run_cross_family_macro_v75.py", "run_ast_v66.py",
                    "rsi/credit_lineage.py", "rsi/internal_body_mutation.py", "rsi/macro_library.py",
                    "rsi/meta_macro.py", "rsi/self_editing_grammar.py", "rsi/semantic_invention.py",
                    "rsi/stack_program.py", "rsi/expression_synthesis.py", "rsi/evolving_domain.py",
                    "rsi/common.py", "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "visible-only multi-generation lineage with cross-task support credit and frozen held-out replay",
        "source_sha256": hashes})
    banks, metadata = create_cross_family_banks(config)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    if config.get("seed_identity", False):
        base_library = [{"macro_id": "identity_seed", "body": [{"op": "load_ord"}],
                         "uses": 0, "source_tasks": [], "body_instructions": 1,
                         "inline_bytes": 24, "call_bytes": 48}]
    else:
        base_library = mine_macro_library(banks["development"], max_macros=config["max_macros"])
    credit_library, lineage_events = evolve_credit_lineage(
        banks["development"], base_library, generations=config["generations"],
        max_library=config["max_library"], min_support=config["min_support"],
        max_children_per_task=config["max_children_per_task"], max_variants=config["max_variants"],
        reserve_grafts=config.get("reserve_grafts", False),
        reserve_rotate=config.get("reserve_rotate", False))
    write_json(output / "macro_library.json", base_library)
    write_json(output / "credit_lineage_library.json", credit_library)
    write_json(output / "lineage_events.json", lineage_events)
    pools = build_pools(banks, base_library, credit_library, config["max_variants"],
                        reserve_grafts=config.get("reserve_grafts", False),
                        reserve_rotate=config.get("reserve_rotate", False))
    write_json(output / "candidate_pools.json", pools)
    scores = {"legacy": score_arm(pools, banks, "legacy", "legacy"),
              "direct_grammar": score_arm(pools, banks, "direct", "direct_grammar"),
              "mined_macro": score_arm(pools, banks, "macro", "mined_macro"),
              "credit_lineage": score_arm(pools, banks, "credit_lineage", "credit_lineage"),
              "internal_mutation": score_arm(pools, banks, "internal_mutation", "internal_mutation")}
    eligible = ["direct_grammar"]
    for arm in ("mined_macro", "credit_lineage", "internal_mutation"):
        if scores[arm]["admission"]["correct"] >= scores["direct_grammar"]["admission"]["correct"]:
            eligible.append(arm)
    selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm))
    result = {"status": "completed", "scores": scores, "eligible": eligible, "selected": selected,
              "macro_library": base_library, "credit_lineage_library": credit_library,
              "lineage_events": lineage_events, "families": config["families"],
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["support credit and mutation grammar remain researcher-authored",
                              "bounded generations, library, and child budgets",
                              "cross-family relationship and admission gate remain authored",
                              "no neural/world-model self-modification",
                              "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026100101)
    parser.add_argument("--generations", type=int, default=2)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--max-macros", type=int, default=16)
    parser.add_argument("--max-library", type=int, default=24)
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--max-children-per-task", type=int, default=4)
    parser.add_argument("--max-variants", type=int, default=48)
    args = parser.parse_args()
    args.families = {"train": "macro_transition", "development": "macro_transition",
                     "admission": "novel_operator_transition", "final": "novel_operator_transition"}
    args.bank_counts = {"train": args.training_tasks, "development": args.development_tasks,
                        "admission": args.admission_tasks, "final": args.final_tasks}
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
