"""Independent replay audit for V34 evolutionary ranker."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.banks import template
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.generative_prior import choose as generator_choose, program_log_probability
from rsi.genetic_ranker import choose, vector
from rsi.retention_run import file_hash
from rsi.version_space import enumerate_candidates


def load(path):
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


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    ranker = load(root / "ranker.json")
    result = load(root / "results.json")
    weights = tuple(ranker["weights"])
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if verify_journal(root / "events.jsonl") < 1 or events[-1]["kind"] != "completed":
        raise AssertionError("journal incomplete")
    if events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    replayed = 0
    for arm, mode in (("baseline", "generator"), ("evolved", "evolved")):
        for split in ("development", "admission", "final"):
            aggregate = result[arm][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                candidates = enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                    synthesize_constants=True, max_atoms=config["max_atoms"], limit=config["candidate_limit"],
                    budget=config["candidate_budget"])
                selected = generator_choose(candidates, 4) if mode == "generator" else choose(weights, candidates)
                selected = selected or {"program": "", "cost": 0.0}
                lp = program_log_probability(selected["program"])
                raw_score = sum(left * right for left, right in zip(weights, vector(selected)))
                actual = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
                          "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
                          "selection_score": None if mode == "generator" else (raw_score if math.isfinite(raw_score) else None),
                          "mode": mode}
                actual["replay_sha256"] = digest(actual)
                actual["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {arm}/{split}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {arm}/{split}")
    expected_accept = result["evolved"]["admission"]["correct"] >= result["baseline"]["admission"]["correct"] and \
        result["evolved"]["development"]["correct"] >= result["baseline"]["development"]["correct"] - config["development_tolerance"]
    if result["accepted"] != expected_accept or result["selected"] != ("evolved" if expected_accept else "baseline"):
        raise AssertionError("gate mismatch")
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": replayed, "selected": result["selected"],
              "final_scores": {"baseline": result["baseline"]["final"]["correct"], "evolved": result["evolved"]["final"]["correct"]},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/genetic-ranker-v34-20260917")
    print(json.dumps(audit(ROOT / parser.parse_args().run), indent=2))
