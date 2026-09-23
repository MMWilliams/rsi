"""Auditable verified replay, coverage decisions, and reversible model promotion."""
from __future__ import annotations

from .common import digest
from .neural import adapter_hash, raw_scores
from .oracle import correct, outcomes
from .evaluation import paired_bootstrap
from dsl import render
from parse import parse, ParseError


def verified_pool(groups, task_map):
    """Stable exact (task, canonical program) dedup; recheck all training certificates."""
    rows, seen = [], set()
    for group in groups:
        for row in group:
            task = task_map[row["task_id"]]
            if row.get("oracle_correct") is not True or not correct(row["program"], task["visible"] + task["hidden"]):
                raise ValueError("Replay contains an unverified solution")
            program = render(parse(row["program"]))
            identity = (row["task_id"], program)
            if identity not in seen:
                seen.add(identity)
                rows.append({"task_id": row["task_id"], "program": program, "oracle_correct": True})
    return rows


def measure(tasks, samples, ks):
    result = raw_scores(tasks, samples, ks)
    for task, row in zip(tasks, result["tasks"]):
        syntax, behavior, parsed = set(), set(), 0
        for text in samples[task["id"]]:
            program = text.strip().splitlines()[0] if text.strip() else ""
            try:
                syntax.add(render(parse(program)))
                parsed += 1
                behavior.add(digest(outcomes(program, task["visible"])))
            except (ParseError, ValueError, TypeError, RecursionError, AttributeError):
                pass
        row.update(distinct_parseable_programs=len(syntax), parseable=parsed,
                   distinct_visible_behaviors=len(behavior))
    result["mean_distinct_parseable_programs"] = sum(r["distinct_parseable_programs"] for r in result["tasks"]) / len(tasks)
    result["mean_distinct_visible_behaviors"] = sum(r["distinct_visible_behaviors"] for r in result["tasks"]) / len(tasks)
    result["parseable_fraction"] = sum(r["parseable"] for r in result["tasks"]) / sum(r["n"] for r in result["tasks"])
    return result


def coverage_decision(parent, candidate, k=64):
    """Conservative observed non-regression gate; no statistical guarantee."""
    left, right = parent["tasks"], candidate["tasks"]
    if not left or [r["id"] for r in left] != [r["id"] for r in right]:
        raise ValueError("Gate requires identical ordered tasks")
    if any(a["n"] != b["n"] or a["n"] < k for a, b in zip(left, right)):
        raise ValueError("Gate requires matched sample counts >= k")
    old, new = {r["id"] for r in left if r["correct"]}, {r["id"] for r in right if r["correct"]}
    delta = candidate["pass_at_k"][str(k)] - parent["pass_at_k"][str(k)]
    delta1 = candidate["pass_at_k"]["1"] - parent["pass_at_k"]["1"]
    reasons = []
    if old - new:
        reasons.append("previously_solved_validation_tasks_lost")
    if delta < -1e-12:
        reasons.append("large_k_validation_regression")
    if delta1 < -1e-12:
        reasons.append("pass1_validation_regression")
    if delta <= 1e-12 and delta1 <= 1e-12:
        reasons.append("no_measured_validation_gain")
    return {"eligible": not reasons, "reasons": reasons or ["coverage_retained_and_measured_gain"],
            "gained_task_ids": sorted(new - old), "lost_task_ids": sorted(old - new),
            "pass_k": k, "pass_k_delta": delta, "pass1_delta": delta1,
            "paired_task_bootstrap": paired_bootstrap([r["pass_at_k"][str(k)] for r in right],
                                                       [r["pass_at_k"][str(k)] for r in left]),
            "interpretation": "Finite sampled validation gate, not proof of true coverage retention or generalization"}


def resolve_update(model, adapter, parent_state, decision, enforce_gate):
    candidate_hash = adapter_hash(model.snapshot(adapter))
    accepted = decision["eligible"] if enforce_gate else True
    if not accepted:
        model.restore(adapter, parent_state)
    selected_hash = adapter_hash(model.snapshot(adapter))
    if selected_hash != (candidate_hash if accepted else adapter_hash(parent_state)):
        raise RuntimeError("Selected model differs from promotion decision")
    return {**decision, "gate_enforced": enforce_gate, "accepted": accepted,
            "selection_reason": decision["reasons"] if enforce_gate else ["preregistered_ungated_control"],
            "parent_sha256": adapter_hash(parent_state), "candidate_sha256": candidate_hash,
            "selected_sha256": selected_hash, "rollback_verified": not accepted}
