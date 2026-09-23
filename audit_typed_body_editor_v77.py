"""Independent replay audit for V77."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.macro_library import mine_macro_library
from rsi.retention_run import file_hash
from run_typed_body_editor_v77 import build_pools, create_cross_family_banks, score_arm


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks = load(root, "protected_banks.json")
    metadata = load(root, "bank_manifest.json")
    library = load(root, "macro_library.json")
    pools = load(root, "candidate_pools.json")
    result = load(root, "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    expected_banks, expected_meta = create_cross_family_banks(config)
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_library = mine_macro_library(expected_banks["development"], max_macros=config["max_macros"])
    assert library == expected_library
    expected_pools = build_pools(expected_banks, expected_library, config["editor_seed"])
    assert pools == expected_pools
    expected_scores = {arm: score_arm(expected_pools, expected_banks, selector, arm)
                       for arm, selector in (("legacy", "legacy"), ("direct_grammar", "direct"),
                                              ("mined_macro", "macro"), ("body_editor", "body_editor"))}
    assert result["scores"] == expected_scores
    eligible = ["direct_grammar"]
    for arm in ("mined_macro", "body_editor"):
        if expected_scores[arm]["admission"]["correct"] >= expected_scores["direct_grammar"]["admission"]["correct"]:
            eligible.append(arm)
    selected = max(eligible, key=lambda arm: (expected_scores[arm]["development"]["correct"], arm))
    assert result["eligible"] == eligible and result["selected"] == selected
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": sum(len(expected_pools[s]) for s in ("development", "admission", "final")) * 4,
              "selected": selected, "final_scores": {arm: expected_scores[arm]["final"]["correct"] for arm in expected_scores},
              "macro_count": len(library), "sealed_artifacts_checked": len(sealed),
              "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
