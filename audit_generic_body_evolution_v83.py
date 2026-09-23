"""Independent replay audit for V83 generic typed-body evolution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.generic_body_evolution import build_generic_body_bank, evolve_generic_lineage
from run_cross_family_macro_v75 import create_cross_family_banks
from run_generic_body_evolution_v83 import build_pools, _cache_generic, score_arm, select_architecture


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks = load(root, "protected_banks.json")
    metadata = load(root, "bank_manifest.json")
    base = load(root, "macro_library.json")
    lineage = load(root, "generic_lineage_library.json")
    lineage_events = load(root, "lineage_events.json")
    body_records = load(root, "generic_body_bank.json") if config.get("global_body_bank", False) else None
    pools = load(root, "candidate_pools.json")
    result = load(root, "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    expected_banks, expected_meta = create_cross_family_banks(config)
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_body_records = None
    if config.get("global_body_bank", False):
        expected_body_records = build_generic_body_bank(
            expected_banks["development"], max_nodes=config["max_nodes"],
            max_states_per_size=config["max_states_per_size"],
            hierarchical=config.get("hierarchical", False))
        assert body_records == expected_body_records
    expected_lineage, expected_events = evolve_generic_lineage(
        expected_banks["development"], base, generations=config["generations"],
        max_library=config["max_library"], min_support=config["min_support"],
        max_children_per_task=config["max_children_per_task"],
        max_nodes=config["max_nodes"], max_states_per_size=config["max_states_per_size"],
        hierarchical=config.get("hierarchical", False), body_records=expected_body_records)
    assert lineage == expected_lineage and lineage_events == expected_events
    generic_cache = _cache_generic(expected_banks, base, config["max_nodes"],
                                   config["max_states_per_size"], config.get("hierarchical", False),
                                   expected_body_records)
    expected_pools = build_pools(expected_banks, base, lineage, generic_cache,
                                 config.get("adaptive_encodings"), config.get("specialist_portfolio", False))
    assert pools == expected_pools
    expected_scores = {arm: score_arm(expected_pools, expected_banks, selector, arm)
                       for arm, selector in (
                           ("legacy", "legacy"), ("direct_grammar", "direct"),
                           ("generic_body_evolution", "generic_body_evolution"),
                           ("generic_lineage", "generic_lineage"))}
    if config.get("adaptive_encodings"):
        expected_scores["encoding_adaptive_lineage"] = score_arm(
            expected_pools, expected_banks, "encoding_adaptive_lineage", "encoding_adaptive_lineage")
    if config.get("specialist_portfolio"):
        expected_scores["specialist_portfolio"] = score_arm(
            expected_pools, expected_banks, "specialist_portfolio", "specialist_portfolio")
    assert result["scores"] == expected_scores
    eligible = ["direct_grammar"]
    for arm in ("generic_body_evolution", "generic_lineage", "encoding_adaptive_lineage", "specialist_portfolio"):
        if arm not in expected_scores:
            continue
        if expected_scores[arm]["admission"]["correct"] >= expected_scores["direct_grammar"]["admission"]["correct"]:
            eligible.append(arm)
    selected = select_architecture(expected_scores, eligible,
                                   config.get("selection_policy", "development_first"))
    assert result["eligible"] == eligible and result["selected"] == selected
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": sum(len(expected_pools[s]) for s in ("development", "admission", "final")) * 4,
              "selected": selected,
              "final_scores": {arm: expected_scores[arm]["final"]["correct"] for arm in expected_scores},
              "base_macro_count": len(base), "generic_lineage_count": len(lineage),
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
