"""Small auditable open-ended operator lab.

The learned adapter proposes bounded search-policy edits. A quality-diversity
beam adds compositions of model hypotheses and baseline edits. Development and
admission are used only for gating; every candidate is then scored on a fresh
final bank so the experiment distinguishes invention from generalization.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import shutil
import sys
import time
from pathlib import Path

from audit_results import published_correct
from rsi.banks import create_banks, public_task, template
from rsi.common import ROOT, Journal, canonical, digest, write_json
from rsi.neural import LocalModel
from rsi.operators import apply, compose_catalog_operator, initial_catalog, validate_operator
from rsi.oracle import correct
from rsi.retention_run import file_hash, seal_artifacts
from rsi.search import BASE_CONFIG, BOUNDS
from rsi.search_diagnostic import solve
from run_neural_micro import symbolic_bootstrap
from rsi.neural import identify_operator


def operator_prompt(table: dict) -> str:
    return (
        "Design one new arithmetic search-config edit using the measured edit statistics below. "
        "Return ONLY JSON with keys name, origin, updates. origin must be model. "
        "Allowed fields: absolute_cost, match_cost, constant_cost, case_cost, length_cost, "
        "progress_weight, widening, macro_discount. An expression is a number, field name, "
        "or [operation,left,right] where operation is add, sub, mul, min, max. `updates` "
        "MUST be an object mapping field names to one scalar or one valid expression tree, "
        "never a list. Change at most four fields. Costs must stay in [0.1,4], length_cost in "
        "[0.02,1.5], widening in "
        "[0.25,1], macro_discount in [0,0.8]. Measured statistics: " + canonical(table)
    )


def normalize_operator(raw: dict) -> tuple[dict, str]:
    """Repair only the model's transport schema, never its numeric meaning."""
    if not isinstance(raw, dict):
        raise ValueError("operator must be an object")
    updates = raw.get("updates")
    repair = "none"
    if isinstance(updates, list):
        converted = {}
        for item in updates:
            if not isinstance(item, dict) or item.get("name") not in BOUNDS:
                raise ValueError("invalid list update")
            field = item["name"]
            if "value" in item:
                value = item["value"]
            elif isinstance(item.get("updates"), dict) and field in item["updates"]:
                value = item["updates"][field]
            else:
                raise ValueError("list update lacks scalar value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError("schema repair accepts scalar numeric values only")
            converted[field] = value
        updates = converted
        repair = "list_updates_to_field_map"
    if not isinstance(updates, dict):
        raise ValueError("updates must be a field map")
    if len(updates) > 4:
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in updates.values()):
            raise ValueError("four-field projection requires scalar updates")
        ranked = sorted(updates, key=lambda field: (abs(float(updates[field]) - BASE_CONFIG[field]), field), reverse=True)
        updates = {field: updates[field] for field in ranked[:4]}
        repair = repair + ("+" if repair != "none" else "") + "top4_effect_projection"
    clipped = {}
    for field, value in updates.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            lo, hi = BOUNDS[field]
            projected = max(lo, min(hi, float(value)))
            clipped[field] = projected
            if projected != value:
                repair = repair + ("+" if repair != "none" else "") + "numeric_box_projection"
        else:
            clipped[field] = value
    updates = clipped
    normalized = {"name": raw.get("name", "model_operator"), "origin": raw.get("origin"), "updates": updates}
    validate_operator(normalized)
    return normalized, repair


def propose_with_adapter(model: LocalModel, table: dict, seed: int, count: int) -> tuple[list[dict], list[dict]]:
    model.activate("bootstrap")
    raw = model.generate_prompts([model.chat(operator_prompt(table))] * count, seed, max_new_tokens=240)
    proposals, journal_rows, seen = [], [], set()
    for text in raw:
        try:
            start, stop = text.index("{"), text.rindex("}") + 1
            parsed = json.loads(text[start:stop])
            normalized, repair = normalize_operator(parsed)
            if normalized["name"] in seen:
                normalized["name"] = "model_" + digest(normalized["updates"])[:12]
                repair = repair + "+deterministic_duplicate_rename"
            operator = identify_operator(normalized)
            seen.add(operator["name"])
            proposals.append(operator)
            journal_rows.append({"raw": text, "valid": True, "repair": repair, "operator": operator})
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            journal_rows.append({"raw": text, "valid": False, "reason": str(exc)})
    return proposals, journal_rows


def score_program(text: str, task: dict) -> bool:
    return published_correct(text, task["visible"] + task["hidden"])


def evaluate(tasks: list[dict], config: dict, macros: list[str], budget: int, proposals_by_id=None) -> dict:
    rows = []
    for task in tasks:
        request = public_task(task)
        proposals = (proposals_by_id or {}).get(task["id"], [])
        first = solve(request, config, budget, 4, macros, proposals, pool_mode="baseline")
        second = solve(request, config, budget, 4, macros, proposals, pool_mode="baseline")
        if canonical(first) != canonical(second):
            raise RuntimeError("non-deterministic search replay")
        rows.append({"task_id": task["id"], "program": first["program"], "oracle_correct": score_program(first["program"], task),
                     "source": first["source"], "cost": first["cost"], "replay_sha256": first["replay_sha256"]})
    return {"tasks": rows, "correct": sum(row["oracle_correct"] for row in rows),
            "n": len(rows), "accuracy": sum(row["oracle_correct"] for row in rows) / max(1, len(rows)),
            "expansions": sum(row["cost"]["expansions"] for row in rows)}


def candidate_summary(parent: dict, child: dict) -> dict:
    parent_ids = {row["task_id"] for row in parent["tasks"] if row["oracle_correct"]}
    child_ids = {row["task_id"] for row in child["tasks"] if row["oracle_correct"]}
    return {"parent_correct": parent["correct"], "child_correct": child["correct"],
            "accuracy_gain": child["accuracy"] - parent["accuracy"],
            "expansion_delta": child["expansions"] - parent["expansions"],
            "gained": sorted(child_ids - parent_ids), "lost": sorted(parent_ids - child_ids),
            "accepted": child["correct"] > parent["correct"] and not (parent_ids - child_ids)}


def bounded_compositions(operator: dict, baselines: list[dict], limit: int) -> list[dict]:
    """Compose hypotheses while respecting the four-field edit interface."""
    result = []
    fields = list(operator["updates"])
    for baseline in baselines:
        for dropped in [None] + fields:
            updates = {key: copy.deepcopy(value) for key, value in operator["updates"].items() if key != dropped}
            for field, tree in baseline["updates"].items():
                updates[field] = copy.deepcopy(tree)
            candidate = {"name": "composed_" + digest(updates)[:16], "origin": "composition", "updates": updates}
            try:
                validate_operator(candidate)
            except ValueError:
                continue
            result.append(candidate)
            if len(result) >= limit:
                return result
    return result


def run(config: dict, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    started = time.perf_counter()
    journal = Journal(output / "events.jsonl")
    source_names = ["run_open_ended.py", "run_neural_micro.py", "rsi/neural.py", "rsi/search_diagnostic.py", "rsi/search.py",
                    "rsi/atom_pool_partial.py", "rsi/banks.py", "rsi/oracle.py", "rsi/common.py", "rsi/operators.py",
                    "audit_results.py", "vendor/trapdoor-loom/dsl.py", "vendor/trapdoor-loom/parse.py", "vendor/trapdoor-loom/trapdoor.py"]
    source_hashes = {name: file_hash(ROOT / name) for name in source_names}
    for name in source_names:
        destination = output / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    write_json(output / "config.json", config)
    journal.append("preregistration", {"config": config, "source_sha256": source_hashes,
                                        "protocol": "adapted-model-proposals + composition beam + development/admission gate"})

    exclusions = set()
    for path in sorted((ROOT / "runs").glob("*/protected_banks.json")):
        banks = json.loads(path.read_text(encoding="utf-8"))
        for rows in banks.values():
            task_rows = rows.get("tasks", []) if isinstance(rows, dict) else rows
            exclusions.update(template(task["reference"]) for task in task_rows)
    bank_config = {"bank_seed": config["bank_seed"],
                   "bank_counts": {"train": config["train_tasks"], "development": config["development_tasks"],
                                   "admission": config["admission_tasks"], "final": config["final_tasks"]},
                   "visible_examples": 3, "hidden_examples": 13, "max_atoms": 4}
    banks, metadata = create_banks(bank_config, exclusions)
    write_json(output / "protected_banks.json", banks)
    write_json(output / "bank_manifest.json", metadata)
    macros = json.loads((ROOT / config["macro_source"]).read_text(encoding="utf-8"))
    write_json(output / "common_macros.json", macros)
    journal.append("bank_frozen", {"sha256": digest(banks), "metadata": metadata})

    model = LocalModel(config, journal)
    task_map = {task["id"]: task for task in banks["train"]}
    anchors = symbolic_bootstrap(banks["train"], macros, config["search_budget"])
    write_json(output / "anchor_rows.json", anchors)
    bootstrap = model.distill(anchors, task_map, "bootstrap", output / "adapters" / "bootstrap", config["neural_seed"], steps=config["bootstrap_steps"])
    model.copy_bootstrap()
    model.activate("bootstrap")
    base_final = evaluate(banks["final"], BASE_CONFIG, macros, config["search_budget"])
    write_json(output / "base_final.json", base_final)

    empty_table = {op["name"]: {"trials": 0, "beneficial": 0, "accepted": 0, "gain_sum": 0.0,
                                 "descendant_trials": 0, "descendant_gain_sum": 0.0} for op in initial_catalog()}
    model_ops, proposal_rows = propose_with_adapter(model, empty_table, config["neural_seed"] + 9000, config["model_proposals"])
    journal.append("model_operator_proposals", {"rows": proposal_rows, "valid": len(model_ops)})
    write_json(output / "model_operator_proposals.json", proposal_rows)

    hypotheses = []
    seen_configs = {canonical(BASE_CONFIG)}
    for operator in model_ops:
        try:
            candidate = apply(operator, BASE_CONFIG)
        except ValueError:
            continue
        key = canonical(candidate)
        if key not in seen_configs:
            seen_configs.add(key)
            hypotheses.append({"id": "model_" + digest(candidate)[:12], "origin": "model", "operator": operator, "config": candidate})
    # Quality-diversity expansion: compose each model edit with a distinct
    # baseline edit so the search is not limited to the model's first beam.
    for hypothesis in list(hypotheses):
        for operator in bounded_compositions(hypothesis["operator"], initial_catalog()[:config["composition_width"]], config["max_hypotheses"]):
            try:
                candidate = apply(operator, BASE_CONFIG)
            except ValueError:
                continue
            key = canonical(candidate)
            if key not in seen_configs:
                seen_configs.add(key)
                hypotheses.append({"id": "composition_" + digest(candidate)[:12], "origin": "composition",
                                   "operator": operator, "config": candidate, "parent": hypothesis["id"]})
            if len(hypotheses) >= config["max_hypotheses"]:
                break
        if len(hypotheses) >= config["max_hypotheses"]:
            break

    parent_dev = evaluate(banks["development"], BASE_CONFIG, macros, config["search_budget"])
    parent_admission = evaluate(banks["admission"], BASE_CONFIG, macros, config["search_budget"])
    results = []
    for hypothesis in hypotheses:
        dev = evaluate(banks["development"], hypothesis["config"], macros, config["search_budget"])
        admission = evaluate(banks["admission"], hypothesis["config"], macros, config["search_budget"])
        gate = {"development": candidate_summary(parent_dev, dev), "admission": candidate_summary(parent_admission, admission)}
        accepted = gate["development"]["accepted"] and gate["admission"]["accepted"]
        final = evaluate(banks["final"], hypothesis["config"], macros, config["search_budget"])
        results.append({**hypothesis, "development": dev, "admission": admission, "gate": gate, "accepted": accepted, "final": final})
        journal.append("operator_evaluated", {"id": hypothesis["id"], "origin": hypothesis["origin"], "accepted": accepted,
                                               "development": gate["development"], "admission": gate["admission"],
                                               "final_correct": final["correct"]})

    result = {"status": "completed", "bootstrap": bootstrap, "anchors": len(anchors), "model_proposals": len(model_ops),
              "hypotheses": results, "parent_development": parent_dev, "parent_admission": parent_admission,
              "base_final": base_final, "ledger": model.ledger, "elapsed_seconds": time.perf_counter() - started,
              "limitations": ["one neural seed", "small task banks", "bounded arithmetic edit language", "fixed DSL", "finite hidden examples", "same-host oracle", "not proof of RSI"]}
    write_json(output / "results.json", result)
    assert all(file_hash(ROOT / name) == value for name, value in source_hashes.items())
    journal.append("completed", {"results_sha256": digest(result)})
    seal_artifacts(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--bank-seed", type=int, default=2026091761)
    parser.add_argument("--train-tasks", type=int, default=24)
    parser.add_argument("--development-tasks", type=int, default=8)
    parser.add_argument("--admission-tasks", type=int, default=8)
    parser.add_argument("--final-tasks", type=int, default=16)
    parser.add_argument("--model-proposals", type=int, default=6)
    parser.add_argument("--max-hypotheses", type=int, default=12)
    parser.add_argument("--composition-width", type=int, default=4)
    parser.add_argument("--bootstrap-steps", type=int, default=8)
    parser.add_argument("--macro-source", default="runs/library-inheritance-20260916-v7/common_macros.json")
    args = parser.parse_args()
    config = {"bank_seed": args.bank_seed, "train_tasks": args.train_tasks, "development_tasks": args.development_tasks,
              "admission_tasks": args.admission_tasks, "final_tasks": args.final_tasks, "model_proposals": args.model_proposals,
              "max_hypotheses": args.max_hypotheses, "composition_width": args.composition_width, "bootstrap_steps": args.bootstrap_steps,
              "macro_source": args.macro_source, "model_id": "Qwen/Qwen3-0.6B", "model_revision": "c1899de289a04d12100db370d81485cdf75e47ca",
              "neural_seed": 17, "generation_batch_size": 8, "max_new_tokens": 96, "lora_steps": 8, "lora_batch_size": 4,
              "lora_learning_rate": 0.0002, "search_budget": 128, "device": "cuda:1"}
    print(json.dumps(run(config, ROOT / args.output), indent=2))
