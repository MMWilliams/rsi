"""Independent replay audit for V74."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.macro_library import mine_macro_library
from rsi.retention_run import file_hash
from run_induced_signature_v54 import bank_config
from run_macro_invention_v74 import build_pools, score_arm


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

    expected_banks, expected_meta = create_evolving_banks(bank_config(config))
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_library = mine_macro_library(expected_banks["development"], max_macros=config["max_macros"])
    assert library == expected_library
    expected_pools = build_pools(expected_banks, expected_library)
    assert pools == expected_pools
    expected_scores = {
        "legacy": score_arm(expected_pools, expected_banks, "legacy", "legacy"),
        "direct_grammar": score_arm(expected_pools, expected_banks, "direct", "direct_grammar"),
        "mined_macro": score_arm(expected_pools, expected_banks, "macro", "mined_macro"),
    }
    assert result["scores"] == expected_scores
    eligible = ["direct_grammar"]
    if expected_scores["mined_macro"]["admission"]["correct"] >= expected_scores["direct_grammar"]["admission"]["correct"]:
        eligible.append("mined_macro")
    selected = max(eligible, key=lambda arm: (expected_scores[arm]["development"]["correct"], arm))
    assert result["eligible"] == eligible and result["selected"] == selected

    checked = sum(len(expected_pools[split]) for split in ("development", "admission", "final")) * 3
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": checked, "selected": selected,
              "final_scores": {arm: expected_scores[arm]["final"]["correct"] for arm in expected_scores},
              "macro_count": len(library), "sealed_artifacts_checked": len(sealed),
              "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
