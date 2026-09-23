"""Independent audit for V60 extrapolative operator invention."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.retention_run import file_hash
from run_extrapolative_v60 import bank_config, evaluate_online


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks, metadata = load(root, "protected_banks.json"), load(root, "bank_manifest.json")
    result = load(root, "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    expected_banks, expected_meta = create_evolving_banks(bank_config(config))
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_scores = {arm["id"]: {split: evaluate_online(banks[split], config, arm)
                                    for split in ("development", "admission", "final")} for arm in result["arms"]}
    assert expected_scores == result["scores"]
    baseline_admission = result["scores"]["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in result["arms"] if arm["id"] != "baseline" and
                result["scores"][arm["id"]]["admission"]["correct"] >= baseline_admission]
    assert result["eligible"] == eligible
    expected_selected = max(eligible, key=lambda arm_id: (result["scores"][arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    assert result["selected"] == expected_selected
    checked = sum(len(banks[split]) for split in ("development", "admission", "final")) * len(result["arms"])
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": checked, "selected": result["selected"],
              "final_scores": {arm["id"]: result["scores"][arm["id"]]["final"]["correct"] for arm in result["arms"]},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
