"""Independent replay audit for V79."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.lineage_library import evolve_lineage_library
from rsi.macro_library import mine_macro_library
from rsi.retention_run import file_hash
from run_lineage_macro_v79 import build_pools, create_cross_family_banks, score_arm


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks = load(root, "protected_banks.json")
    metadata = load(root, "bank_manifest.json")
    base = load(root, "macro_library.json")
    lineage = load(root, "lineage_library.json")
    events_lineage = load(root, "lineage_events.json")
    pools = load(root, "candidate_pools.json")
    result = load(root, "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    expected_banks, expected_meta = create_cross_family_banks(config)
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_base = mine_macro_library(expected_banks["development"], max_macros=config["max_macros"])
    assert base == expected_base
    expected_lineage, expected_events = evolve_lineage_library(
        expected_banks["development"], expected_base, max_library=config["max_library"],
        max_children_per_task=config["max_children_per_task"], max_variants=config["max_variants"])
    assert lineage == expected_lineage and events_lineage == expected_events
    expected_pools = build_pools(expected_banks, expected_base, expected_lineage, config["max_variants"])
    assert pools == expected_pools
    expected_scores = {arm: score_arm(expected_pools, expected_banks, selector, arm)
                       for arm, selector in (("legacy", "legacy"), ("direct_grammar", "direct"),
                                              ("mined_macro", "macro"), ("lineage_library", "lineage"),
                                              ("internal_mutation", "internal_mutation"))}
    assert result["scores"] == expected_scores
    eligible = ["direct_grammar"]
    for arm in ("mined_macro", "lineage_library", "internal_mutation"):
        if expected_scores[arm]["admission"]["correct"] >= expected_scores["direct_grammar"]["admission"]["correct"]:
            eligible.append(arm)
    selected = max(eligible, key=lambda arm: (expected_scores[arm]["development"]["correct"], arm))
    assert result["eligible"] == eligible and result["selected"] == selected
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": sum(len(expected_pools[s]) for s in ("development", "admission", "final")) * 5,
              "selected": selected, "final_scores": {arm: expected_scores[arm]["final"]["correct"] for arm in expected_scores},
              "base_macro_count": len(base), "lineage_macro_count": len(lineage),
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
