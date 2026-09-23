"""Independent replay audit for the V19 CEGIS archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.banks import public_task
from rsi.cegis_search import solve as cegis_solve
from rsi.common import digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG
from rsi.search_diagnostic import solve as diagnostic_solve
from run_cegis_v19 import selected_score
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
    synthesize_constants = config.get("synthesize_constants", False)
    checked = 0

    baseline = read("baseline_final.json")
    partial = read("partial_final.json")
    cegis = read("cegis_final.json")
    assert baseline == selected_score({row["task_id"]: row["program"] for row in baseline["tasks"]}, banks["final"])
    assert partial == selected_score({row["task_id"]: row["program"] for row in partial["tasks"]}, banks["final"])
    assert cegis == selected_score({row["task_id"]: row["program"] for row in cegis["tasks"]}, banks["final"])
    for task in banks["final"]:
        public = public_task(task)
        task_id = task["id"]
        expected = {
            "baseline": next(row for row in baseline["tasks"] if row["task_id"] == task_id),
            "partial": next(row for row in partial["tasks"] if row["task_id"] == task_id),
            "cegis": next(row for row in cegis["tasks"] if row["task_id"] == task_id),
        }
        replays = {
            "baseline": diagnostic_solve(public, BASE_CONFIG, budget, 4, macros, [], pool_mode="baseline"),
            "partial": diagnostic_solve(public, BASE_CONFIG, budget, 4, macros, [], pool_mode="partial_empty"),
            "cegis": cegis_solve(public, BASE_CONFIG, budget, 4, macros, [], synthesize_constants=synthesize_constants),
        }
        for name, replay in replays.items():
            assert replay["program"] == expected[name]["program"]
            assert published_correct(expected[name]["program"], task["visible"] + task["hidden"]) == expected[name]["oracle_correct"]
            checked += 1

    counts = {phase: read(f"cegis_counts_{phase}.json") for phase in ("pre", "post")}
    for phase in ("pre", "post"):
        raw = read(f"raw_final_{phase}.json")
        repaired = read(f"cegis_samples_{phase}.json")
        ranked = read(f"cegis_ranked_{phase}.json")
        assert result["scores"][f"raw_{phase}"] == pass_metrics(raw, banks["final"])
        assert result["scores"][f"cegis_{phase}"] == pass_metrics(repaired, banks["final"])
        assert result["scores"][f"ranked_{phase}"] == selected_score(ranked, banks["final"])
        for task in banks["final"]:
            task_id = task["id"]
            proposals = raw[task_id]
            outputs = repaired[task_id]
            assert len(proposals) == len(outputs) == config["samples_per_task"]
            for proposal, output in zip(proposals, outputs):
                first = cegis_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal],
                                    synthesize_constants=synthesize_constants)
                second = cegis_solve(public_task(task), BASE_CONFIG, budget, 4, macros, [proposal],
                                     synthesize_constants=synthesize_constants)
                assert first == second
                assert first["program"] == output
                checked += 1
            ranked_replay = cegis_solve(public_task(task), BASE_CONFIG, budget, 4, macros, proposals,
                                        synthesize_constants=synthesize_constants)
            assert ranked_replay["program"] == ranked[task_id]
            assert ranked_replay["transition_count"] == counts[phase][task_id]["transitions"]
            assert ranked_replay["neural_transition_count"] == counts[phase][task_id]["neural_transitions"]
            checked += 1

    verified = read("verified_cegis_rows.json")
    assert len(verified) == result["verified_cegis_rows"]
    for row in verified:
        task = train_map[row["task_id"]]
        assert row["oracle_correct"] is True
        assert published_correct(row["program"], task["visible"] + task["hidden"])

    report = {
        "status": "passed",
        "journal_events": journal_events,
        "selected_and_sampled_programs_regraded": checked,
        "verified_cegis_rows_rechecked": len(verified),
        "limits": "Replays baseline, partial-empty, exact CEGIS and neural-seeded CEGIS on visible inputs and regrades hidden outcomes; it does not rerun neural optimization or authenticate the host.",
    }
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
