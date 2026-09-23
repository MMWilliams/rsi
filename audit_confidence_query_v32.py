"""Independent replay audit for the V32 confidence-gated CEGIS run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.common import ROOT, canonical, verify_journal, write_json
from rsi.confidence_query import BayesianConfidence, solve as confidence_solve
from rsi.search import BASE_CONFIG


def audit(root: Path) -> dict:
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    banks = json.loads((root / "protected_banks.json").read_text(encoding="utf-8"))
    macros = json.loads((root / "common_macros.json").read_text(encoding="utf-8"))
    stored = json.loads((root / "results.json").read_text(encoding="utf-8"))
    model_doc = json.loads((root / "model.json").read_text(encoding="utf-8"))
    model = BayesianConfidence.from_dict(model_doc["model"])
    search_config = dict(BASE_CONFIG)
    search_config.update({"budget": config["budget"], "max_atoms": config["max_atoms"]})
    replayed = 0
    final_scores = {}
    for split in ("development", "admission", "final"):
        final_scores[split] = {}
        for name, expected in stored["scores"][split].items():
            if name == "q0":
                continue
            if name == "q2":
                from rsi.active_cegis import counterexample_guided_solve
                rows = []
                for task in banks[split]:
                    public = {"id": task["id"], "visible": task["visible"]}
                    first = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                                        max_atoms=config["max_atoms"], macros=macros,
                                                        synthesize_constants=True, max_queries=config["max_queries"])
                    second = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                                         max_atoms=config["max_atoms"], macros=macros,
                                                         synthesize_constants=True, max_queries=config["max_queries"])
                    if canonical(first) != canonical(second):
                        raise AssertionError(f"q2 replay mismatch: {split}/{task['id']}")
                    rows.append({"correct": published_correct(first["program"], task["visible"] + task["hidden"]),
                                 "queries": first.get("queries", 0)})
            else:
                threshold = float(name.split("_")[-1])
                rows = []
                for task in banks[split]:
                    first = confidence_solve(task, model, threshold, search_config, macros, config["max_queries"])
                    second = confidence_solve(task, model, threshold, search_config, macros, config["max_queries"])
                    if canonical(first) != canonical(second):
                        raise AssertionError(f"confidence replay mismatch: {split}/{name}/{task['id']}")
                    rows.append({"correct": published_correct(first["program"], task["visible"] + task["hidden"]),
                                 "queries": first["queries"]})
            correct = sum(row["correct"] for row in rows)
            mean_queries = sum(row["queries"] for row in rows) / max(1, len(rows))
            if correct != expected["correct"] or abs(mean_queries - expected["mean_queries"]) > 1e-12:
                raise AssertionError(f"score mismatch: {split}/{name}")
            final_scores[split][name] = correct
            replayed += len(rows)
    baseline = stored["scores"]["admission"]["q0"]["correct"]
    candidates = ["q2"] + [f"confidence_{threshold:g}" for threshold in config["thresholds"]]
    eligible = [name for name in candidates if stored["scores"]["admission"][name]["correct"] >= baseline]
    if eligible != stored["eligible"] or stored["selected"] not in eligible + ["q0"]:
        raise AssertionError("selection gate mismatch")
    result = {"status": "passed", "run_id": root.name, "journal_events": verify_journal(root / "events.jsonl"),
              "evaluation_rows_replayed": replayed, "selected": stored["selected"],
              "final_scores": final_scores, "eligible": eligible, "limitations": stored["limitations"]}
    write_json(root / "audit.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/confidence-query-v32-20260917")
    print(json.dumps(audit(ROOT / parser.parse_args().run), indent=2))
