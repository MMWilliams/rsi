"""V75: cross-family replay of visible-only executable macros."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import time
from pathlib import Path

from rsi.common import ROOT, Journal, digest, write_json
from rsi.evolving_domain import make_task
from rsi.macro_library import mine_macro_library, synthesize_macro_predicates
from rsi.meta_macro import annotate_candidates, choose_candidate
from rsi.retention_run import file_hash, seal_artifacts
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from rsi.semantic_invention import evaluate_program
from rsi.expression_synthesis import synthesize_ordinal_expressions
from run_ast_v66 import _direct_ast_candidates


def create_cross_family_banks(config):
    rng = random.Random(config["bank_seed"])
    banks, metadata = {}, {}
    for split, count in config["bank_counts"].items():
        family = config["families"][split]
        encoding = config.get("encodings", {}).get(split, "identity")
        rows = [make_task(rng, split, index, family, config["visible_examples"],
                          config["hidden_examples"], encoding)
                for index in range(count)]
        banks[split] = rows
        metadata[split] = {"family": family, "encoding": encoding,
                           "count": len(rows), "sha256": digest(rows)}
    return banks, metadata


def build_pools(banks, library):
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
            mined = [{**candidate, "macro_source": "mined_visible_only"}
                     for candidate in _direct_ast_candidates(
                         task, synthesize_macro_predicates(task["visible"], library))]
            candidates = legacy + direct + mined
            for candidate in candidates:
                candidate["oracle_correct"] = evaluate_program(
                    candidate["program"], task["visible"] + task["hidden"])
            rows.append({"task_id": task["id"], "reference": task["reference"],
                         "legacy_candidate_count": len(legacy),
                         "direct_candidate_count": len(direct),
                         "macro_candidate_count": len(mined),
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
            row = {"task_id": task["id"], "reference": task["reference"],
                   "program": selected["program"], "cost": selected["cost"],
                   "candidate_count": len(pool["candidates"]),
                   "legacy_candidate_count": pool["legacy_candidate_count"],
                   "direct_candidate_count": pool["direct_candidate_count"],
                   "macro_candidate_count": pool["macro_candidate_count"],
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
    source_names = ["run_cross_family_macro_v75.py", "run_ast_v66.py",
                    "rsi/macro_library.py", "rsi/meta_macro.py",
                    "rsi/self_editing_grammar.py", "rsi/semantic_invention.py",
                    "rsi/stack_program.py", "rsi/expression_synthesis.py",
                    "rsi/evolving_domain.py", "rsi/common.py", "rsi/retention_run.py",
                    "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config,
        "protocol": "development-only macro mining followed by cross-family admission/final replay",
        "source_sha256": hashes})
    banks, metadata = create_cross_family_banks(config)
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
              "macro_library": library, "families": config["families"],
              "cross_family_transfer": config["families"]["development"] != config["families"]["final"],
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["macro mining starts from researcher-authored typed expression grammar",
                              "development visible examples remain supervisory",
                              "cross-family relationship is still chosen by the researcher",
                              "synthetic mechanism families and bounded admission remain authored",
                              "not proof of open-ended RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026092101)
    parser.add_argument("--training-tasks", type=int, default=48)
    parser.add_argument("--development-tasks", type=int, default=24)
    parser.add_argument("--admission-tasks", type=int, default=24)
    parser.add_argument("--final-tasks", type=int, default=24)
    parser.add_argument("--visible-examples", type=int, default=40)
    parser.add_argument("--hidden-examples", type=int, default=13)
    parser.add_argument("--max-macros", type=int, default=16)
    args = parser.parse_args()
    args.families = {"train": "macro_transition", "development": "macro_transition",
                     "admission": "novel_operator_transition", "final": "novel_operator_transition"}
    args.bank_counts = {"train": args.training_tasks, "development": args.development_tasks,
                        "admission": args.admission_tasks, "final": args.final_tasks}
    print(json.dumps(run(vars(args), Path(args.output)), indent=2))
