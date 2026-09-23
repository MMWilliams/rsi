"""Independent replay audit for V33 relational program priors."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.generative_prior import choose as generator_choose, program_log_probability
from rsi.relational_library import instantiate_relational_templates, mine_relational_templates, program_relational_bonus
from rsi.relational_prior import choose as relational_choose, score as relational_score
from rsi.retention_run import file_hash
from rsi.version_space import enumerate_candidates


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    library = load(root / "relational_library.json")
    result = load(root / "results.json")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if verify_journal(root / "events.jsonl") < 1 or events[-1]["kind"] != "completed":
        raise AssertionError("journal incomplete")
    if events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    expected_library = mine_relational_templates([task["reference"] for task in banks["development"]],
        max_library=config["library_size"], max_length=config["library_max_length"], min_frequency=config["library_min_frequency"])
    if library != expected_library or result["relational_library"] != library:
        raise AssertionError("relational library mismatch")
    replayed = 0
    for arm, learned in (("baseline", False), ("learned", True)):
        for split in ("development", "admission", "final"):
            aggregate = result[arm][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                proposals = [] if not learned else instantiate_relational_templates(library, task["visible"], macros,
                    max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
                candidates = enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                    proposals=proposals, synthesize_constants=True, max_atoms=config["max_atoms"],
                    limit=config["candidate_limit"], budget=config["candidate_budget"])
                selected = relational_choose(candidates, library, config["relational_beta"]) if learned else \
                    generator_choose(candidates, config["generator_max_atoms"])
                selected = selected or {"program": "", "cost": 0.0}
                lp = program_log_probability(selected["program"], config["generator_max_atoms"])
                raw_selection_score = relational_score(selected, library, config["relational_beta"]) if learned else lp
                actual = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
                          "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
                          "relational_bonus": program_relational_bonus(selected["program"], library) if learned else 0.0,
                          "selection_score": raw_selection_score if math.isfinite(raw_selection_score) else None}
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
              "final_scores": {"baseline": result["baseline"]["final"]["correct"], "learned": result["learned"]["final"]["correct"]},
              "templates": len(library["templates"]), "sealed_artifacts_checked": len(sealed),
              "results_sha256": digest(result), "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/relational-prior-v33-20260917")
    print(json.dumps(audit(ROOT / parser.parse_args().run), indent=2))
