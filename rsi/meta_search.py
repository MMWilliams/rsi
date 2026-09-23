"""Visible-only portfolio selection for verified program frontiers.

The selectors operate before hidden grading. They combine independently
generated candidate frontiers using cost, syntactic diversity and novelty
descriptors, providing an executable MAP-Elites-style search portfolio.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from typing import Iterable, Mapping


def _descriptor(candidate: Mapping[str, object]) -> tuple:
    program = str(candidate["program"])
    return (
        str(candidate.get("source", "unknown")),
        program.count("Concat"),
        program.count("SubStr"),
        program.count("Case"),
        program.count("ConstStr"),
        program.count("CPos") + program.count("MatchPos"),
        min(8, len(program) // 12),
    )


def cost_frontier(candidates: Iterable[Mapping[str, object]], limit: int = 64) -> list[dict]:
    """Return the cheapest canonical candidates, deduplicated by program."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    unique = {}
    for candidate in candidates:
        program = str(candidate["program"])
        old = unique.get(program)
        if old is None or float(candidate["cost"]) < float(old["cost"]):
            unique[program] = dict(candidate)
    return sorted(unique.values(), key=lambda row: (float(row["cost"]), len(row["program"]), row["program"]))[:limit]


def map_elites_frontier(candidates: Iterable[Mapping[str, object]], limit: int = 64) -> list[dict]:
    """Keep the cheapest elite in each visible-only syntax niche."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    niches: OrderedDict[tuple, dict] = OrderedDict()
    for candidate in candidates:
        row = dict(candidate)
        key = _descriptor(row)
        old = niches.get(key)
        if old is None or (float(row["cost"]), row["program"]) < (float(old["cost"]), old["program"]):
            niches[key] = row
    selected = sorted(niches.values(), key=lambda row: (float(row["cost"]), len(row["program"]), row["program"]))[:limit]
    if len(selected) < limit:
        seen = {row["program"] for row in selected}
        for row in cost_frontier(candidates, limit * 4):
            if row["program"] not in seen:
                selected.append(row)
                seen.add(row["program"])
            if len(selected) == limit:
                break
    return selected


def novelty_cost_frontier(candidates: Iterable[Mapping[str, object]], limit: int = 64) -> list[dict]:
    """Greedily trade off visible syntax novelty against candidate cost."""
    pool = cost_frontier(candidates, max(limit * 8, limit))
    if not pool:
        return []
    selected = [pool.pop(0)]
    while pool and len(selected) < limit:
        def score(row):
            descriptor = _descriptor(row)
            distances = [sum(left != right for left, right in zip(descriptor, _descriptor(old))) for old in selected]
            novelty = min(distances) if distances else 0
            cost = float(row["cost"])
            return novelty / (1.0 + math.log1p(max(0.0, cost)))
        best = max(pool, key=lambda row: (score(row), -float(row["cost"]), row["program"]))
        selected.append(best)
        pool.remove(best)
    return sorted(selected, key=lambda row: (float(row["cost"]), len(row["program"]), row["program"]))
