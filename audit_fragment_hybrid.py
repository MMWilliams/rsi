"""Independent replay audit for the neural fragment-macro hybrid archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.banks import public_task
from rsi.common import digest, verify_journal, write_json
from rsi.neural_macro_search import fragment_programs, solve as fragment_solve
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve as base_solve
from run_fragment_hybrid import selected_score
from run_neural_micro import pass_metrics


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    files = {path.relative_to(root).as_posix() for path in root.rglob("*")
             if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    assert set(manifest) == files
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"]
        assert (root / name).stat().st_size == entry["bytes"]

    journal_events = verify_journal(root / "events.jsonl")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    result = read("results.json")
    banks = read("protected_banks.json")
    config = read("config.json")
    macros = read("common_macros.json")
    metadata = read("bank_manifest.json")
    for split, rows in banks.items():
        assert digest(rows) == metadata[split]["sha256"]
    assert events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)

    final_map = {task["id"]: task for task in banks["final"]}
    train_map = {task["id"]: task for task in banks["train"]}
    budget = config["search_budget"]
    base = read("base_final.json")
    base_rows = {row["task_id"]: row["program"] for row in base["tasks"]}
    expected_base = selected_score(base_rows, banks["final"])
    assert base == expected_base
    checked = 0
    for row in base["tasks"]:
        task = final_map[row["task_id"]]
        replay = base_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [], pool_mode="baseline")
        assert replay["program"] == row["program"]
        assert published_correct(row["program"], task["visible"] + task["hidden"]) == row["oracle_correct"]
        checked += 1

    counts = {"pre": read("fragment_counts_pre.json"), "post": read("fragment_counts_post.json")}
    for phase in ("pre", "post"):
        raw = read(f"raw_final_{phase}.json")
        fragments = read(f"fragment_samples_{phase}.json")
        ranked = read(f"fragment_ranked_{phase}.json")
        expected_raw = pass_metrics(raw, banks["final"])
        expected_fragments = pass_metrics(fragments, banks["final"])
        expected_ranked = selected_score(ranked, banks["final"])
        assert result["scores"][f"raw_{phase}"] == expected_raw
        assert result["scores"][f"fragment_{phase}"] == expected_fragments
        assert result["scores"][f"ranked_{phase}"] == expected_ranked

        for task in banks["final"]:
            task_id = task["id"]
            proposals = raw[task_id]
            outputs = fragments[task_id]
            assert len(proposals) == len(outputs) == config["samples_per_task"]
            for proposal, output in zip(proposals, outputs):
                first = fragment_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal])
                second = fragment_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal])
                assert first == second
                assert first["program"] == output
                assert first["neural_fragment_count"] == len(fragment_programs([proposal], task["visible"], 4))
                checked += 1
            ranked_replay = fragment_solve(public_task(task), BASE_CONFIG, budget, 4, macros, proposals)
            assert ranked_replay["program"] == ranked[task_id]
            assert ranked_replay["neural_fragment_count"] == counts[phase][task_id]
            checked += 1

    verified = read("verified_fragment_rows.json")
    assert len(verified) == result["verified_fragment_rows"]
    for row in verified:
        task = train_map[row["task_id"]]
        assert row["oracle_correct"] is True
        assert published_correct(row["program"], task["visible"] + task["hidden"])

    report = {
        "status": "passed",
        "journal_events": journal_events,
        "selected_and_sampled_programs_regraded": checked,
        "verified_fragment_rows_rechecked": len(verified),
        "limits": "Regrades symbolic and fragment selections and reconstructs visible-only fragment counts; it does not rerun neural optimization or authenticate the host.",
    }
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
