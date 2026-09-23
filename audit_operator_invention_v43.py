"""Independent audit for V43 visible-only operator invention."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rsi.common import digest, verify_journal, write_json
from rsi.invented_space import enumerate_invented, invented_correct
from rsi.retention_run import file_hash
from rsi.search import BASE_CONFIG


def audit(root: Path) -> dict:
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    files = {path.relative_to(root).as_posix() for path in root.rglob("*")
             if path.is_file() and path.name not in ("artifact_manifest.json", "audit.json")}
    assert set(manifest) == files
    for name, entry in manifest.items():
        assert file_hash(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"]
    journal_events = verify_journal(root / "events.jsonl")
    result, banks, config, macros = read("results.json"), read("protected_banks.json"), read("config.json"), read("common_macros.json")
    metadata = read("bank_manifest.json")
    for split, rows in banks.items():
        assert digest(rows) == metadata[split]["sha256"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)

    def replay_arm(arm, split):
        rows = []
        expected = result["scores"][arm["id"]][split]
        for task in banks[split]:
            if arm["mode"] == "baseline":
                families = []
            elif arm["mode"] == "structural":
                from rsi.invented_space import _FAMILY_ORDER
                families = list(_FAMILY_ORDER)
            else:
                families = None
            candidates = enumerate_invented({"id": task["id"], "visible": task["visible"]}, config=BASE_CONFIG,
                search_width=arm["search_width"], families=families, invented_cost=arm["invented_cost"],
                limit=config["candidate_limit"], state_beam=config["state_beam"], budget=config["candidate_budget"],
                macros=macros, synthesize_constants=True)
            selected = candidates[0] if candidates else {"program": "", "cost": 0.0, "invented_atoms": 0}
            correct = invented_correct(selected["program"], task["visible"] + task["hidden"])
            row = {"task_id": task["id"], "program": selected["program"], "cost": selected["cost"],
                   "candidate_count": len(candidates), "invented_atoms": selected.get("invented_atoms", 0),
                   "search_width": arm["search_width"], "arm": arm["id"], "oracle_correct": correct}
            row["replay_sha256"] = digest({key: row[key] for key in row if key != "replay_sha256" and key != "oracle_correct"})
            rows.append(row)
        assert rows == expected["tasks"]
        assert sum(row["oracle_correct"] for row in rows) == expected["correct"]
        assert expected["n"] == len(rows)
        return len(rows)

    checked = 0
    for arm in result["arms"]:
        for split in ("development", "admission", "final"):
            checked += replay_arm(arm, split)
    baseline_admission = result["scores"]["baseline"]["admission"]["correct"]
    eligible = [arm["id"] for arm in result["arms"] if arm["id"] != "baseline" and
                result["scores"][arm["id"]]["admission"]["correct"] >= baseline_admission]
    assert result["eligible"] == eligible
    expected_selected = max(eligible, key=lambda arm_id: (result["scores"][arm_id]["admission"]["correct"],
                                                            result["scores"][arm_id]["development"]["correct"], arm_id)) if eligible else "baseline"
    assert result["selected"] == expected_selected
    report = {"status": "passed", "run_id": root.name, "journal_events": journal_events,
              "arms_replayed": len(result["arms"]), "evaluation_rows_replayed": checked,
              "selected": result["selected"], "sealed_artifacts_checked": len(manifest),
              "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
