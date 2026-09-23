from __future__ import annotations

import copy
import random

from .common import digest
from .operators import apply, empty_stats, initial_catalog, select, shuffled_table
from .search import BASE_CONFIG


def evolve(evaluator, banks, config, seed, mode="adaptive", initial_table=None, catalog=None, generations=None, label="evolution", macros=(), initial_config=None, proposals=None):
    rng = random.Random(seed)
    catalog = copy.deepcopy(catalog or initial_catalog())
    table = {op["name"]: copy.deepcopy((initial_table or {}).get(op["name"], empty_stats())) for op in catalog}
    state = dict(initial_config or BASE_CONFIG)
    lineage = []
    snapshots = {0: {"config": dict(state), "table": copy.deepcopy(table)}}
    generations = config["generations"] if generations is None else generations
    decisions = []
    for generation in range(1, generations + 1):
        width = max(1, len(banks["development"]) // generations)
        dev = banks["development"][(generation - 1) * width:generation * width]
        width_guard = max(1, len(banks["admission"]) // generations)
        guard = banks["admission"][(generation - 1) * width_guard:generation * width_guard]
        parent = evaluator.evaluate(dev, state, f"{label}/{seed}/g{generation}/parent", macros=macros, proposals=proposals)
        candidates = []
        attempts = []
        names = []
        for proposal_index in range(config["proposals_per_generation"]):
            selection = {} if config.get("log_selection", False) else None
            operator = select(catalog, table, rng, mode=mode, exclude=names, trace=selection,
                              credit_mode=config.get("credit_mode"))
            names.append(operator["name"])
            stats = table[operator["name"]]
            attempt = {"change_id": f"{label}/{seed}/g{generation}/p{proposal_index}",
                       "operator": copy.deepcopy(operator), "parent_config": dict(state),
                       "parent_config_sha256": digest(state), "stats_before": copy.deepcopy(stats),
                       "parent_evaluation_request_sha256": parent["request_sha256"],
                       "development_task_ids": [task["id"] for task in dev],
                       "hypothesis": "This bounded edit improves solve rate at the fixed search budget"}
            if selection is not None:
                attempt["selection"] = selection
            evaluator.journal.append("search_change_proposed", attempt)
            attempts.append(attempt)
            try:
                candidate = apply(operator, state)
            except ValueError as exc:
                stats["trials"] += 1
                attempt.update(valid=False, accepted=False, reason="invalid_edit", detail=str(exc), stats_after=copy.deepcopy(stats))
                continue
            measured = evaluator.evaluate(dev, candidate, f"{label}/{seed}/g{generation}/p{proposal_index}/{operator['name']}", macros=macros, proposals=proposals)
            gain = measured["accuracy"] - parent["accuracy"]
            stats["trials"] += 1
            stats["beneficial"] = stats.get("beneficial", 0) + int(gain > 0)
            stats["gain_sum"] += gain
            attempt.update(valid=True, candidate_config=candidate, candidate_config_sha256=digest(candidate),
                           development_gain=gain, candidate_evaluation_request_sha256=measured["request_sha256"],
                           parent_correct=parent["correct"], candidate_correct=measured["correct"],
                           n=measured["n"], stats_after_trial=copy.deepcopy(stats))
            candidates.append((gain, operator["name"], candidate, operator, attempt["change_id"]))
        best = max(candidates, key=lambda row: (row[0], row[1])) if candidates else None
        accepted = False
        guard_gain = None
        # Same admission cost for every generation, even if development gain is zero.
        if best:
            guard_parent = evaluator.evaluate(guard, state, f"{label}/{seed}/g{generation}/guard_parent", macros=macros, proposals=proposals)
            guard_child = evaluator.evaluate(guard, best[2], f"{label}/{seed}/g{generation}/guard_candidate", macros=macros, proposals=proposals)
            guard_gain = guard_child["accuracy"] - guard_parent["accuracy"]
            accepted = best[0] > 0 and guard_gain >= 0
            for ancestor in lineage:
                table[ancestor]["descendant_trials"] += 1
                table[ancestor]["descendant_gain_sum"] += guard_gain
            if accepted:
                table[best[1]]["accepted"] += 1
                lineage.append(best[1])
                state = best[2]
        for attempt in attempts:
            if attempt["valid"]:
                is_best = best is not None and attempt["change_id"] == best[4]
                reason = ("not_selected_after_development_comparison" if not is_best else
                          "no_positive_development_gain" if best[0] <= 0 else
                          "admission_regression" if guard_gain < 0 else "development_gain_and_admission_nonregression")
                attempt.update(accepted=bool(is_best and accepted), reason=reason,
                               admission_evaluated=is_best, admission_gain=guard_gain if is_best else None,
                               stats_after=copy.deepcopy(table[attempt["operator"]["name"]]))
                if is_best:
                    attempt.update(admission_parent_request_sha256=guard_parent["request_sha256"],
                                   admission_candidate_request_sha256=guard_child["request_sha256"])
            attempt["selected_config_sha256"] = digest(state)
            evaluator.journal.append("search_change_resolved", attempt)
        decision = {"generation": generation, "operator": best[1] if best else None, "dev_gain": best[0] if best else None,
                    "admission_gain": guard_gain, "accepted": accepted, "config": dict(state), "table_sha256": digest(table),
                    "attempts": attempts}
        decisions.append(decision)
        evaluator.journal.append("generation", {"label": label, "seed": seed, **decision})
        snapshots[generation] = {"config": dict(state), "table": copy.deepcopy(table)}
    return {"seed": seed, "mode": mode, "config": state, "table": table, "snapshots": snapshots, "decisions": decisions}


def inheritance_test(evaluator, banks, config, evolved, macros=()):
    """Table-only transfer. Every cell restarts from BASE_CONFIG and initial catalog."""
    records = []
    cut = len(banks["transfer_development"]) // 2
    transfer_banks = {"development": banks["transfer_development"][:cut], "admission": banks["transfer_development"][cut:]}
    transfer_config = {**config, "generations": config["transfer_steps"], "proposals_per_generation": config.get("transfer_proposals_per_generation", 1)}
    for repetition in range(config["transfer_repeats"]):
        source = evolved[repetition % len(evolved)]
        trial_seed = 10000 + repetition
        snapshots = source["snapshots"]
        tables = {"g0": snapshots[0]["table"], "g3": snapshots[3]["table"], "g6": snapshots[6]["table"],
                  "empty": {}, "scrambled_g6": shuffled_table(snapshots[6]["table"], random.Random(trial_seed + 77))}
        for name, table in tables.items():
            inherited = evolve(evaluator, transfer_banks, transfer_config, trial_seed, initial_table=table,
                               label=f"inheritance/{name}", macros=macros)
            # This final score is never fed back into the inherited table.
            score = evaluator.evaluate(banks["transfer_final"], inherited["config"], f"inheritance/{name}/{trial_seed}/final", macros=macros)
            records.append({"condition": name, "repetition": repetition, "source_seed": source["seed"], "accuracy": score["accuracy"],
                            "correct": score["correct"], "n": score["n"], "accepted_edits": sum(row["accepted"] for row in inherited["decisions"]),
                            "config": inherited["config"], "task_scores": [int(row["oracle_correct"]) for row in score["results"]]})
    return records
