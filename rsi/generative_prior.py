"""Bayesian program prior matching the synthetic task generator."""

from __future__ import annotations

import math

from .common import ROOT  # noqa: F401 - installs the pinned vendor import path
from dsl import CPos, Case, ConstStr, MatchPos, SubStr
from parse import parse


def position_log_probability(position) -> float:
    """Log probability under trapdoor.sample_pos."""
    if isinstance(position, CPos):
        if position.k >= 0:
            return math.log(0.5) + math.log(0.7 / 9.0)
        if -8 <= position.k <= -1:
            return math.log(0.5) + math.log(0.3 / 8.0)
        return -math.inf
    if isinstance(position, MatchPos):
        if position.tok not in ("WORD", "DIGITS", "UPPER", "LOWER") or position.n not in (1, 2) or position.side not in ("start", "end"):
            return -math.inf
        return math.log(0.5) + math.log(1 / 4) + math.log(1 / 2) + math.log(1 / 2)
    return -math.inf


def atom_log_probability(atom) -> float:
    if isinstance(atom, ConstStr):
        if atom.s not in (" ", "-", "/", ".", ", ", ": "):
            return -math.inf
        return math.log(0.25) + math.log(1 / 6)
    if isinstance(atom, SubStr):
        return math.log(0.60) + position_log_probability(atom.start) + position_log_probability(atom.end)
    if isinstance(atom, Case):
        if atom.op not in ("upper", "lower", "cap") or not isinstance(atom.atom, SubStr):
            return -math.inf
        # sample_atom chooses a case operation, then samples a substring with
        # allow_case=False, so the substring's .60 branch is conditional away.
        return math.log(0.15) + math.log(1 / 3) + position_log_probability(atom.atom.start) + position_log_probability(atom.atom.end)
    return -math.inf


def program_log_probability(program: str, generator_max_atoms: int = 4) -> float:
    try:
        parsed = parse(program)
    except Exception:
        return -math.inf
    if not 1 <= len(parsed.atoms) <= generator_max_atoms:
        return -math.inf
    score = -math.log(generator_max_atoms)
    for atom in parsed.atoms:
        score += atom_log_probability(atom)
    return score


def choose(candidates: list[dict], generator_max_atoms: int = 4) -> dict | None:
    if not candidates:
        return None
    return max(candidates, key=lambda row: (program_log_probability(row["program"], generator_max_atoms),
                                             -float(row.get("cost", 0.0)), row["program"]))
