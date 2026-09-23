"""Independent replay audit for V42 recursive macro learning."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.compressed_space import enumerate_compressed
from rsi.generative_prior import choose, program_log_probability
from rsi.grammar_library import instantiate_templates, mine_templates
from rsi.retention_run import file_hash


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    gen0 = load(root / "generation0.json")
    gen1 = load(root / "generation1.json")
    library1 = load(root / "library1.json")
    library2 = load(root / "library2.json")
    result = load(root / "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if verify_journal(root / "events.jsonl") < 1 or events[-1]["kind"] != "completed":
        raise AssertionError("journal incomplete")
    if events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    expected_gen0 = []
    for task in banks["development"]:
        public = {"id": task["id"], "visible": task["visible"]}
        item = counterexample_guided_solve(public, task["hidden"], budget=config["training_budget"],
            max_atoms=config["training_max_atoms"], macros=macros, synthesize_constants=True,
            max_queries=config["training_queries"])
        if published_correct(item["program"], task["visible"] + task["hidden"]):
            expected_gen0.append({"task_id": task["id"], "program": item["program"], "queries": item["queries"],
                                  "replay_sha256": item["replay_sha256"]})
    if gen0 != expected_gen0:
        raise AssertionError("generation0 mismatch")
    expected_library1 = mine_templates([row["program"] for row in gen0], max_library=config["library_size"],
        max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    if library1 != expected_library1:
        raise AssertionError("library1 mismatch")
    task_map = {task["id"]: task for task in banks["development"]}
    expected_stage1 = []
    for task in banks["development"]:
        proposals = instantiate_templates(library1, task["visible"], macros,
            max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
        candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
            compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
            limit=config["candidate_limit"], budget=config["candidate_budget"])
        selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
        if published_correct(selected["program"], task["visible"] + task["hidden"]):
            expected_stage1.append({"task_id": task["id"], "program": selected["program"],
                                    "replay_sha256": digest({"task_id": task["id"], "program": selected["program"],
                                                               "cost": selected.get("cost", 0.0),
                                                               "candidate_count": len(candidates),
                                                               "bayesian_log_probability": program_log_probability(selected["program"], config["generator_max_atoms"]) if math.isfinite(program_log_probability(selected["program"], config["generator_max_atoms"])) else None,
                                                               "search_width": config["search_width"], "arm": "generation1"})})
    if gen1 != expected_stage1:
        raise AssertionError("generation1 mismatch")
    expected_library2 = mine_templates([row["program"] for row in gen0 + gen1], max_library=config["library_size"],
        max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    if library2 != expected_library2:
        raise AssertionError("library2 mismatch")
    replayed = 0
    for split in ("development", "admission", "final"):
        task_map = {task["id"]: task for task in banks[split]}
        for arm, library in (("baseline", None), ("generation1", library1), ("generation2", library2)):
            aggregate = result["scores"][split][arm]
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                proposals = [] if library is None else instantiate_templates(library, task["visible"], macros,
                    max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
                candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
                    compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
                    limit=config["candidate_limit"], budget=config["candidate_budget"])
                selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
                lp = program_log_probability(selected["program"], config["generator_max_atoms"])
                actual = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
                          "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
                          "search_width": config["search_width"], "arm": arm}
                actual["replay_sha256"] = digest(actual)
                actual["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {split}/{arm}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {split}/{arm}")
    baseline = result["scores"]["admission"]["baseline"]["correct"]
    expected_eligible = [arm for arm in ("generation1", "generation2")
                         if result["scores"]["admission"][arm]["correct"] >= baseline]
    if expected_eligible != result["eligible"]:
        raise AssertionError("eligibility mismatch")
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": replayed, "selected": result["selected"],
              "generation0_programs": len(gen0), "generation1_verified_programs": len(gen1),
              "final_scores": {arm: result["scores"]["final"][arm]["correct"] for arm in ("baseline", "generation1", "generation2")},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/recursive-macro-v42-20260917")
    print(json.dumps(audit(ROOT / parser.parse_args().run), indent=2))
