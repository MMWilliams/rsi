"""Small, dependency-free research-design primitives for RSI sweeps.

These helpers do not claim to implement a complete RL trainer. They provide
reproducible allocation, search, and analysis machinery around the existing
audited runner so exploratory results can be compared without silently
changing the confirmatory protocol.
"""

from __future__ import annotations

import copy
import math
import random
from itertools import product
from typing import Iterable, Mapping, Sequence


def factorial_size(space: Mapping[str, Mapping[str, object]]) -> int:
    """Return the size of a discrete Cartesian design."""
    size = 1
    for spec in space.values():
        values = spec.get("values")
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
            raise ValueError("factorial_size requires non-empty discrete values")
        size *= len(values)
    return size


def factorial_design(space: Mapping[str, Mapping[str, object]]) -> list[dict[str, object]]:
    """Enumerate a deterministic Cartesian design from discrete factors."""
    names = list(space)
    values = []
    for name in names:
        options = space[name].get("values")
        if not isinstance(options, Sequence) or isinstance(options, (str, bytes)) or not options:
            raise ValueError(f"{name} is not a discrete factor")
        values.append(list(options))
    return [dict(zip(names, row)) for row in product(*values)]


def latin_hypercube(space: Mapping[str, Mapping[str, object]], samples: int, seed: int) -> list[dict[str, object]]:
    """Generate a deterministic mixed numeric/categorical Latin-hypercube design."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    rng = random.Random(seed)
    columns: dict[str, list[object]] = {}
    for name, spec in space.items():
        if "values" in spec:
            values = list(spec["values"])
            if not values:
                raise ValueError(f"{name} has no values")
            columns[name] = [values[index % len(values)] for index in rng.sample(range(samples), samples)]
            continue
        low, high = float(spec["low"]), float(spec["high"])
        if not math.isfinite(low) or not math.isfinite(high) or low > high:
            raise ValueError(f"invalid range for {name}")
        bins = list(range(samples))
        rng.shuffle(bins)
        columns[name] = [low + (bin_index + rng.random()) / samples * (high - low) for bin_index in bins]
    return [{name: columns[name][row] for name in space} for row in range(samples)]


def apply_overrides(base: Mapping[str, object], overrides: Mapping[str, object]) -> dict[str, object]:
    """Copy a JSON-like config and apply dotted-path overrides."""
    result = copy.deepcopy(dict(base))
    for path, value in overrides.items():
        parts = path.split(".")
        cursor = result
        for part in parts[:-1]:
            if not isinstance(cursor, dict):
                raise ValueError(f"Cannot descend through {path}")
            cursor = cursor.setdefault(part, {})
        if not isinstance(cursor, dict):
            raise ValueError(f"Cannot assign {path}")
        cursor[parts[-1]] = value
    return result


def ucb1(counts: Sequence[int], rewards: Sequence[float], total: int | None = None) -> int:
    """Select an arm with UCB1; untried arms are selected first."""
    if len(counts) != len(rewards) or not counts:
        raise ValueError("counts and rewards must be equally sized and non-empty")
    for index, count in enumerate(counts):
        if count == 0:
            return index
        if count < 0:
            raise ValueError("counts must be non-negative")
    total = total if total is not None else sum(counts)
    if total <= 0:
        raise ValueError("total must be positive after initialization")
    return max(range(len(counts)), key=lambda i: rewards[i] / counts[i] + math.sqrt(2 * math.log(total) / counts[i]))


def thompson_beta(alpha: Sequence[float], beta: Sequence[float], seed: int) -> int:
    """Sample a Bernoulli arm posterior for lightweight adaptive allocation."""
    if len(alpha) != len(beta) or not alpha:
        raise ValueError("alpha and beta must be equally sized and non-empty")
    if any(a <= 0 or b <= 0 for a, b in zip(alpha, beta)):
        raise ValueError("beta posterior parameters must be positive")
    rng = random.Random(seed)
    return max(range(len(alpha)), key=lambda i: rng.betavariate(alpha[i], beta[i]))


def pareto_front(rows: Iterable[Mapping[str, float]], maximize: Sequence[str]) -> list[dict[str, float]]:
    """Return non-dominated rows for the requested maximization metrics."""
    rows = [dict(row) for row in rows]
    result = []
    for candidate in rows:
        dominated = False
        for other in rows:
            if other is candidate:
                continue
            no_worse = all(other[key] >= candidate[key] for key in maximize)
            strictly_better = any(other[key] > candidate[key] for key in maximize)
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            result.append(candidate)
    return result
