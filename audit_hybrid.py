"""Independent audit for the neural-symbolic hybrid archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.banks import public_task
from rsi.common import canonical, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.search_diagnostic import solve
from run_hybrid import pass_metrics, selected_score


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

    final_map = {task["id"]: task for task in banks["final"]}
    train_map = {task["id"]: task for task in banks["train"]}
    budget = config["search_budget"]
    base_config = {"absolute_cost": 1.0, "match_cost": 1.0, "constant_cost": 1.0, "case_cost": 1.0,
                   "length_cost": 0.15, "progress_weight": 1.0, "widening": 0.5, "macro_discount": 0.25}

    base = read("base_final.json")
    for row in base["tasks"]:
        task = final_map[row["task_id"]]
        replay = solve(public_task(task), base_config, budget, 4, macros, [], pool_mode="baseline")
        assert replay["program"] == row["program"]
        assert published_correct(row["program"], task["visible"] + task["hidden"]) == row["oracle_correct"]
    assert selected_score({row["task_id"]: row["program"] for row in base["tasks"]}, banks["final"]) == base

    checked = len(base["tasks"])
    for phase in ("pre", "post"):
        raw = read(f"raw_final_{phase}.json")
        hybrid = read(f"hybrid_samples_{phase}.json")
        ranked = read(f"hybrid_ranked_{phase}.json")
        expected_raw = pass_metrics(raw, banks["final"])
        expected_hybrid = pass_metrics(hybrid, banks["final"])
        expected_ranked = selected_score(ranked, banks["final"])
        assert result["scores"]["raw_" + phase] == expected_raw
        assert result["scores"]["hybrid_" + phase] == expected_hybrid
        assert result["scores"]["ranked_" + phase] == expected_ranked
        for task in banks["final"]:
            proposals = raw[task["id"]]
            outputs = hybrid[task["id"]]
            assert len(proposals) == len(outputs) == config["samples_per_task"]
            for proposal, output in zip(proposals, outputs):
                replay = solve(public_task(task), base_config, budget, 4, macros, [proposal], pool_mode="baseline")
                assert replay["program"] == output
                checked += 1
            ranked_replay = solve(public_task(task), base_config, budget, 4, macros, proposals, pool_mode="baseline")
            assert ranked_replay["program"] == ranked[task["id"]]
            checked += 1

    verified = read("verified_hybrid_rows.json")
    assert len(verified) == result["verified_hybrid_rows"]
    for row in verified:
        task = train_map[row["task_id"]]
        assert row["oracle_correct"] is True
        assert published_correct(row["program"], task["visible"] + task["hidden"])
    assert result["direct_model_correct_train"] >= 0
    report = {"status": "passed", "journal_events": journal_events, "selected_programs_regraded": checked,
              "verified_hybrid_rows_rechecked": len(verified), "limits": "Regrades raw and hybrid generations and replays symbolic selection; it does not rerun neural optimization."}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
