"""A small learned prior for selecting among visible-equivalent programs."""

from __future__ import annotations

import math
from collections import defaultdict

from .common import ROOT  # noqa: F401 - installs the pinned vendor import path
from dsl import Case, CPos, ConstStr, MatchPos, SubStr
from parse import parse


def _add(row: dict[str, float], name: str, value: float = 1.0) -> None:
    row[name] = row.get(name, 0.0) + value


def _position_features(row: dict[str, float], position, prefix: str) -> None:
    if isinstance(position, CPos):
        _add(row, prefix + ":cpos")
        _add(row, f"{prefix}:cpos:{position.k}")
        _add(row, prefix + ":negative", float(position.k < 0))
    elif isinstance(position, MatchPos):
        _add(row, prefix + ":match")
        _add(row, f"{prefix}:match:{position.tok}:{position.n}:{position.side}")
        _add(row, f"{prefix}:token:{position.tok}")


def _atom_features(row: dict[str, float], atom) -> None:
    if isinstance(atom, ConstStr):
        _add(row, "atom:const")
        _add(row, "atom:const:length", len(atom.s))
        _add(row, f"atom:const:value:{atom.s}")
    elif isinstance(atom, SubStr):
        _add(row, "atom:substr")
        _position_features(row, atom.start, "substr:start")
        _position_features(row, atom.end, "substr:end")
    elif isinstance(atom, Case):
        _add(row, "atom:case")
        _add(row, f"atom:case:{atom.op}")
        _atom_features(row, atom.atom)


def program_features(program: str, cost: float = 0.0) -> dict[str, float]:
    """Extract sparse structural features from a canonical candidate program."""
    row = {"bias": 1.0, "candidate:cost": float(cost)}
    parsed = parse(program)
    _add(row, "program:atoms", len(parsed.atoms))
    _add(row, f"program:atom-count:{len(parsed.atoms)}")
    for atom in parsed.atoms:
        _atom_features(row, atom)
    return row


class PairwisePrior:
    """Online pairwise ranker trained from oracle-resolved development tasks."""

    def __init__(self, learning_rate: float = 0.05, margin: float = 0.1):
        self.learning_rate = learning_rate
        self.margin = margin
        self.weights: dict[str, float] = defaultdict(float)
        self.updates = 0

    def score(self, candidate: dict) -> float:
        features = program_features(candidate["program"], candidate.get("cost", 0.0))
        return sum(self.weights[name] * value for name, value in features.items())

    def update(self, positive: dict, negative: dict) -> bool:
        pos = program_features(positive["program"], positive.get("cost", 0.0))
        neg = program_features(negative["program"], negative.get("cost", 0.0))
        names = set(pos) | set(neg)
        gap = sum(self.weights[name] * (pos.get(name, 0.0) - neg.get(name, 0.0)) for name in names)
        if gap >= self.margin:
            return False
        scale = self.learning_rate
        for name in names:
            self.weights[name] += scale * (pos.get(name, 0.0) - neg.get(name, 0.0))
        self.updates += 1
        return True

    def fit(self, rows: list[tuple[dict, list[dict]]], epochs: int = 3) -> dict:
        for _ in range(epochs):
            for positive, candidates in rows:
                for negative in candidates:
                    if negative["program"] != positive["program"]:
                        self.update(positive, negative)
        return {"updates": self.updates, "weights": dict(sorted(self.weights.items()))}

    def choose(self, candidates: list[dict]) -> dict | None:
        if not candidates:
            return None
        return max(candidates, key=lambda row: (self.score(row), -float(row.get("cost", 0.0)),
                                                 -len(row["program"]), row["program"]))
