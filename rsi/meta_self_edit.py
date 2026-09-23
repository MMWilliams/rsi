"""Evolutionary grammar-editor policy for V73."""

from __future__ import annotations

import copy
import random

from .common import canonical
from .invented_space import _split_atoms
from .semantic_invention import parse_span
from .self_editing_grammar import SAFE_OPS


def _walk(node, operations):
    if isinstance(node, dict):
        if isinstance(node.get("grammar_ops"), list):
            operations.update(node["grammar_ops"])
        for value in node.values():
            _walk(value, operations)
    elif isinstance(node, list):
        for value in node:
            _walk(value, operations)


def required_ops(program):
    operations = set()
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is not None:
                for boundary in span:
                    _walk(boundary.get("predicate"), operations)
    return tuple(sorted(operations))


def complexity(program):
    values = []
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is not None:
                for boundary in span:
                    predicate = boundary.get("predicate")
                    if isinstance(predicate, dict) and isinstance(predicate.get("complexity"), int):
                        values.append(predicate["complexity"])
    return max(values, default=999)


def annotate_candidates(candidates):
    result = []
    for candidate in candidates:
        row = dict(candidate)
        row["required_ops"] = list(required_ops(candidate["program"]))
        row["grammar_complexity"] = complexity(candidate["program"])
        result.append(row)
    return result


def allows(candidate, architecture):
    return (set(candidate.get("required_ops", required_ops(candidate["program"])))
            <= set(architecture["enabled_ops"])
            and candidate.get("grammar_complexity", complexity(candidate["program"])) <= architecture["max_complexity"])


def _score(candidate, architecture):
    if architecture["rank_mode"] == "complexity":
        return (-candidate["grammar_complexity"], -len(candidate["program"]), candidate["program"])
    if architecture["rank_mode"] == "novelty":
        return (len(candidate.get("required_ops", [])), -candidate["grammar_complexity"],
                -len(candidate["program"]), candidate["program"])
    return (-len(candidate["program"]), -candidate["grammar_complexity"], candidate["program"])


def choose_candidate(candidates, architecture):
    eligible = [candidate for candidate in candidates if allows(candidate, architecture)]
    return max(eligible, key=lambda candidate: _score(candidate, architecture)) if eligible else None


def canonical_architecture(architecture):
    return {"enabled_ops": sorted(set(architecture["enabled_ops"])),
            "max_complexity": int(architecture["max_complexity"]),
            "rank_mode": architecture["rank_mode"]}


def initial_population(seed, size=24):
    rng = random.Random(seed)
    base = ["and", "shr", "xor", "add", "mod"]
    population = [{"enabled_ops": base, "max_complexity": 999, "rank_mode": "shortest"},
                  {"enabled_ops": list(SAFE_OPS), "max_complexity": 999, "rank_mode": "shortest"},
                  {"enabled_ops": base + ["not"], "max_complexity": 999, "rank_mode": "complexity"},
                  {"enabled_ops": base + ["or", "sub"], "max_complexity": 999, "rank_mode": "novelty"}]
    while len(population) < size:
        population.append({"enabled_ops": [op for op in SAFE_OPS if rng.random() < 0.6],
                           "max_complexity": rng.choice((300, 500, 800, 999)),
                           "rank_mode": rng.choice(("shortest", "complexity", "novelty"))})
    return [canonical_architecture(item) for item in population]


def _development_score(architecture, pools):
    correct = selected = 0
    for pool in pools:
        candidate = choose_candidate(pool["candidates"], architecture)
        if candidate is not None:
            selected += 1
            correct += int(candidate.get("oracle_correct", False))
    return correct, selected, -len(architecture["enabled_ops"])


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
            parent = rng.choice(elites)
            enabled = list(parent["enabled_ops"])
            if rng.random() < 0.7:
                op = rng.choice(SAFE_OPS)
                if op in enabled and len(enabled) > 1:
                    enabled.remove(op)
                elif op not in enabled:
                    enabled.append(op)
            complexity_value = parent["max_complexity"] if rng.random() < 0.7 else rng.choice((300, 500, 800, 999))
            mode = parent["rank_mode"] if rng.random() < 0.8 else rng.choice(("shortest", "complexity", "novelty"))
            next_population.append(canonical_architecture({"enabled_ops": enabled,
                                                             "max_complexity": complexity_value,
                                                             "rank_mode": mode}))
        current = next_population
    scored = sorted(((_development_score(item, development_pools), item) for item in current),
                    key=lambda row: (row[0], canonical(row[1])), reverse=True)
    trace.append({"generation": generations, "best_score": list(scored[0][0]),
                  "best_architecture": scored[0][1], "population": len(current)})
    return scored[0][1], trace
