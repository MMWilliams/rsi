"""Regrade and reconcile the replay-and-gate neural archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import digest, verify_journal, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash


def score(samples: dict[str, list[str]], tasks: list[dict]) -> dict:
    rows = []
    for task in tasks:
        flags = [published_correct(text, task["visible"] + task["hidden"]) for text in samples[task["id"]]]
        rows.append({"task_id": task["id"], "n": len(flags), "correct": sum(flags),
                     "pass_at_1": float(flags[0]) if flags else 0.0,
                     "pass_at_8": float(any(flags[:8])), "pass_at_16": float(any(flags[:16]))})
    return {"tasks": rows, "pass_at_k": {str(k): sum(row[f"pass_at_{k}"] for row in rows) / len(rows) for k in (1, 8, 16)}}


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    assert set(manifest) == files
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    journal_count = verify_journal(root / "events.jsonl")
    result, banks = read("results.json"), read("protected_banks.json")
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)

    final_tasks, validation_tasks = banks["final"], banks["validation"]
    unadapted = score(read("final_samples_unadapted.json"), final_tasks)
    final_scores = {
        "round1": score(read("final_samples_round1.json"), final_tasks),
        "round2": score(read("final_samples_round2.json"), final_tasks),
    }
    assert unadapted == result["unadapted_final"]
    for round_name, metrics in final_scores.items():
        assert metrics == result["states"][round_name]["final_score"]

    validation_scores = {}
    for round_index in (1, 2):
        parent = score(read(f"validation_parent_round{round_index}.json"), validation_tasks)
        candidate = score(read(f"validation_candidate_round{round_index}.json"), validation_tasks)
        state = result["states"][f"round{round_index}"]
        assert parent == state["parent_score"] and candidate == state["candidate_score"]
        assert state["p1_gain"] == candidate["pass_at_k"]["1"] - parent["pass_at_k"]["1"]
        assert state["p16_gain"] == candidate["pass_at_k"]["16"] - parent["pass_at_k"]["16"]
        expected_accept = state["p1_gain"] >= 0 and state["p16_gain"] >= 0 and (state["p1_gain"] > 0 or state["p16_gain"] > 0)
        assert state["accepted"] == expected_accept
        validation_scores[f"round{round_index}"] = {"parent": parent, "candidate": candidate}

    train_tasks = {task["id"]: task for task in banks["train"]}
    verified_rows = 0
    for name in ("anchor_rows.json", "verified_rows_round1.json", "verified_rows_round2.json"):
        for row in read(name):
            task = train_tasks[row["task_id"]]
            assert row["oracle_correct"] is True
            assert correct(row["program"], task["visible"] + task["hidden"])
            verified_rows += 1
    assert verified_rows == len(read("anchor_rows.json")) + sum(result["states"][f"round{i}"]["verified_rows"] for i in (1, 2))
    assert all(not result["states"][f"round{i}"]["accepted"] for i in (1, 2))
    report = {"status": "passed", "journal_events": journal_count,
              "final_sample_sets_regraded": 3 * len(final_tasks),
              "validation_sample_sets_regraded": 4 * len(validation_tasks),
              "verified_rows_rechecked": verified_rows,
              "rejected_updates": 2,
              "limits": "Regrades stored generations and verified targets; rollback integrity is checked by the run's tensor-hash assertion."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
