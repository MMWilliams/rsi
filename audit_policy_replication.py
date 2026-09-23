"""Independently regrade a frozen policy replication archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.oracle import correct
from rsi.retention_run import file_hash


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    assert set(manifest) == {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    count = verify_journal(root / "events.jsonl")
    result = read("results.json")
    banks = read("replication_banks.json") if (root / "replication_banks.json").exists() else read("protected_banks.json")
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)
    checked = 0
    recomputed = {policy: {metric: 0 for metric in ("selected_correct", "coverage64", "expansions", "generated_nodes", "tasks")} for policy in ("base", "champion")}
    for group in result["scores"]:
        seed_bank = banks.get(str(group["seed"]), banks.get("seed_" + str(group["seed"])))
        tasks = seed_bank["tasks"] if isinstance(seed_bank, dict) else seed_bank
        task_map = {task["id"]: task for task in tasks}
        for policy in ("base", "champion"):
            rows = group[policy + "_rows"]
            recomputed[policy]["tasks"] += len(rows)
            for row in rows:
                task = task_map[row["task_id"]]
                selected = bool(row["selected_program"] and correct(row["selected_program"], task["visible"] + task["hidden"]))
                assert selected == row["selected_correct"]
                if "frontier_programs" in row:
                    coverage = any(correct(program, task["visible"] + task["hidden"]) for program in row["frontier_programs"])
                    assert coverage == row["coverage64"]
                recomputed[policy]["selected_correct"] += int(selected)
                recomputed[policy]["coverage64"] += int(row["coverage64"])
                recomputed[policy]["expansions"] += row["cost"]["expansions"]
                recomputed[policy]["generated_nodes"] += row["cost"]["generated_nodes"]
                checked += 1
    assert recomputed == result["aggregate"]
    report = {"status": "passed", "journal_events": count, "rows_regraded": checked,
              "aggregate_reconciled": True, "limits": "Regrades saved final programs and frontier candidates; does not rerun search or authenticate a hostile host."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
