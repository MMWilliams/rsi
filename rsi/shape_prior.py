"""Hierarchical prior combining generator likelihood with learned shapes."""

from __future__ import annotations

import json
import math

from .generative_prior import program_log_probability
from .grammar_library import atom_shape
from dsl import Concat
from parse import parse


def program_shape_bonus(program: str, library: dict) -> float:
    try:
        atoms = tuple(parse(program).atoms)
    except Exception:
        return 0.0
    counts = {json.dumps(item["shape"], sort_keys=True, separators=(",", ":")): item["count"]
              for item in library.get("templates", [])}
    best = 0.0
    for length in range(2, min(3, len(atoms)) + 1):
        for start in range(len(atoms) - length + 1):
            shape = json.dumps([atom_shape(atom) for atom in atoms[start:start + length]],
                               sort_keys=True, separators=(",", ":"))
            if shape in counts:
                best = max(best, math.log1p(counts[shape]))
    return best


def score(candidate: dict, library: dict, beta: float = 1.0) -> float:
    base = program_log_probability(candidate["program"])
    if not math.isfinite(base):
        return -math.inf
    return base + beta * program_shape_bonus(candidate["program"], library)


def choose(candidates: list[dict], library: dict, beta: float = 1.0) -> dict | None:
    if not candidates:
        return None
    return max(candidates, key=lambda row: (score(row, library, beta),
                                             program_log_probability(row["program"]),
                                             -float(row.get("cost", 0.0)), row["program"]))
