"""Evolutionary retention policy for V70 stack programs."""

from __future__ import annotations

import copy
import random

from .common import canonical
from .invented_space import _split_atoms
from .semantic_invention import parse_span


STACK_FAMILIES = ("fold", "bitmix")
RANK_MODES = ("frozen", "shortest", "complexity", "novelty")


def _walk(node, families):
    if isinstance(node, dict):
        if node.get("stack_family") in STACK_FAMILIES:
            families.add(node["stack_family"])
        for value in node.values():
            _walk(value, families)
    elif isinstance(node, list):
        for value in node:
            _walk(value, families)


def stack_families(program):
    families = set()
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is None:
                continue
            for boundary in span:
                _walk(boundary.get("predicate"), families)
    return tuple(sorted(families))


def complexity(program):
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
    result = []
    for candidate in candidates:
        row = dict(candidate)
        row["stack_families"] = list(stack_families(candidate["program"]))
        row["stack_complexity"] = complexity(candidate["program"])
        row["stack_source"] = row["stack_families"][0] if row["stack_families"] else "legacy"
        result.append(row)
    return result


def allows(candidate, architecture):
    return (set(candidate.get("stack_families", stack_families(candidate["program"])))
            <= set(architecture["enabled_families"])
            and candidate.get("stack_complexity", complexity(candidate["program"]))
            <= architecture["max_complexity"])


def _score(candidate, architecture):
    program = candidate["program"]
    mode = architecture["rank_mode"]
    if mode == "frozen":
        return (-len(program), program)
    if mode == "complexity":
        return (-candidate["stack_complexity"], -len(program), program)
    if mode == "novelty":
        return (sum(program.count(family) for family in STACK_FAMILIES),
                -candidate["stack_complexity"], -len(program), program)
    return (-len(program), -candidate["stack_complexity"], program)


def choose_candidate(candidates, architecture):
    eligible = [candidate for candidate in candidates if allows(candidate, architecture)]
    return max(eligible, key=lambda candidate: _score(candidate, architecture)) if eligible else None


def canonical_architecture(architecture):
    return {"enabled_families": sorted(set(architecture["enabled_families"])),
            "max_complexity": int(architecture["max_complexity"]),
            "rank_mode": architecture["rank_mode"]}


def initial_population(seed, size=24):
    rng = random.Random(seed)
    population = [
        {"enabled_families": [], "max_complexity": 999, "rank_mode": "frozen"},
        {"enabled_families": list(STACK_FAMILIES), "max_complexity": 999, "rank_mode": "frozen"},
        {"enabled_families": ["fold"], "max_complexity": 999, "rank_mode": "complexity"},
        {"enabled_families": ["bitmix"], "max_complexity": 999, "rank_mode": "shortest"},
    ]
    while len(population) < size:
        population.append({"enabled_families": [family for family in STACK_FAMILIES if rng.random() < 0.65],
                           "max_complexity": rng.choice((180, 240, 320, 999)),
                           "rank_mode": rng.choice(RANK_MODES[1:])})
    return [canonical_architecture(item) for item in population]


def _development_score(architecture, pools):
    correct = 0
    selected = 0
    for pool in pools:
        candidate = choose_candidate(pool["candidates"], architecture)
        if candidate is not None:
            selected += 1
            correct += int(candidate.get("oracle_correct", False))
    return correct, selected, -len(architecture["enabled_families"])


def evolve(population, development_pools, generations=5, elite_count=5, seed=0):
    rng = random.Random(seed)
    current = [copy.deepcopy(item) for item in population]
    trace = []
    for generation in range(generations):
        scored = sorted(((_development_score(item, development_pools), item) for item in current),
                        key=lambda row: (row[0], canonical(row[1])), reverse=True)
        trace.append({"generation": generation, "best_score": list(scored[0][0]),
                      "best_architecture": scored[0][1], "population": len(current)})
        elites = [item for _score, item in scored[:elite_count]]
        next_population = [copy.deepcopy(item) for item in elites]
        while len(next_population) < len(current):
            left, right = rng.choice(elites), rng.choice(elites)
            enabled = [family for family in STACK_FAMILIES
                       if (family in left["enabled_families"] if rng.random() < 0.5
                           else family in right["enabled_families"])]
            if rng.random() < 0.70:
                family = rng.choice(STACK_FAMILIES)
                if family in enabled and len(enabled) > 1:
                    enabled.remove(family)
                elif family not in enabled:
                    enabled.append(family)
            complexity_value = left["max_complexity"] if rng.random() < 0.5 else right["max_complexity"]
            if rng.random() < 0.30:
                complexity_value = rng.choice((180, 240, 320, 999))
            mode = left["rank_mode"] if rng.random() < 0.5 else right["rank_mode"]
            if rng.random() < 0.20:
                mode = rng.choice(RANK_MODES[1:])
            next_population.append(canonical_architecture({"enabled_families": enabled,
                                                             "max_complexity": complexity_value,
                                                             "rank_mode": mode}))
        current = next_population
    scored = sorted(((_development_score(item, development_pools), item) for item in current),
                    key=lambda row: (row[0], canonical(row[1])), reverse=True)
    trace.append({"generation": generations, "best_score": list(scored[0][0]),
                  "best_architecture": scored[0][1], "population": len(current)})
    return scored[0][1], trace
