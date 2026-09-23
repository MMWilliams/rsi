"""Independent audit for V50 shifted semantic operator domain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.extended_banks import create_extended_banks
from rsi.retention_run import file_hash
from rsi.semantic_invention import evaluate_program
from run_semantic_domain_v50 import evaluate, infer_catalog


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks, metadata = load(root, "protected_banks.json"), load(root, "bank_manifest.json")
    catalog, result = load(root, "inferred_operator_catalog.json"), load(root, "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    expected_banks, expected_meta = create_extended_banks({"bank_seed": config["bank_seed"],
        "bank_counts": {"train": config["training_tasks"], "development": config["development_tasks"],
                         "admission": config["admission_tasks"], "final": config["final_tasks"]},
        "visible_examples": config["visible_examples"], "hidden_examples": config["hidden_examples"]})
    # JSON sealing canonicalizes tuple examples to lists; compare canonical
    # serialized forms rather than Python container types.
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_catalog = infer_catalog(banks["train"], config)
    assert catalog == expected_catalog and result["inferred_operators"] == expected_catalog["operators"]
    learned_ops = tuple(expected_catalog["operators"])
    expected_scores = {arm["id"]: {split: evaluate(banks[split], config, arm, learned_ops)
                                    for split in ("development", "admission", "final")} for arm in result["arms"]}
    assert expected_scores == result["scores"]
    baseline_admission = result["scores"]["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in result["arms"] if arm["id"] != "baseline" and result["scores"][arm["id"]]["admission"]["correct"] >= baseline_admission]
    assert result["eligible"] == eligible
    expected_selected = max(eligible, key=lambda arm_id: (result["scores"][arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    assert result["selected"] == expected_selected
    checked = sum(len(banks[split]) for split in ("development", "admission", "final")) * len(result["arms"])
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "inferred_operators": expected_catalog["operators"], "training_verified": len(expected_catalog["verified"]),
              "evaluation_rows_replayed": checked, "selected": result["selected"],
              "final_scores": {arm["id"]: result["scores"][arm["id"]]["final"]["correct"] for arm in result["arms"]},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
