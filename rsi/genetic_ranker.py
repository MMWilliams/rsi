"""Evolutionary synthesis of a candidate-ranking program."""

from __future__ import annotations

import math
import random

from .generative_prior import program_log_probability
from .meta_ranker import program_features
from parse import parse


FEATURES = ("bias", "generator_logp", "candidate_cost", "atom_count", "const_atoms",
            "substr_atoms", "case_atoms", "cpos_positions", "match_positions",
            "negative_positions", "constant_chars")


def vector(candidate: dict) -> tuple[float, ...]:
    program = candidate.get("program", "")
    values = {name: 0.0 for name in FEATURES}
    values["bias"] = 1.0
    lp = program_log_probability(program)
    values["generator_logp"] = max(-40.0, lp) if math.isfinite(lp) else -40.0
    values["candidate_cost"] = float(candidate.get("cost", 0.0))
    try:
        parsed = parse(program)
        values["atom_count"] = len(parsed.atoms)
        sparse = program_features(program)
        values["const_atoms"] = sparse.get("atom:const", 0.0)
        values["substr_atoms"] = sparse.get("atom:substr", 0.0)
        values["case_atoms"] = sparse.get("atom:case", 0.0)
        values["cpos_positions"] = sum(value for key, value in sparse.items() if ":cpos" in key and key.endswith("cpos"))
        values["match_positions"] = sum(value for key, value in sparse.items() if ":match" in key and key.endswith("match"))
        values["negative_positions"] = sparse.get("substr:start:negative", 0.0) + sparse.get("substr:end:negative", 0.0)
        values["constant_chars"] = sparse.get("atom:const:length", 0.0)
    except Exception:
        pass
    return tuple(values[name] for name in FEATURES)


def score(weights: tuple[float, ...], candidate: dict) -> float:
    return sum(left * right for left, right in zip(weights, vector(candidate)))


def choose(weights: tuple[float, ...], candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    return max(candidates, key=lambda row: (score(weights, row), -float(row.get("cost", 0.0)), row.get("program", "")))


def hashable(weights):
    return tuple(round(float(value), 10) for value in weights)


def mutate(parent: tuple[float, ...], rng: random.Random, sigma: float) -> tuple[float, ...]:
    child = list(parent)
    for index in range(len(child)):
        if rng.random() < 0.75:
            child[index] += rng.gauss(0.0, sigma)
        child[index] = max(-12.0, min(12.0, child[index]))
    return hashable(child)


def evolve(dataset: list[dict], population_size: int = 32,
           generations: int = 24, elite_size: int = 8, sigma: float = 0.35,
           seed: int = 0) -> tuple[tuple[float, ...], dict]:
    rng = random.Random(seed)
    baseline = tuple(1.0 if name == "generator_logp" else 0.0 for name in FEATURES)
    population = [baseline] + [hashable(rng.uniform(-1.0, 1.0) for _ in FEATURES)
                               for _ in range(max(1, population_size - 1))]
    trace = []

    def fitness(weights):
        correct = 0
        mean_margin = 0.0
        for row in dataset:
            selected = choose(weights, row["candidates"])
            if selected is not None and row["oracle_labels"].get(selected["program"], False):
                correct += 1
            # A tiny deterministic tie-break rewards separation without changing
            # the primary correctness objective.
            if selected is not None:
                mean_margin += score(weights, selected)
        return correct, mean_margin

    for generation in range(generations):
        ranked = sorted(((fitness(weights), weights) for weights in population),
                        key=lambda item: (item[0][0], item[0][1], tuple(-x for x in item[1])), reverse=True)
        elites = [weights for _, weights in ranked[:elite_size]]
        trace.append({"generation": generation, "best_correct": ranked[0][0][0],
                      "best_score_sum": ranked[0][0][1], "weights": list(ranked[0][1])})
        population = elites[:]
        while len(population) < population_size:
            parent = rng.choice(elites)
            population.append(mutate(parent, rng, sigma))
    ranked = sorted(((fitness(weights), weights) for weights in population),
                    key=lambda item: (item[0][0], item[0][1], tuple(-x for x in item[1])), reverse=True)
    best = ranked[0][1]
    return best, {"features": list(FEATURES), "population_size": population_size,
                  "generations": generations, "elite_size": elite_size, "sigma": sigma,
                  "seed": seed, "trace": trace, "best_correct": ranked[0][0][0],
                  "weights": list(best)}
