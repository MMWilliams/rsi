"""Declarative architecture search for the V22 self-improver.

The candidate generator is deliberately independent of the solver.  It uses a
factorial design for the discrete architecture factors, then normalizes
irrelevant fields so equivalent programs are not counted as separate ideas.
Promotion is multi-fidelity: cheap screen -> full development -> admission.
"""

from __future__ import annotations

from itertools import product

from .research_frameworks import pareto_front


def candidate_id(architecture: dict) -> str:
    fields = (architecture["engine"], architecture["budget"], architecture["max_atoms"],
              architecture["synthesize_constants"], architecture["progress_weight"],
              architecture["widening"])
    return "automl_" + "_".join(str(value) for value in fields)


def normalize(architecture: dict) -> dict:
    row = dict(architecture)
    if row["engine"] == "cegis":
        # CEGIS uses exact shortest-path ordering; these legacy policy fields
        # are intentionally canonicalized instead of pretending to vary.
        row["progress_weight"] = 1.0
        row["widening"] = 0.5
    else:
        row["synthesize_constants"] = False
    row["id"] = candidate_id(row)
    return row


def factorial_candidates() -> list[dict]:
    """Enumerate the bounded architecture space without hand-picking mutations."""
    rows = []
    for engine, budget, max_atoms, synth, progress, widening in product(
        ("baseline", "partial", "cegis"), (128, 256, 512), (4, 5, 6),
        (False, True), (0.75, 1.0, 1.25), (0.4, 0.5, 0.7)):
        rows.append(normalize({"engine": engine, "budget": budget, "max_atoms": max_atoms,
                               "synthesize_constants": synth, "progress_weight": progress,
                               "widening": widening}))
    unique = {row["id"]: row for row in rows}
    return [unique[key] for key in sorted(unique)]


def promotion_order(records: list[dict], limit: int, force_ids: set[str] | None = None) -> list[dict]:
    """Keep a correctness/cost Pareto set, then fill deterministically."""
    force_ids = force_ids or set()
    front_input = [{"id": row["architecture"]["id"], "correct": row["correct"],
                    "cost": -float(row["architecture"]["budget"] * row["architecture"]["max_atoms"])}
                   for row in records]
    front_ids = {row["id"] for row in pareto_front(front_input, ("correct", "cost"))}
    ranked = sorted(records, key=lambda row: (-row["correct"],
                                               row["architecture"]["budget"] * row["architecture"]["max_atoms"],
                                               row["architecture"]["id"]))
    selected = []
    selected_ids = set()
    for row in records:
        if row["architecture"]["id"] in force_ids and row["architecture"]["id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["architecture"]["id"])
    for row in ranked:
        if len(selected) >= limit:
            break
        if row["architecture"]["id"] in selected_ids:
            continue
        if row["architecture"]["id"] in front_ids or len(selected) < max(1, limit // 2):
            selected.append(row)
            selected_ids.add(row["architecture"]["id"])
    return selected[:limit]


def select_admission(records: list[dict], baseline: dict, development_tolerance: int) -> dict:
    eligible = [row for row in records
                if row["admission"]["correct"] >= baseline["admission"]["correct"]
                and row["development"]["correct"] >= baseline["development"]["correct"] - development_tolerance]
    if not eligible:
        return {"accepted": False, "architecture": baseline["architecture"], "reason": "no_candidate_passed_gate"}
    selected = max(eligible, key=lambda row: (row["admission"]["correct"], row["development"]["correct"],
                                               -row["architecture"]["budget"], row["architecture"]["id"]))
    improved = (selected["admission"]["correct"] > baseline["admission"]["correct"] or
                selected["development"]["correct"] > baseline["development"]["correct"])
    return {"accepted": improved, "architecture": selected["architecture"],
            "reason": "strict_admission_or_development_gain" if improved else "no_strict_gain",
            "development": selected["development"], "admission": selected["admission"],
            "eligible_count": len(eligible)}
