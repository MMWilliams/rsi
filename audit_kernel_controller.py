"""Independent replay audit for the kernel portfolio controller."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.banks import public_task
from rsi.common import canonical, digest, verify_journal, write_json
from rsi.contextual_policy import select_policy
from rsi.retention_run import file_hash
from run_kernel_controller import POLICIES, run_kernel


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

    checked = 0
    for split, tasks in (("development", banks["development"]), ("final", banks["final"])):
        for policy in POLICIES:
            record = result[split][policy]
            task_map = {task["id"]: task for task in tasks}
            assert record["n"] == len(tasks)
            for row in record["tasks"]:
                task = task_map[row["task_id"]]
                replay = run_kernel(policy, task, macros, config["search_budget"])
                assert replay["program"] == row["program"]
                assert replay["cost"] == row["cost"] and replay["replay_sha256"] == row["replay_sha256"]
                assert published_correct(row["program"], task["visible"] + task["hidden"]) == row["oracle_correct"]
                checked += 1
            assert record["correct"] == sum(row["oracle_correct"] for row in record["tasks"])

    dev_tasks = banks["development"]
    dev_rows = {policy: {row["task_id"]: row["oracle_correct"] for row in result["development"][policy]["tasks"]} for policy in POLICIES}
    final_maps = {policy: {row["task_id"]: row for row in result["final"][policy]["tasks"]} for policy in POLICIES}
    choices = read("choices.json")
    expected_choices = []
    for task in banks["final"]:
        policy = select_policy(dev_tasks, dev_rows, task, list(POLICIES), neighbors=config["neighbors"])
        expected_choices.append({"task_id": task["id"], "policy": policy})
        selected = final_maps[policy][task["id"]]
        assert selected["program"] == next(row["program"] for row in read("controller_final.json")["tasks"] if row["task_id"] == task["id"])
    assert choices == expected_choices
    controller = read("controller_final.json")
    assert controller["correct"] == sum(row["oracle_correct"] for row in controller["tasks"])
    assert controller["n"] == len(banks["final"])
    assert result["controller"] == controller
    report = {"status": "passed", "journal_events": journal_events, "kernel_rows_replayed": checked,
              "controller_choices_reconstructed": len(choices), "limits": "Replays all kernels and reconstructs visible-feature choices; it does not authenticate the host."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
