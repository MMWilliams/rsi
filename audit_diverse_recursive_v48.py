"""Independent replay audit for V48 quality-diversity recursion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.common import digest, verify_journal, write_json
from rsi.grammar_library import instantiate_templates, mine_templates
from rsi.retention_run import file_hash
from run_diverse_recursive_v48 import evaluate, verified_population
from run_recursive_macro_v42 import exclusions


def load(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    root = Path(root)
    config = load(root, "config.json")
    banks, metadata = load(root, "protected_banks.json"), load(root, "bank_manifest.json")
    macros = load(root, "common_macros.json")
    gen0, library1 = load(root, "generation0.json"), load(root, "library1.json")
    population, library2 = load(root, "generation1_population.json"), load(root, "library2.json")
    result = load(root, "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert verify_journal(root / "events.jsonl") >= 1 and events[-1]["kind"] == "completed"
    assert events[-1]["payload"]["results_sha256"] == digest(result)
    for name, rows in banks.items():
        assert metadata[name]["sha256"] == digest(rows) and metadata[name]["count"] == len(rows)
    expected_gen0 = []
    for task in banks["development"]:
        item = counterexample_guided_solve({"id": task["id"], "visible": task["visible"]}, task["hidden"],
            budget=config["training_budget"], max_atoms=config["training_max_atoms"], macros=macros,
            synthesize_constants=True, max_queries=config["training_queries"])
        if published_correct(item["program"], task["visible"] + task["hidden"]):
            expected_gen0.append({"task_id": task["id"], "program": item["program"], "queries": item["queries"],
                                  "replay_sha256": item["replay_sha256"]})
    assert gen0 == expected_gen0
    expected_library1 = mine_templates([row["program"] for row in gen0], max_library=config["library_size"],
        max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    assert library1 == expected_library1
    expected_population = verified_population(banks["development"], macros, library1, config)
    assert population == expected_population
    expected_library2 = mine_templates([row["program"] for row in gen0] +
        [program for row in population for program in row["programs"]], max_library=config["library_size"],
        max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    assert library2 == expected_library2
    expected_scores = {}
    for split in ("development", "admission", "final"):
        expected_scores[split] = {"baseline": evaluate(banks[split], macros, None, config, "baseline"),
                                 "generation1": evaluate(banks[split], macros, library1, config, "generation1"),
                                 "generation2": evaluate(banks[split], macros, library2, config, "generation2")}
    assert result["scores"] == expected_scores
    baseline_admission = result["scores"]["admission"]["baseline"]["correct"]
    eligible = [arm for arm in ("generation1", "generation2") if result["scores"]["admission"][arm]["correct"] >= baseline_admission]
    assert result["eligible"] == eligible
    expected_selected = max(eligible, key=lambda arm: (result["scores"]["admission"][arm]["correct"], result["scores"]["development"][arm]["correct"], arm)) if eligible else "baseline"
    assert result["selected"] == expected_selected
    checked = sum(len(banks[split]) for split in ("development", "admission", "final")) * 3
    sealed = load(root, "artifact_manifest.json")
    for relative, info in sealed.items():
        path = root / relative
        assert path.is_file() and path.stat().st_size == info["bytes"] and file_hash(path) == info["sha256"]
    report = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "generation0_programs": len(gen0), "population_programs": result["population_programs"],
              "evaluation_rows_replayed": checked, "selected": result["selected"],
              "final_scores": {arm: result["scores"]["final"][arm]["correct"] for arm in ("baseline", "generation1", "generation2")},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(Path(parser.parse_args().run)), indent=2))
