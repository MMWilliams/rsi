"""Independent replay audit for V25 generator-derived Bayesian selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.generative_prior import choose, program_log_probability
from rsi.retention_run import file_hash
from rsi.version_space import enumerate_candidates


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pool(task, macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def row(task, candidates, mode, config):
    selected = candidates[0] if mode == "cost" and candidates else choose(candidates, config["generator_max_atoms"])
    selected = selected or {"program": "", "cost": 0.0}
    lp = program_log_probability(selected["program"], config["generator_max_atoms"])
    result = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
              "candidate_count": len(candidates), "bayesian_log_probability": lp if lp != float("-inf") else None}
    result["replay_sha256"] = digest(result)
    result["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
    return result


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    result = load(root / "results.json")
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    replayed = 0
    for mode in ("cost", "bayesian"):
        for split in ("development", "admission", "final"):
            aggregate = result["scores"][mode][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                actual = row(task, pool(task, macros, config), mode, config)
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {mode}/{split}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {mode}/{split}")
    baseline = result["scores"]["cost"]
    bayesian = result["scores"]["bayesian"]
    expected_accept = bayesian["admission"]["correct"] >= baseline["admission"]["correct"] and \
        bayesian["development"]["correct"] >= baseline["development"]["correct"] - config["development_tolerance"]
    if expected_accept != result["accepted"] or result["selected"] != ("bayesian" if expected_accept else "cost"):
        raise AssertionError("admission gate mismatch")
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": replayed, "selected": result["selected"],
              "final_scores": {mode: result["scores"][mode]["final"]["correct"] for mode in ("cost", "bayesian")},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/bayesian-prior-v25b-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
