"""V74: mine and reuse executable macros across tasks."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.expression_synthesis import synthesize_ordinal_expressions
from rsi.macro_library import mine_macro_library, synthesize_macro_predicates
from rsi.meta_macro import annotate_candidates, choose_candidate
from rsi.retention_run import file_hash, seal_artifacts
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from rsi.semantic_invention import evaluate_program
from run_ast_v66 import _direct_ast_candidates
from run_induced_signature_v54 import bank_config


def build_pools(banks, library):
    pools = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task in banks[split]:
            legacy_predicates = synthesize_ordinal_expressions(task["visible"], compose=False)
            legacy = [{**candidate, "macro_source": "legacy"}
                      for candidate in _direct_ast_candidates(task, legacy_predicates)]
            direct = [{**candidate, "macro_source": "direct_grammar"}
                      for candidate in _direct_ast_candidates(task,
                          synthesize_self_edit_predicates(task["visible"], SAFE_OPS))]
            mined = [{**candidate, "macro_source": "mined_visible_only"}
                     for candidate in _direct_ast_candidates(task,
                         synthesize_macro_predicates(task["visible"], library))]
            candidates = legacy + direct + mined
            for candidate in candidates:
                candidate["oracle_correct"] = evaluate_program(candidate["program"],
                                                                task["visible"] + task["hidden"])
            rows.append({"task_id": task["id"], "legacy_candidate_count": len(legacy),
                         "direct_candidate_count": len(direct), "macro_candidate_count": len(mined),
                         "candidates": annotate_candidates(candidates)})
        pools[split] = rows
    return pools


def score_arm(pools, banks, arm, arm_id):
    result = {}
    for split in ("development", "admission", "final"):
        rows = []
        for task, pool in zip(banks[split], pools[split]):
            candidate = choose_candidate(pool["candidates"], arm)
            selected = candidate or {"program": "", "cost": 0.0, "macro_ids": [],
                                     "macro_source": "none", "oracle_correct": False}
            row = {"task_id": task["id"], "program": selected["program"], "cost": selected["cost"],
                   "candidate_count": len(pool["candidates"]), "legacy_candidate_count": pool["legacy_candidate_count"],
                   "direct_candidate_count": pool["direct_candidate_count"],
                   "macro_candidate_count": pool["macro_candidate_count"],
                   "macro_ids": selected.get("macro_ids", []), "macro_source": selected.get("macro_source", "none"),
                   "arm": arm_id, "oracle_correct": selected["oracle_correct"]}
            row["replay_sha256"] = digest({key: row[key] for key in row
                                            if key not in ("replay_sha256", "oracle_correct")})
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
    source_names = ["run_macro_invention_v74.py", "run_ast_v66.py", "run_induced_signature_v54.py",
                    "rsi/macro_library.py", "rsi/meta_macro.py", "rsi/self_editing_grammar.py",
                    "rsi/stack_program.py", "rsi/expression_synthesis.py", "rsi/semantic_invention.py",
                    "rsi/evolving_domain.py", "rsi/invented_space.py", "rsi/common.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "visible-only macro mining and held-out macro replay",
        "source_sha256": hashes})
    banks, metadata = create_evolving_banks(bank_config(config))
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    library = mine_macro_library(banks["development"], max_macros=config["max_macros"])
    write_json(output / "macro_library.json", library)
    pools = build_pools(banks, library)
    write_json(output / "candidate_pools.json", pools)
    scores = {"legacy": score_arm(pools, banks, "legacy", "legacy"),
              "direct_grammar": score_arm(pools, banks, "direct", "direct_grammar"),
              "mined_macro": score_arm(pools, banks, "macro", "mined_macro")}
    eligible = ["direct_grammar"]
    if scores["mined_macro"]["admission"]["correct"] >= scores["direct_grammar"]["admission"]["correct"]:
        eligible.append("mined_macro")
    selected = max(eligible, key=lambda arm: (scores[arm]["development"]["correct"], arm))
    result = {"status": "completed", "scores": scores, "eligible": eligible, "selected": selected,
              "macro_library": library, "training_family": config["train_family"],
              "eval_family": config["eval_family"], "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["macro mining starts from researcher-authored typed expression grammar",
                              "visible examples and bounded admission remain supervisory",
                              "synthetic cross-task mechanism family", "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026092001)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--train-family", default="delimiter")
    parser.add_argument("--eval-family", default="macro_transition")
    parser.add_argument("--max-macros", type=int, default=16)
    args = parser.parse_args()
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
