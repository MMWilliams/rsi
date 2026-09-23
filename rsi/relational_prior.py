"""Generator likelihood plus relational anti-unification support."""

from __future__ import annotations

import math

from .generative_prior import program_log_probability
from .relational_library import program_relational_bonus


def score(candidate: dict, library: dict, beta: float = 1.0) -> float:
    base = program_log_probability(candidate["program"])
    if not math.isfinite(base):
        return -math.inf
    return base + beta * program_relational_bonus(candidate["program"], library)


def choose(candidates: list[dict], library: dict, beta: float = 1.0) -> dict | None:
    if not candidates:
        return None
    return max(candidates, key=lambda row: (score(row, library, beta),
                                             program_log_probability(row["program"]),
                                             -float(row.get("cost", 0.0)), row["program"]))
