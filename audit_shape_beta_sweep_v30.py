"""Independent replay audit for V30 beta sweep."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.generative_prior import choose as generator_choose, program_log_probability
from rsi.grammar_library import instantiate_templates, mine_templates
from rsi.retention_run import file_hash
from rsi.shape_prior import choose as shape_choose, program_shape_bonus, score as shape_score
from rsi.version_space import enumerate_candidates


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path) -> dict:
    config = load(root / "config.json")
    banks = load(root / "protected_banks.json")
    manifest = load(root / "bank_manifest.json")
    macros = load(root / "common_macros.json")
    library = load(root / "shape_library.json")
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
    if library != expected_library or result["shape_library"] != library:
        raise AssertionError("shape library mismatch")
    replayed = 0
    for arm, beta in result["arms"].items():
        for split in ("development", "admission", "final"):
            aggregate = result["scores"][arm][split]
            task_map = {task["id"]: task for task in banks[split]}
            correct = 0
            for stored in aggregate["tasks"]:
                task = task_map[stored["task_id"]]
                learned = beta is not None
                proposals = [] if not learned else instantiate_templates(library, task["visible"], macros,
                    max_proposals=config["max_proposals"], slot_limit=config["slot_limit"])
                candidates = enumerate_candidates({"id": task["id"], "visible": task["visible"]}, macros=macros,
                    proposals=proposals, synthesize_constants=True, max_atoms=config["max_atoms"],
                    limit=config["candidate_limit"], budget=config["candidate_budget"])
                selected = (shape_choose(candidates, library, beta) if learned else
                            generator_choose(candidates, config["generator_max_atoms"])) or {"program": "", "cost": 0.0}
                lp = program_log_probability(selected["program"], config["generator_max_atoms"])
                actual = {"task_id": task["id"], "program": selected["program"], "cost": selected.get("cost", 0.0),
                          "candidate_count": len(candidates), "bayesian_log_probability": lp if math.isfinite(lp) else None,
                          "shape_bonus": program_shape_bonus(selected["program"], library) if learned else 0.0,
                          "selection_score": shape_score(selected, library, beta) if learned else lp}
                actual["replay_sha256"] = digest(actual)
                actual["oracle_correct"] = published_correct(selected["program"], task["visible"] + task["hidden"])
                if actual != stored:
                    raise AssertionError(f"replay mismatch: {arm}/{split}/{task['id']}")
                correct += int(actual["oracle_correct"])
                replayed += 1
            if correct != aggregate["correct"] or len(aggregate["tasks"]) != aggregate["n"]:
                raise AssertionError(f"aggregate mismatch: {arm}/{split}")
    control = result["scores"]["control"]
    eligible = [name for name in result["scores"] if name != "control"
                and result["scores"][name]["admission"]["correct"] >= control["admission"]["correct"]
                and result["scores"][name]["development"]["correct"] >= control["development"]["correct"] - config["development_tolerance"]]
    expected = max(eligible, key=lambda name: (result["scores"][name]["admission"]["correct"],
                                                result["scores"][name]["development"]["correct"],
                                                -float(result["arms"][name]))) if eligible else "control"
    if result["eligible"] != eligible or result["selected"] != expected:
        raise AssertionError("selection gate mismatch")
    sealed = load(root / "artifact_manifest.json")
    for relative, metadata in sealed.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size != metadata["bytes"] or file_hash(path) != metadata["sha256"]:
            raise AssertionError(f"sealed artifact mismatch: {relative}")
    output = {"status": "passed", "run_id": root.name, "journal_events": len(events),
              "evaluation_rows_replayed": replayed, "selected": result["selected"],
              "final_scores": {name: result["scores"][name]["final"]["correct"] for name in result["scores"]},
              "eligible": eligible, "sealed_artifacts_checked": len(sealed), "results_sha256": digest(result),
              "limitations": result["limitations"]}
    write_json(root / "audit.json", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/shape-beta-sweep-v30-20260917")
    args = parser.parse_args()
    print(json.dumps(audit(ROOT / args.run), indent=2))
