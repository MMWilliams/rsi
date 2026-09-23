"""Independent replay audit for V44 resource-allocation policies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.retention_run import file_hash
from run_adaptive_width_v44 import options_for, score, use_policy


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    files = {path.relative_to(root).as_posix() for path in root.rglob("*")
             if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    assert set(manifest) == files
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    journal_events = verify_journal(root / "events.jsonl")
    result, banks, config, macros = read("results.json"), read("protected_banks.json"), read("config.json"), read("common_macros.json")
    metadata = read("bank_manifest.json")
    for split, rows in banks.items():
        assert digest(rows) == metadata[split]["sha256"]
    stored_options = read("visible_option_tables.json")
    options = {split: {task["id"]: options_for(task, config, macros) for task in banks[split]}
               for split in ("development", "admission", "final")}
    assert options == stored_options
    checked = 0
    for policy in result["policies"]:
        for split in ("development", "admission", "final"):
            replayed = score(options[split], banks[split], policy, policy)
            assert replayed == result["scores"][policy][split]
            checked += len(banks[split])
    baseline_admission = result["scores"]["width2"]["admission"]["correct"]
    eligible = [policy for policy in result["policies"] if policy != "width2" and
                result["scores"][policy]["admission"]["correct"] >= baseline_admission]
    assert result["eligible"] == eligible
    expected_selected = max(eligible, key=lambda policy: (result["scores"][policy]["development"]["correct"],
                                                             -result["scores"][policy]["development"]["mean_width"], policy)) if eligible else "width2"
    assert result["selected"] == expected_selected
    report = {"status": "passed", "run_id": root.name, "journal_events": journal_events,
              "policies_replayed": len(result["policies"]), "evaluation_rows_replayed": checked,
              "selected": result["selected"], "sealed_artifacts_checked": len(manifest),
              "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
