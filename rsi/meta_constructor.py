"""Evolutionary selection of failure-driven typed constructors for V69."""

from __future__ import annotations

import copy
import random

from .common import canonical
from .invented_space import _split_atoms
from .semantic_invention import parse_span


CONSTRUCTORS = ("popcount", "parity", "rotl", "gcd")
RANK_MODES = ("frozen", "shortest", "complexity", "novelty")


def _walk(node, operations):
    if isinstance(node, dict):
        if node.get("op") in CONSTRUCTORS:
            operations.add(node["op"])
        for value in node.values():
            _walk(value, operations)
    elif isinstance(node, list):
        for value in node:
            _walk(value, operations)


def constructor_operations(program: str) -> tuple[str, ...]:
    operations = set()
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is None:
                continue
            for boundary in span:
                _walk(boundary.get("predicate"), operations)
    return tuple(sorted(operations))


def constructor_complexity(program: str) -> int:
    values = []
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is None:
                continue
            for boundary in span:
                predicate = boundary.get("predicate")
                if isinstance(predicate, dict) and isinstance(predicate.get("complexity"), int):
                    values.append(predicate["complexity"])
    return max(values, default=999)


def annotate_candidates(candidates):
    annotated = []
    for candidate in candidates:
        row = dict(candidate)
        row["constructor_ops"] = list(constructor_operations(candidate["program"]))
        row["constructor_complexity"] = constructor_complexity(candidate["program"])
        row["constructor_family"] = (row["constructor_ops"][0]
                                      if row["constructor_ops"] else "legacy")
        annotated.append(row)
    return annotated


def architecture_allows(candidate, architecture):
    return (set(candidate.get("constructor_ops", constructor_operations(candidate["program"])))
            <= set(architecture["enabled_constructors"])
            and candidate.get("constructor_complexity", constructor_complexity(candidate["program"]))
            <= architecture["max_complexity"])


def _score(candidate, architecture):
    program = candidate["program"]
    mode = architecture["rank_mode"]
    if mode == "frozen":
        return (-len(program), program)
    if mode == "shortest":
        return (-len(program), -candidate["constructor_complexity"], program)
    if mode == "complexity":
        return (-candidate["constructor_complexity"], -len(program), program)
    return (sum(program.count(op) for op in CONSTRUCTORS),
            -candidate["constructor_complexity"], -len(program), program)


def choose_candidate(candidates, architecture):
    eligible = [candidate for candidate in candidates if architecture_allows(candidate, architecture)]
    return max(eligible, key=lambda candidate: _score(candidate, architecture)) if eligible else None


def canonical_architecture(architecture):
    return {"enabled_constructors": sorted(set(architecture["enabled_constructors"])),
            "max_complexity": int(architecture["max_complexity"]),
            "rank_mode": architecture["rank_mode"]}


def initial_population(seed: int, size: int = 24):
    rng = random.Random(seed)
    population = [
        {"enabled_constructors": [], "max_complexity": 999, "rank_mode": "frozen"},
        {"enabled_constructors": list(CONSTRUCTORS), "max_complexity": 999, "rank_mode": "frozen"},
        {"enabled_constructors": ["popcount", "parity"], "max_complexity": 999, "rank_mode": "complexity"},
        {"enabled_constructors": ["rotl"], "max_complexity": 999, "rank_mode": "shortest"},
        {"enabled_constructors": ["gcd"], "max_complexity": 999, "rank_mode": "shortest"},
    ]
    while len(population) < size:
        enabled = [op for op in CONSTRUCTORS if rng.random() < 0.65]
        population.append({"enabled_constructors": enabled,
                           "max_complexity": rng.choice((180, 220, 280, 999)),
                           "rank_mode": rng.choice(RANK_MODES[1:])})
    return [canonical_architecture(item) for item in population]


def _score_development(architecture, pools):
    correct = 0
    selected = 0
    for pool in pools:
        candidate = choose_candidate(pool["candidates"], architecture)
        if candidate is not None:
            selected += 1
            correct += int(candidate.get("oracle_correct", False))
    return correct, selected, -len(architecture["enabled_constructors"])


def evolve(population, development_pools, generations=5, elite_count=5, seed=0):
    rng = random.Random(seed)
    current = [copy.deepcopy(item) for item in population]
    trace = []
    for generation in range(generations):
        scored = sorted(((_score_development(item, development_pools), item) for item in current),
                        key=lambda row: (row[0], canonical(row[1])), reverse=True)
        trace.append({"generation": generation, "best_score": list(scored[0][0]),
                      "best_architecture": scored[0][1], "population": len(current)})
        elites = [item for _score, item in scored[:elite_count]]
        next_population = [copy.deepcopy(item) for item in elites]
        while len(next_population) < len(current):
            left, right = rng.choice(elites), rng.choice(elites)
            enabled = [op for op in CONSTRUCTORS
                       if (op in left["enabled_constructors"] if rng.random() < 0.5
                           else op in right["enabled_constructors"])]
            if rng.random() < 0.70:
                op = rng.choice(CONSTRUCTORS)
                if op in enabled and len(enabled) > 1:
                    enabled.remove(op)
                elif op not in enabled:
                    enabled.append(op)
            complexity = left["max_complexity"] if rng.random() < 0.5 else right["max_complexity"]
            if rng.random() < 0.30:
                complexity = rng.choice((180, 220, 280, 999))
            mode = left["rank_mode"] if rng.random() < 0.5 else right["rank_mode"]
            if rng.random() < 0.20:
                mode = rng.choice(RANK_MODES[1:])
            next_population.append(canonical_architecture({"enabled_constructors": enabled,
                                                             "max_complexity": complexity,
                                                             "rank_mode": mode}))
        current = next_population
    scored = sorted(((_score_development(item, development_pools), item) for item in current),
                    key=lambda row: (row[0], canonical(row[1])), reverse=True)
    trace.append({"generation": generations, "best_score": list(scored[0][0]),
                  "best_architecture": scored[0][1], "population": len(current)})
    return scored[0][1], trace
