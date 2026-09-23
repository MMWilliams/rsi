"""V43: gated invention of bounded positional operators from visible data."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from rsi.banks import create_banks, template
from rsi.common import ROOT, Journal, digest, write_json
from rsi.invented_space import _FAMILY_ORDER, _observed_families, enumerate_invented, invented_correct
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


def evaluate(tasks, arm, config, common_macros):
    rows = []
    for task in tasks:
        if arm["mode"] == "baseline":
            families = []
        elif arm["mode"] == "structural":
            families = list(_FAMILY_ORDER)
        else:
            families = None
        candidates = enumerate_invented(
            {"id": task["id"], "visible": task["visible"]},
            config=BASE_CONFIG,
            search_width=arm["search_width"],
            families=families,
            invented_cost=arm["invented_cost"],
            limit=config["candidate_limit"],
            state_beam=config["state_beam"],
            budget=config["candidate_budget"],
            macros=common_macros,
            synthesize_constants=True,
        )
        selected = candidates[0] if candidates else {"program": "", "cost": 0.0, "atoms": []}
        correct = invented_correct(selected["program"], task["visible"] + task["hidden"])
        row = {"task_id": task["id"], "program": selected["program"], "cost": selected["cost"],
               "candidate_count": len(candidates), "invented_atoms": selected.get("invented_atoms", 0),
               "search_width": arm["search_width"], "arm": arm["id"], "oracle_correct": correct}
        row["replay_sha256"] = digest({key: row[key] for key in row if key != "replay_sha256" and key != "oracle_correct"})
        rows.append(row)
    correct = sum(row["oracle_correct"] for row in rows)
    return {"correct": correct, "n": len(rows), "accuracy": correct / max(1, len(rows)), "tasks": rows}


def run(config, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_operator_invention_v43.py", "rsi/invented_space.py", "rsi/atom_pool_partial.py",
                    "rsi/cegis_search.py", "rsi/search.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py",
                    "rsi/retention_run.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py",
                    "vendor/trapdoor-loom/trapdoor.py"]
    hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": hashes,
                                       "protocol": "visible-only bounded positional operator invention with MDL cost sweep"})
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"development": config["development_tasks"], "admission": config["admission_tasks"],
                                   "final": config["final_tasks"]}, "visible_examples": 3, "hidden_examples": 13,
                   "max_atoms": config["reference_max_atoms"]}
    banks, metadata = create_banks(bank_config, exclusions())
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    common_macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", common_macros)
    write_json(output / "invented_operator_families.json", {
        "fixed_structural_families": list(_FAMILY_ORDER),
        "visible_derived_family_rule": "observed non-alphanumeric literal separators only",
    })
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    arms = [{"id": "baseline", "mode": "baseline", "invented_cost": 99.0, "search_width": 2},
            {"id": "baseline_w3", "mode": "baseline", "invented_cost": 99.0, "search_width": 3}]
    for mode in ("structural", "all"):
        for cost in (0.5, 1.0, 1.5):
            arms.append({"id": f"{mode}_c{str(cost).replace('.', '')}_w2", "mode": mode,
                         "invented_cost": cost, "search_width": 2})
    arms.append({"id": "all_c10_w3", "mode": "all", "invented_cost": 1.0, "search_width": 3})
    scores = {}
    for arm in arms:
        scores[arm["id"]] = {split: evaluate(banks[split], arm, config, common_macros)
                              for split in ("development", "admission", "final")}
        journal.append("arm_evaluated", {"arm": arm, "development": scores[arm["id"]]["development"]["correct"],
                                           "admission": scores[arm["id"]]["admission"]["correct"],
                                           "final": scores[arm["id"]]["final"]["correct"]})
    baseline_admission = scores["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in arms if arm["id"] != "baseline" and
                scores[arm["id"]]["admission"]["correct"] >= baseline_admission]
    selected = max(eligible, key=lambda arm_id: (scores[arm_id]["admission"]["correct"],
                                                  scores[arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    result = {"status": "completed", "arms": arms, "scores": scores, "eligible": eligible, "selected": selected,
              "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["operator metalanguage is researcher-bounded", "operator proposals use visible inputs only",
                              "fresh tasks still come from the original DSL", "small synthetic banks", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == expected for name, expected in hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091888)
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
