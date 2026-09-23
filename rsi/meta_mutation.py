"""Evolutionary retention policy for V72 mutation-generated programs."""

from __future__ import annotations

import copy
import random

from .common import canonical
from .invented_space import _split_atoms
from .semantic_invention import parse_span


RANK_MODES = ("shortest", "complexity", "mutation")


def annotate_candidates(candidates):
    result = []
    for candidate in candidates:
        row = dict(candidate)
        genome = candidate.get("mutation_genome", {})
        if not genome:
            genome = _program_genome(candidate["program"])
        row["mutation_terms"] = len(genome.get("positions", []))
        row["mutation_complexity"] = candidate.get("complexity", 999)
        result.append(row)
    return result


def _program_genome(program):
    found = {}
    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("mutation_genome"), dict):
                found.update(node["mutation_genome"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is not None:
                for boundary in span:
                    walk(boundary.get("predicate"))
    return found


def allows(candidate, architecture):
    return candidate.get("mutation_terms", 0) <= architecture["max_terms"]


def _score(candidate, architecture):
    if architecture["rank_mode"] == "complexity":
        return (-candidate["mutation_complexity"], -len(candidate["program"]), candidate["program"])
    if architecture["rank_mode"] == "mutation":
        return (candidate.get("mutation_terms", 0), -candidate["mutation_complexity"],
                -len(candidate["program"]), candidate["program"])
    return (-len(candidate["program"]), -candidate["mutation_complexity"], candidate["program"])


def choose_candidate(candidates, architecture):
    eligible = [candidate for candidate in candidates if allows(candidate, architecture)]
    return max(eligible, key=lambda candidate: _score(candidate, architecture)) if eligible else None


def canonical_architecture(architecture):
    return {"max_terms": int(architecture["max_terms"]), "rank_mode": architecture["rank_mode"]}


def initial_population(seed, size=24):
    rng = random.Random(seed)
    population = [{"max_terms": 8, "rank_mode": "shortest"},
                  {"max_terms": 8, "rank_mode": "complexity"},
                  {"max_terms": 4, "rank_mode": "shortest"},
                  {"max_terms": 6, "rank_mode": "mutation"}]
    while len(population) < size:
        population.append({"max_terms": rng.randint(1, 8), "rank_mode": rng.choice(RANK_MODES)})
    return [canonical_architecture(item) for item in population]


def _development_score(architecture, pools):
    correct = selected = 0
    for pool in pools:
        candidate = choose_candidate(pool["candidates"], architecture)
        if candidate is not None:
            selected += 1
            correct += int(candidate.get("oracle_correct", False))
    return correct, selected, -architecture["max_terms"]


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
            child = dict(parent)
            if rng.random() < 0.55:
                child["max_terms"] = max(1, min(8, child["max_terms"] + rng.choice((-2, -1, 1, 2))))
            if rng.random() < 0.25:
                child["rank_mode"] = rng.choice(RANK_MODES)
            next_population.append(canonical_architecture(child))
        current = next_population
    scored = sorted(((_development_score(item, development_pools), item) for item in current),
                    key=lambda row: (row[0], canonical(row[1])), reverse=True)
    trace.append({"generation": generations, "best_score": list(scored[0][0]),
                  "best_architecture": scored[0][1], "population": len(current)})
    return scored[0][1], trace
