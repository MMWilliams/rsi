"""Meta-evolution of the AST proposer's ranking policy for V67."""

from __future__ import annotations

import random


FEATURES = ("div", "mul", "xor", "mask", "shr", "not", "length")


def features(program: str) -> tuple[int, ...]:
    return tuple(program.count(name) for name in FEATURES[:-1]) + (len(program),)


def genome_score(program: str, genome: dict[str, int]) -> int:
    return sum(weight * value for weight, value in zip(genome["weights"], features(program)))


def choose_candidate(candidates: list[dict], genome: dict[str, int]) -> dict | None:
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: (genome_score(candidate["program"], genome), -len(candidate["program"]), candidate["program"]))


def initial_population(seed: int, size: int = 18) -> list[dict]:
    rng = random.Random(seed)
    population = [
        {"weights": [100, 10, 5, 2, 1, 0, -1]},
        {"weights": [25, 25, 5, 2, 1, 0, -1]},
        {"weights": [5, 25, 25, 2, 1, 0, -1]},
    ]
    while len(population) < size:
        population.append({"weights": [rng.randint(-20, 120) for _ in FEATURES[:-1]] + [rng.randint(-3, 0)]})
    return population


def evolve(population: list[dict], development_pools: list[dict], task_map: dict, generations: int = 4,
           elite_count: int = 4, seed: int = 0) -> tuple[dict, list[dict]]:
    rng = random.Random(seed)
    trace = []
    current = population
    for generation in range(generations):
        scored = []
        for genome in current:
            correct = 0
            for pool in development_pools:
                candidate = choose_candidate(pool["candidates"], genome)
                if candidate and candidate["oracle_correct"]:
                    correct += 1
            scored.append((correct, genome))
        scored.sort(key=lambda row: (row[0], row[1]["weights"]), reverse=True)
        trace.append({"generation": generation, "best_correct": scored[0][0],
                      "best_genome": scored[0][1], "population": len(current)})
        elites = [genome for _score, genome in scored[:elite_count]]
        next_population = list(elites)
        while len(next_population) < len(current):
            left, right = rng.choice(elites), rng.choice(elites)
            weights = [left["weights"][i] if rng.random() < 0.5 else right["weights"][i]
                       for i in range(len(FEATURES))]
            index = rng.randrange(len(weights))
            weights[index] += rng.randint(-15, 15)
            next_population.append({"weights": weights})
        current = next_population
    final_scores = []
    for genome in current:
        correct = sum(bool((candidate := choose_candidate(pool["candidates"], genome)) and candidate["oracle_correct"])
                      for pool in development_pools)
        final_scores.append((correct, genome))
    final_scores.sort(key=lambda row: (row[0], row[1]["weights"]), reverse=True)
    trace.append({"generation": generations, "best_correct": final_scores[0][0],
                  "best_genome": final_scores[0][1], "population": len(current)})
    return final_scores[0][1], trace
