"""V83: generic typed-body evolution without a named operator mutation."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import make_task
from rsi.expression_synthesis import synthesize_ordinal_expressions
from rsi.generic_body_evolution import (
    build_generic_body_bank,
    evolve_generic_lineage,
    synthesize_generic_predicates_from_records,
    synthesize_generic_mutation_predicates,
    synthesize_library_body_predicates,
    synthesize_encoding_adaptive_library_predicates,
)
from rsi.meta_macro import annotate_candidates, choose_candidate
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from run_ast_v66 import _direct_ast_candidates
from run_cross_family_macro_v75 import create_cross_family_banks


def _cache_generic(banks, base_library, max_nodes, max_states_per_size,
                   hierarchical=False, body_records=None):
    cache = {}
    for split in ("development", "admission", "final"):
        for task in banks[split]:
            if body_records is None:
                cache[task["id"]] = synthesize_generic_mutation_predicates(
                    task["visible"], base_library, max_nodes=max_nodes,
                    max_states_per_size=max_states_per_size, hierarchical=hierarchical)
            else:
                cache[task["id"]] = synthesize_generic_predicates_from_records(
                    task["visible"], base_library, body_records,
                    hierarchical=hierarchical)
    return cache


def build_pools(banks, base_library, lineage_library, generic_cache,
                adaptive_encodings=None, specialist_portfolio=False):
    pools = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task in banks[split]:
            legacy = [{**candidate, "macro_source": "legacy"}
                      for candidate in _direct_ast_candidates(
                          task, synthesize_ordinal_expressions(task["visible"], compose=False))]
            direct = [{**candidate, "macro_source": "direct_grammar"}
                      for candidate in _direct_ast_candidates(
                          task, synthesize_self_edit_predicates(task["visible"], SAFE_OPS))]
            generic = [{**candidate, "macro_source": "generic_body_evolution"}
                       for candidate in _direct_ast_candidates(task, generic_cache[task["id"]])]
            lineage_predicates = synthesize_library_body_predicates(
                task["visible"], lineage_library, source="generic_lineage")
            lineage = [{**candidate, "macro_source": "generic_lineage"}
                       for candidate in _direct_ast_candidates(task, lineage_predicates)]
            adaptive_predicates = synthesize_encoding_adaptive_library_predicates(
                task["visible"], lineage_library, adaptive_encodings
            ) if adaptive_encodings else []
            adaptive = [{**candidate, "macro_source": "encoding_adaptive_lineage"}
                        for candidate in _direct_ast_candidates(task, adaptive_predicates)]
            candidates = legacy + direct + generic + lineage + adaptive
            for candidate in candidates:
                candidate["oracle_correct"] = evaluate_program(
                    candidate["program"], task["visible"] + task["hidden"])
            row = {"task_id": task["id"], "reference": task["reference"],
                   "legacy_candidate_count": len(legacy),
                   "direct_candidate_count": len(direct),
                   "generic_candidate_count": len(generic),
                   "lineage_candidate_count": len(lineage),
                   "candidates": annotate_candidates(candidates)}
            if adaptive_encodings:
                row["adaptive_candidate_count"] = len(adaptive)
            rows.append(row)
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
            row = {"task_id": task["id"], "reference": task["reference"],
                   "program": selected["program"], "cost": selected["cost"],
                   "candidate_count": len(pool["candidates"]),
                   "legacy_candidate_count": pool["legacy_candidate_count"],
                   "direct_candidate_count": pool["direct_candidate_count"],
                   "generic_candidate_count": pool["generic_candidate_count"],
                   "lineage_candidate_count": pool["lineage_candidate_count"],
                   "macro_ids": selected.get("macro_ids", []),
                   "macro_source": selected.get("macro_source", "none"),
                   "arm": arm_id, "oracle_correct": selected["oracle_correct"]}
            if "adaptive_candidate_count" in pool:
                row["adaptive_candidate_count"] = pool["adaptive_candidate_count"]
            row["replay_sha256"] = digest({key: row[key] for key in row
                                            if key not in ("replay_sha256", "oracle_correct")})
            rows.append(row)
        correct = sum(row["oracle_correct"] for row in rows)
        result[split] = {"correct": correct, "n": len(rows),
                         "accuracy": correct / max(1, len(rows)), "tasks": rows}
    return result


def select_architecture(scores, eligible, policy="development_first"):
    """Select only after admission eligibility; support validation-first ranking."""
    if policy == "admission_first":
        key = lambda arm: (scores[arm]["admission"]["correct"],
                           scores[arm]["development"]["correct"], arm)
    else:
        key = lambda arm: (scores[arm]["development"]["correct"],
                           scores[arm]["admission"]["correct"], arm)
    return max(eligible, key=key)


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_generic_body_evolution_v83.py", "audit_generic_body_evolution_v83.py",
                    "run_cross_family_macro_v75.py", "run_ast_v66.py",
                    "rsi/generic_body_evolution.py", "rsi/stack_program.py",
                    "rsi/semantic_invention.py", "rsi/expression_synthesis.py",
                    "rsi/self_editing_grammar.py", "rsi/meta_macro.py", "rsi/evolving_domain.py",
                    "rsi/common.py", "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py",
                    "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "generic typed-body evolution with immutable parents, cross-task support credit, and frozen held-out replay",
        "source_sha256": hashes})
    banks, metadata = create_cross_family_banks(config)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    base_library = [{"macro_id": "identity_seed", "body": [{"op": "load_ord"}],
                     "uses": 0, "source_tasks": [], "body_instructions": 1,
                     "inline_bytes": 24, "call_bytes": 48}]
    body_records = None
    if config.get("global_body_bank", False):
        body_records = build_generic_body_bank(
            banks["development"], max_nodes=config["max_nodes"],
            max_states_per_size=config["max_states_per_size"],
            hierarchical=config.get("hierarchical", False))
        write_json(output / "generic_body_bank.json", body_records)
    lineage_library, lineage_events = evolve_generic_lineage(
        banks["development"], base_library, generations=config["generations"],
        max_library=config["max_library"], min_support=config["min_support"],
        max_children_per_task=config["max_children_per_task"],
        max_nodes=config["max_nodes"], max_states_per_size=config["max_states_per_size"],
        hierarchical=config.get("hierarchical", False), body_records=body_records)
    write_json(output / "macro_library.json", base_library)
    write_json(output / "generic_lineage_library.json", lineage_library)
    write_json(output / "lineage_events.json", lineage_events)
    generic_cache = _cache_generic(banks, base_library, config["max_nodes"],
                                   config["max_states_per_size"], config.get("hierarchical", False),
                                   body_records)
    pools = build_pools(banks, base_library, lineage_library, generic_cache,
                        config.get("adaptive_encodings"), config.get("specialist_portfolio", False))
    write_json(output / "candidate_pools.json", pools)
    scores = {"legacy": score_arm(pools, banks, "legacy", "legacy"),
              "direct_grammar": score_arm(pools, banks, "direct", "direct_grammar"),
              "generic_body_evolution": score_arm(pools, banks, "generic_body_evolution", "generic_body_evolution"),
              "generic_lineage": score_arm(pools, banks, "generic_lineage", "generic_lineage")}
    if config.get("adaptive_encodings"):
        scores["encoding_adaptive_lineage"] = score_arm(
            pools, banks, "encoding_adaptive_lineage", "encoding_adaptive_lineage")
    if config.get("specialist_portfolio"):
        scores["specialist_portfolio"] = score_arm(
            pools, banks, "specialist_portfolio", "specialist_portfolio")
    eligible = ["direct_grammar"]
    for arm in ("generic_body_evolution", "generic_lineage", "encoding_adaptive_lineage", "specialist_portfolio"):
        if scores[arm]["admission"]["correct"] >= scores["direct_grammar"]["admission"]["correct"]:
            eligible.append(arm)
    selected = select_architecture(scores, eligible, config.get("selection_policy", "development_first"))
    result = {"status": "completed", "scores": scores, "eligible": eligible,
              "selected": selected, "selection_policy": config.get("selection_policy", "development_first"),
              "macro_library": base_library,
              "generic_lineage_library": lineage_library, "lineage_events": lineage_events,
              "families": config["families"], "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["typed leaves, binary operators, constant bounds, and beam search remain authored",
                              "support threshold, visible alignment, and admission gate remain authored",
                              "cross-family relation and synthetic mechanism bank remain authored",
                              "no neural/world-model self-modification", "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026100801)
    parser.add_argument("--generations", type=int, default=2)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--max-library", type=int, default=24)
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--max-children-per-task", type=int, default=8)
    parser.add_argument("--max-nodes", type=int, default=7)
    parser.add_argument("--max-states-per-size", type=int, default=16)
    parser.add_argument("--hierarchical", action="store_true")
    parser.add_argument("--global-body-bank", action="store_true")
    parser.add_argument("--encoding-adaptive", action="store_true")
    parser.add_argument("--admission-first", action="store_true")
    parser.add_argument("--specialist-portfolio", action="store_true")
    parser.add_argument("--development-encoding", choices=("identity", "xor55", "affine5", "rotate3", "bit_reverse"),
                        default="identity")
    parser.add_argument("--admission-encoding", choices=("identity", "xor55", "affine5", "rotate3", "bit_reverse"),
                        default="identity")
    parser.add_argument("--final-encoding", choices=("identity", "xor55", "affine5", "rotate3", "bit_reverse"),
                        default="identity")
    args = parser.parse_args()
    args.seed_identity = True
    args.families = {"train": "novel_operator_transition", "development": "novel_operator_transition",
                     "admission": "stack_transition", "final": "stack_transition"}
    args.encodings = {"train": args.development_encoding, "development": args.development_encoding,
                      "admission": args.admission_encoding, "final": args.final_encoding}
    args.adaptive_encodings = ["identity", "xor55", "affine5", "rotate3"] if args.encoding_adaptive else None
    args.selection_policy = "admission_first" if args.admission_first else "development_first"
    args.bank_counts = {"train": args.training_tasks, "development": args.development_tasks,
                        "admission": args.admission_tasks, "final": args.final_tasks}
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
