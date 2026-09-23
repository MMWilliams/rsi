"""Regrade raw generations and reconcile the neural micro-loop archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import digest, verify_journal, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash


def score(samples, tasks):
    rows = []
    for task in tasks:
        flags = [published_correct(text, task["visible"] + task["hidden"]) for text in samples[task["id"]]]
        rows.append({"task_id": task["id"], "n": len(flags), "correct": sum(flags), "pass_at_1": float(flags[0]),
                     "pass_at_8": float(any(flags[:8])), "pass_at_16": float(any(flags[:16]))})
    return {"tasks": rows, "pass_at_k": {str(k): sum(row[f"pass_at_{k}"] for row in rows) / len(rows) for k in (1, 8, 16)}}


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    assert set(manifest) == {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    count = verify_journal(root / "events.jsonl")
    result, banks = read("results.json"), read("protected_banks.json")
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)
    final_tasks = banks["final"]
    expected = {
        "after_bootstrap": score(read("final_samples_after_bootstrap.json"), final_tasks),
        "after_round1": score(read("final_samples_after_round1.json"), final_tasks),
        "after_round2": score(read("final_samples_after_round2.json"), final_tasks),
    }
    assert expected == result["final_scores"]
    train_tasks = {task["id"]: task for task in banks["train"]}
    verified_rows = 0
    for name in ("bootstrap_rows.json", "round1_verified_rows.json", "round2_verified_rows.json"):
        for row in read(name):
            assert row["task_id"] in train_tasks and row["oracle_correct"] is True
            assert correct(row["program"], train_tasks[row["task_id"]]["visible"] + train_tasks[row["task_id"]]["hidden"])
            verified_rows += 1
    assert verified_rows == sum(result["verified_rows"].values())
    report = {"status": "passed", "journal_events": count, "final_samples_regraded": sum(len(row["tasks"]) for row in expected.values()),
              "verified_rows_rechecked": verified_rows, "limits": "Regrades saved generations and verified targets; does not rerun GPU sampling or authenticate a hostile host."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
