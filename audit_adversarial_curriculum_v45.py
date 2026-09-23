"""Independent replay audit for V45 curriculum selection."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.common import digest, verify_journal, write_json
from rsi.compressed_space import enumerate_compressed
from rsi.generative_prior import choose, program_log_probability
from rsi.grammar_library import instantiate_templates, mine_templates
from rsi.retention_run import file_hash
from run_adversarial_curriculum_v45 import evaluate, visible_diagnostic


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks, manifest = load(root / "protected_banks.json"), load(root / "bank_manifest.json")
    macros, diagnostics = load(root / "common_macros.json"), load(root / "training_visible_diagnostics.json")
    training, policies = load(root / "active_training.json"), load(root / "curriculum_selection.json")
    libraries, result = load(root / "shape_libraries.json"), load(root / "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1
    assert events[-1]["kind"] == "completed" and events[-1]["payload"]["results_sha256"] == digest(result)
    for name, rows in banks.items():
        assert manifest[name]["sha256"] == digest(rows) and manifest[name]["count"] == len(rows)

    expected_diagnostics = [visible_diagnostic(task, config, macros) for task in banks["train"]]
    assert diagnostics == expected_diagnostics
    expected_training = []
    for task in banks["train"]:
        public = {"id": task["id"], "visible": task["visible"]}
        first = counterexample_guided_solve(public, task["hidden"], budget=config["training_budget"],
            max_atoms=config["training_max_atoms"], macros=macros, synthesize_constants=True,
            max_queries=config["training_queries"])
        if published_correct(first["program"], task["visible"] + task["hidden"]):
            expected_training.append({"task_id": task["id"], "program": first["program"],
                                      "queries": first["queries"], "replay_sha256": first["replay_sha256"]})
    assert training == expected_training
    by_id = {row["task_id"]: row for row in training}
    diagnostic_by_id = {row["task_id"]: row for row in diagnostics}
    verified_ids = [row["task_id"] for row in training]
    size = config["curriculum_size"]
    hard_sorted = sorted(verified_ids, key=lambda task_id: (diagnostic_by_id[task_id]["candidate_count"], task_id))
    empty_ids = [task_id for task_id in hard_sorted if diagnostic_by_id[task_id]["candidate_count"] == 0]
    expected_policies = {"uniform_17": verified_ids[:min(17, len(verified_ids))], "uniform_24": verified_ids[:size],
                         "hard_low_24": hard_sorted[:size], "hard_empty": empty_ids,
                         "hard_empty_padded_24": (empty_ids + [task_id for task_id in hard_sorted if task_id not in empty_ids])[:size]}
    assert policies == expected_policies
    expected_libraries = {name: mine_templates([by_id[task_id]["program"] for task_id in ids],
        max_library=config["library_size"], max_length=config["library_max_length"],
        min_frequency=config["library_min_frequency"]) for name, ids in policies.items()}
    assert libraries == expected_libraries
    checked = 0
    expected_scores = {"baseline": {split: evaluate(banks[split], macros, None, config, "baseline")
                                     for split in ("development", "admission", "final")}}
    for name, library in libraries.items():
        expected_scores[name] = {split: evaluate(banks[split], macros, library, config, name)
                                 for split in ("development", "admission", "final")}
    assert expected_scores == result["scores"]
    checked = sum(len(banks[split]) for split in ("development", "admission", "final")) * len(expected_scores)
    baseline_admission = result["scores"]["baseline"]["admission"]["correct"]
    eligible = [name for name in policies if result["scores"][name]["admission"]["correct"] >= baseline_admission]
    assert result["eligible"] == eligible
    expected_selected = max(eligible, key=lambda name: (result["scores"][name]["development"]["correct"], -len(policies[name]), name)) if eligible else "baseline"
    assert result["selected"] == expected_selected
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == metadata["bytes"] and file_hash(path) == metadata["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "verified_training_programs": len(training), "curricula_replayed": len(policies),
              "evaluation_rows_replayed": checked, "selected": result["selected"],
              "final_scores": {name: result["scores"][name]["final"]["correct"] for name in ["baseline", *policies]},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
