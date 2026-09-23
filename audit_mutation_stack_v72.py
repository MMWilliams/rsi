"""Independent replay audit for V72."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.evolving_domain import create_evolving_banks
from rsi.meta_mutation import evolve, initial_population
from rsi.retention_run import file_hash
from run_induced_signature_v54 import bank_config
from run_mutation_stack_v72 import build_pools, score_arm


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks, metadata, pools, result = (load(root, name) for name in
                                      ("protected_banks.json", "bank_manifest.json", "candidate_pools.json", "results.json"))
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    expected_banks, expected_meta = create_evolving_banks(bank_config(config))
    assert digest(banks) == digest(expected_banks) and metadata == expected_meta
    expected_pools = build_pools(banks)
    assert pools == expected_pools
    frozen = {"max_terms": 0, "rank_mode": "shortest"}
    broad = {"max_terms": 8, "rank_mode": "shortest"}
    population = initial_population(config["meta_seed"], size=config["population_size"])
    evolved, trace = evolve(population, pools["development"], generations=config["generations"],
                            elite_count=config["elite_count"], seed=config["meta_seed"])
    expected_scores = {"frozen_legacy": score_arm(pools, banks, frozen, "frozen_legacy"),
                       "broad_mutation": score_arm(pools, banks, broad, "broad_mutation"),
                       "evolved_mutation": score_arm(pools, banks, evolved, "evolved_mutation")}
    assert result["scores"] == expected_scores and result["evolved_architecture"] == evolved
    assert result["evolution_trace"] == trace
    eligible = ["broad_mutation"]
    if expected_scores["evolved_mutation"]["admission"]["correct"] >= expected_scores["broad_mutation"]["admission"]["correct"]:
        eligible.append("evolved_mutation")
    selected = max(eligible, key=lambda arm: (expected_scores[arm]["development"]["correct"], arm))
    assert result["eligible"] == eligible and result["selected"] == selected
    checked = sum(len(pools[split]) for split in ("development", "admission", "final")) * 3
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": checked, "selected": selected,
              "final_scores": {arm: expected_scores[arm]["final"]["correct"] for arm in expected_scores},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
