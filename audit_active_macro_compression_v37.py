"""Independent replay audit for V37 active-trajectory macro induction."""

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
    training = load(root / "active_training.json")
    library = load(root / "shape_library.json")
    result = load(root / "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if verify_journal(root / "events.jsonl") < 1 or events[-1]["kind"] != "completed":
        raise AssertionError("journal incomplete")
    if events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    task_map = {task["id"]: task for task in banks["development"]}
    expected_training = []
    for task in banks["development"]:
        public = {"id": task["id"], "visible": task["visible"]}
        first = counterexample_guided_solve(public, task["hidden"], budget=config["training_budget"],
            max_atoms=config["training_max_atoms"], macros=macros, synthesize_constants=True,
            max_queries=config["training_queries"])
        if published_correct(first["program"], task["visible"] + task["hidden"]):
            expected_training.append({"task_id": task["id"], "program": first["program"],
                                      "queries": first["queries"], "replay_sha256": first["replay_sha256"]})
    if training != expected_training:
        raise AssertionError("active training mismatch")
    expected_library = mine_templates([row["program"] for row in training if row["program"]],
        max_library=config["library_size"], max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    if library != expected_library or result["shape_library"] != library:
        raise AssertionError("shape library mismatch")
    replayed = 0
    for arm, learned in (("baseline", False), ("learned", True)):
        for split in ("development", "admission", "final"):
            aggregate = result[arm][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                proposals = [] if not learned else instantiate_templates(library, task["visible"], macros,
                    max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
                candidates = enumerate_compressed({"id": task["id"], "visible": task["visible"]}, macros=macros,
                    compressed_macros=proposals, synthesize_constants=True, search_width=config["search_width"],
                    limit=config["candidate_limit"], budget=config["candidate_budget"])
                selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
                lp = program_log_probability(selected["program"], config["generator_max_atoms"])
                actual = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
                          "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
                          "search_width": config["search_width"], "learned": learned}
                actual["replay_sha256"] = digest(actual)
                actual["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {arm}/{split}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {arm}/{split}")
    expected_accept = result["learned"]["admission"]["correct"] >= result["baseline"]["admission"]["correct"] and \
        result["learned"]["development"]["correct"] >= result["baseline"]["development"]["correct"] - config["development_tolerance"]
    if result["accepted"] != expected_accept or result["selected"] != ("learned" if expected_accept else "baseline"):
        raise AssertionError("gate mismatch")
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": replayed, "selected": result["selected"],
              "verified_training_programs": len(training),
              "final_scores": {"baseline": result["baseline"]["final"]["correct"], "learned": result["learned"]["final"]["correct"]},
              "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/active-macro-v37-20260917")
    print(json.dumps(audit(ROOT / parser.parse_args().run), indent=2))
