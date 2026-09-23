"""Independent replay audit for the V31 tabular query controller."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_results import published_correct
from rsi.banks import template
from rsi.common import ROOT, canonical, digest, verify_journal, write_json
from rsi.rl_query_policy import TabularQueryPolicy, solve as rl_solve
from rsi.search import BASE_CONFIG


def audit(root: Path) -> dict:
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    banks = json.loads((root / "protected_banks.json").read_text(encoding="utf-8"))
    macros = json.loads((root / "common_macros.json").read_text(encoding="utf-8"))
    stored = json.loads((root / "results.json").read_text(encoding="utf-8"))
    policy_doc = json.loads((root / "policy.json").read_text(encoding="utf-8"))
    policy = TabularQueryPolicy(alpha=config["alpha"], gamma=config["gamma"],
                                query_penalty=config["query_penalty"], seed=config["policy_seed"])
    for state, values in policy_doc["q_values"].items():
        policy.q[state] = values
    replayed = 0
    final_scores = {}
    for split in ("development", "admission", "final"):
        final_scores[split] = {}
        for mode in ("q0", "q2", "rl"):
            expected = stored["scores"][split][mode]
            rows = []
            for task in banks[split]:
                if mode == "rl":
                    search_config = dict(BASE_CONFIG)
                    search_config.update({"budget": config["budget"], "max_atoms": config["max_atoms"]})
                    first = rl_solve(task, policy, search_config,
                                     macros, config["max_queries"])
                    second = rl_solve(task, policy, search_config,
                                      macros, config["max_queries"])
                else:
                    from rsi.active_cegis import counterexample_guided_solve
                    public = {"id": task["id"], "visible": task["visible"]}
                    q = 0 if mode == "q0" else config["max_queries"]
                    first = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                                        max_atoms=config["max_atoms"], macros=macros,
                                                        synthesize_constants=True, max_queries=q)
                    second = counterexample_guided_solve(public, task["hidden"], budget=config["budget"],
                                                         max_atoms=config["max_atoms"], macros=macros,
                                                         synthesize_constants=True, max_queries=q)
                if canonical(first) != canonical(second):
                    raise AssertionError(f"replay mismatch: {split}/{mode}/{task['id']}")
                correct = published_correct(first["program"], task["visible"] + task["hidden"])
                rows.append({"task_id": task["id"], "program": first["program"], "oracle_correct": correct,
                             "queries": first.get("queries", 0), "cost": first["cost"]})
            correct = sum(row["oracle_correct"] for row in rows)
            mean_queries = sum(row["queries"] for row in rows) / max(1, len(rows))
            if correct != expected["correct"] or abs(mean_queries - expected["mean_queries"]) > 1e-12:
                raise AssertionError(f"score mismatch: {split}/{mode}")
            final_scores[split][mode] = correct
            replayed += len(rows)
    baseline = stored["scores"]["admission"]["q0"]["correct"]
    eligible = [mode for mode in ("q2", "rl") if stored["scores"]["admission"][mode]["correct"] >= baseline]
    if eligible != stored["eligible"] or stored["selected"] not in (eligible + ["q0"]):
        raise AssertionError("selection gate mismatch")
    result = {"status": "passed", "run_id": root.name, "journal_events": verify_journal(root / "events.jsonl"),
              "evaluation_rows_replayed": replayed, "selected": stored["selected"],
              "final_scores": final_scores, "eligible": eligible,
              "limitations": stored["limitations"]}
    write_json(root / "audit.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", default="runs/rl-query-v31-20260917")
    print(json.dumps(audit(ROOT / parser.parse_args().run), indent=2))
