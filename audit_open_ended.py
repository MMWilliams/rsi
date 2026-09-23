"""Independent replay and semantic audit for the open-ended operator lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import canonical, digest, verify_journal, write_json
from rsi.operators import apply, validate_operator
from rsi.retention_run import file_hash
from rsi.search_diagnostic import solve
from rsi.banks import public_task


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    assert set(manifest) == files
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    journal_events = verify_journal(root / "events.jsonl")
    result, banks, config, macros = read("results.json"), read("protected_banks.json"), read("config.json"), read("common_macros.json")
    metadata = read("bank_manifest.json")
    for split, rows in banks.items():
        assert digest(rows) == metadata[split]["sha256"]
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)

    def regrade(record: dict, tasks: list[dict], search_config: dict) -> int:
        task_map = {task["id"]: task for task in tasks}
        assert len(record["tasks"]) == len(tasks)
        rows_checked = 0
        correct_count = 0
        for row in record["tasks"]:
            task = task_map[row["task_id"]]
            expected = published_correct(row["program"], task["visible"] + task["hidden"])
            assert expected == row["oracle_correct"]
            replay = solve(public_task(task), search_config, config["search_budget"], 4, macros, [], pool_mode="baseline")
            assert replay["program"] == row["program"]
            assert replay["cost"] == row["cost"]
            assert replay["replay_sha256"] == row["replay_sha256"]
            rows_checked += 1
            correct_count += int(expected)
        assert correct_count == record["correct"]
        assert record["n"] == len(tasks)
        assert record["accuracy"] == record["correct"] / record["n"]
        return rows_checked

    train_map = {task["id"]: task for task in banks["train"]}
    anchors = read("anchor_rows.json")
    for row in anchors:
        task = train_map[row["task_id"]]
        assert row["oracle_correct"] is True
        assert row["program"] and published_correct(row["program"], task["visible"] + task["hidden"])

    proposal_rows = read("model_operator_proposals.json")
    valid_proposals = [row for row in proposal_rows if row["valid"]]
    for row in valid_proposals:
        operator = row["operator"]
        validate_operator(operator)
        apply(operator, {"absolute_cost": 1.0, "match_cost": 1.0, "constant_cost": 1.0, "case_cost": 1.0,
                         "length_cost": 0.15, "progress_weight": 1.0, "widening": 0.5, "macro_discount": 0.25})
    assert result["model_proposals"] == len(valid_proposals)

    development, admission, final = banks["development"], banks["admission"], banks["final"]
    checked = regrade(result["base_final"], final, {"absolute_cost": 1.0, "match_cost": 1.0, "constant_cost": 1.0, "case_cost": 1.0,
                                                      "length_cost": 0.15, "progress_weight": 1.0, "widening": 0.5, "macro_discount": 0.25})
    regrade(result["parent_development"], development, {"absolute_cost": 1.0, "match_cost": 1.0, "constant_cost": 1.0, "case_cost": 1.0,
                                                         "length_cost": 0.15, "progress_weight": 1.0, "widening": 0.5, "macro_discount": 0.25})
    regrade(result["parent_admission"], admission, {"absolute_cost": 1.0, "match_cost": 1.0, "constant_cost": 1.0, "case_cost": 1.0,
                                                      "length_cost": 0.15, "progress_weight": 1.0, "widening": 0.5, "macro_discount": 0.25})
    for hypothesis in result["hypotheses"]:
        assert hypothesis["config"] not in ({},)
        dev = regrade(hypothesis["development"], development, hypothesis["config"])
        adm = regrade(hypothesis["admission"], admission, hypothesis["config"])
        fin = regrade(hypothesis["final"], final, hypothesis["config"])
        for label, record, parent in (("development", hypothesis["gate"]["development"], result["parent_development"]),
                                      ("admission", hypothesis["gate"]["admission"], result["parent_admission"])):
            child = hypothesis[label]
            parent_ids = {row["task_id"] for row in parent["tasks"] if row["oracle_correct"]}
            child_ids = {row["task_id"] for row in child["tasks"] if row["oracle_correct"]}
            assert record["parent_correct"] == parent["correct"]
            assert record["child_correct"] == child["correct"]
            assert record["gained"] == sorted(child_ids - parent_ids)
            assert record["lost"] == sorted(parent_ids - child_ids)
            assert record["accepted"] == (child["correct"] > parent["correct"] and not (parent_ids - child_ids))
        assert hypothesis["accepted"] == (hypothesis["gate"]["development"]["accepted"] and hypothesis["gate"]["admission"]["accepted"])
        checked += dev + adm + fin

    report = {"status": "passed", "journal_events": journal_events, "valid_model_proposals": len(valid_proposals),
              "hypotheses_replayed": len(result["hypotheses"]), "selected_programs_regraded": checked,
              "accepted_hypotheses": sum(bool(row["accepted"]) for row in result["hypotheses"]),
              "limits": "Replays the deterministic search and regrades stored programs; it does not authenticate the host or rerun neural training."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
