"""Independent replay audit for V26 library induction."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.generative_prior import choose, program_log_probability
from rsi.library_learning import mine_library
from rsi.retention_run import file_hash
from rsi.version_space import enumerate_candidates


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def pool(task, macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def replay_row(task, candidates, arm, config):
    selected = candidates[0] if arm.endswith("cost") and candidates else choose(candidates, config["generator_max_atoms"])
    selected = selected or {"program": "", "cost": 0.0}
    lp = program_log_probability(selected["program"], config["generator_max_atoms"])
    result = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
              "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None}
    result["replay_sha256"] = digest(result)
    result["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
    return result


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    common_macros = load(root / "common_macros.json")
    stored_library = load(root / "learned_library.json")
    result = load(root / "results.json")
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    expected_library = mine_library([task["reference"] for task in banks["development"]],
                                    max_library=config["library_size"], max_length=config["library_max_length"],
                                    min_frequency=config["library_min_frequency"])
    if expected_library != stored_library or digest(expected_library) != digest(result["library"]):
        raise AssertionError("library replay mismatch")
    arm_macros = {"baseline_cost": [], "generator_prior": [],
                  "library_cost": stored_library["macros"], "library_bayesian": stored_library["macros"]}
    replayed = 0
    for arm, macros in arm_macros.items():
        for split in ("development", "admission", "final"):
            aggregate = result["scores"][arm][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                actual = replay_row(task, pool(task, [*common_macros, *macros], config), arm, config)
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {arm}/{split}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {arm}/{split}")
    base = result["scores"]["generator_prior"]
    candidate = result["scores"]["library_bayesian"]
    expected_accept = candidate["admission"]["correct"] >= base["admission"]["correct"] and \
        candidate["development"]["correct"] >= base["development"]["correct"] - config["development_tolerance"]
    if result["accepted"] != expected_accept or result["selected"] != ("library_bayesian" if expected_accept else "generator_prior"):
        raise AssertionError("admission gate mismatch")
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": replayed, "selected": result["selected"],
              "final_scores": {arm: result["scores"][arm]["final"]["correct"] for arm in arm_macros},
              "library_macros": len(stored_library["macros"]), "sealed_artifacts_checked": len(sealed),
              "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/library-learning-v26-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
