"""Independent replay audit for the V24 retained-prior experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.meta_ranker import PairwisePrior
from rsi.retention_run import file_hash
from rsi.version_space import enumerate_candidates


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pool(task, macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def score(task, rows, prior=None):
    chosen = (prior.choose(rows) if prior else (rows[0] if rows else None)) or {"program": "", "cost": 0.0}
    row = {"task_id": task["id"], "program": chosen["program"], "cost": chosen.get("cost", 0.0),
           "candidate_count": len(rows), "rank_score": prior.score(chosen) if prior else None}
    row["replay_sha256"] = digest(row)
    row["oracle_correct"] = published_correct(chosen["program"], task["visible"] + task["hidden"])
    return row


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    training = load(root / "training.json")
    prior_json = load(root / "prior.json")
    result = load(root / "results.json")
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    by_id = {task["id"]: task for rows in banks.values() for task in rows}
    fit_rows = []
    for row in training:
        task = by_id[row["task_id"]]
        fresh_pool = pool(task, macros, config)
        active = counterexample_guided_solve({"id": task["id"], "visible": task["visible"]}, task["hidden"],
                                             budget=config["active_budget"], max_atoms=config["max_atoms"],
                                             macros=macros, max_queries=config["active_queries"])
        if fresh_pool != row["candidates"] or active["program"] != row["active_program"]:
            raise AssertionError(f"training replay mismatch: {task['id']}")
        positive = next(candidate for candidate in fresh_pool if candidate["program"] == active["program"])
        if positive != row["positive"]:
            raise AssertionError(f"positive label mismatch: {task['id']}")
        fit_rows.append((positive, fresh_pool))
    prior = PairwisePrior(config["learning_rate"], config["margin"])
    fit = prior.fit(fit_rows, epochs=config["epochs"])
    if fit != prior_json:
        raise AssertionError("prior fit mismatch")
    replayed = 0
    for split in ("admission", "final"):
        for arm in ("baseline", "learned_prior"):
            expected_rows = result[split if split == "admission" else "final"][arm]["tasks"]
            expected_prior = prior if arm == "learned_prior" else None
            correct = 0
            for stored in expected_rows:
                task = by_id[stored["task_id"]]
                actual = score(task, pool(task, macros, config), expected_prior)
                if actual != stored:
                    raise AssertionError(f"score replay mismatch: {split}/{arm}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            aggregate = result[split if split == "admission" else "final"][arm]
            if correct != aggregate["correct"] or len(expected_rows) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {split}/{arm}")
    manifest_files = load(root / "artifact_manifest.json")
    for relative, metadata in manifest_files.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "training_tasks_replayed": len(training), "evaluation_rows_replayed": replayed,
              "baseline_final": result["final"]["baseline"]["correct"],
              "learned_final": result["final"]["learned_prior"]["correct"],
              "sealed_artifacts_checked": len(manifest_files), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/meta-prior-v24-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
