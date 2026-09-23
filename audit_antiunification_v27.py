"""Independent replay audit for V27 anti-unified template induction."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.generative_prior import choose, program_log_probability
from rsi.grammar_library import instantiate_templates, mine_templates
from rsi.retention_run import file_hash
from rsi.version_space import enumerate_candidates


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def replay_row(task, candidates, config):
    selected = choose(candidates, config["generator_max_atoms"]) or {"program": "", "cost": 0.0}
    lp = program_log_probability(selected["program"], config["generator_max_atoms"])
    row = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
           "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None}
    row["replay_sha256"] = digest(row)
    row["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
    return row


def control_candidates(task, common_macros, config):
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=common_macros,
                                synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def learned_candidates(task, common_macros, library, config):
    proposals = instantiate_templates(library, task["visible"], common_macros,
                                      max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
    return enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=common_macros,
                                proposals=proposals, synthesize_constants=True, max_atoms=config["max_atoms"],
                                limit=config["candidate_limit"], budget=config["candidate_budget"])


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    common_macros = load(root / "common_macros.json")
    library = load(root / "antiunified_library.json")
    result = load(root / "results.json")
    if verify_journal(root / "events.jsonl") < 1:
        raise AssertionError("empty journal")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if events[-1]["kind"] != "completed" or events[-1]["payload"]["results_sha256"] != digest(result):
        raise AssertionError("completion event does not bind results")
    for name, rows in banks.items():
        if manifest[name]["sha256"] != digest(rows) or manifest[name]["count"] != len(rows):
            raise AssertionError(f"bank manifest mismatch: {name}")
    expected_library = mine_templates([task["reference"] for task in banks["development"]],
                                      max_library=config["library_size"], max_length=config["library_max_length"],
                                      min_frequency=config["library_min_frequency"])
    if library != expected_library or result["library"] != expected_library:
        raise AssertionError("library mismatch")
    replayed = 0
    for arm, use_library in (("baseline", False), ("learned", True)):
        for split in ("development", "admission", "final"):
            aggregate = result[arm][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                candidates = learned_candidates(task, common_macros, library, config) if use_library else control_candidates(task, common_macros, config)
                actual = replay_row(task, candidates, config)
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {arm}/{split}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {arm}/{split}")
    expected_accept = result["learned"]["admission"]["correct"] >= result["baseline"]["admission"]["correct"] and \
        result["learned"]["development"]["correct"] >= result["baseline"]["development"]["correct"] - config["development_tolerance"]
    if result["accepted"] != expected_accept or result["selected"] != ("learned" if expected_accept else "baseline"):
        raise AssertionError("admission gate mismatch")
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
    parser.add_argument("run", nargs="?", default="runs/antiunification-v27-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
