"""Counterexample-guided grow/delete/splice synthesis for V72.

The search manipulates typed instruction fragments rather than named operator
families.  A genome is a set of bit-extraction fragments plus a reducer and an
optional modulus.  Visible behavior signatures provide the fitness signal;
hidden outputs are never consulted while proposing programs.
"""

from __future__ import annotations

import random

from .common import canonical
from .stack_program import evaluate_stack


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def _fragment(position):
    return ({"op": "load_ord"}, {"op": "const", "value": 1 << position},
            {"op": "and"}, {"op": "const", "value": position}, {"op": "shr"})


def _compile(genome):
    instructions = []
    for index, position in enumerate(genome["positions"]):
        instructions.extend(_fragment(position))
        if index:
            instructions.append({"op": genome["reducer"]})
    if genome["modulus"] is not None:
        instructions.extend(({"op": "const", "value": genome["modulus"]}, {"op": "mod"}))
    return instructions


def _canonical_genome(genome):
    positions = sorted(set(int(position) for position in genome["positions"]))
    return {"positions": positions, "reducer": genome["reducer"], "modulus": genome["modulus"]}


def _mutate(genome, rng, max_terms):
    action = rng.choice(("grow", "delete", "splice", "reducer", "modulus"))
    positions = list(genome["positions"])
    if action == "grow" and len(positions) < max_terms:
        positions.append(rng.choice([position for position in range(8) if position not in positions] or [rng.randrange(8)]))
    elif action == "delete" and len(positions) > 1:
        positions.pop(rng.randrange(len(positions)))
    elif action == "splice":
        extra = rng.sample(range(8), k=rng.randint(1, min(3, 8)))
        positions.extend(extra)
        positions = positions[:max_terms]
    elif action == "reducer":
        genome = {**genome, "reducer": "add" if genome["reducer"] == "xor" else "xor"}
    elif action == "modulus":
        genome = {**genome, "modulus": rng.choice((None, 2, 3, 4, 5, 6))}
    return _canonical_genome({**genome, "positions": positions}), action


def _fitness(genome, chars, target_mask, other_mask):
    values = tuple(evaluate_stack(_compile(genome), char) for char in chars)
    masks = {}
    for relation in ("eq", "lt", "ge"):
        for constant in range(0, 10):
            mask = 0
            for index, value in enumerate(values):
                result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                if result:
                    mask |= 1 << index
            masks[(relation, constant)] = mask
    best = max(masks.items(), key=lambda item: (-(item[1] ^ target_mask).bit_count(), -len(_compile(genome))))
    distance = (best[1] ^ target_mask).bit_count()
    exact = best[1] == target_mask or best[1] == other_mask
    return distance, exact, best[0], best[1], values


def synthesize_mutated_stack_programs(visible: list[list[str]], max_terms=8,
                                      iterations=8, population_size=40, seed=0):
    target, other, chars = _aligned(visible)
    if not target or not other:
        return [], []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    rng = random.Random(seed)
    population = []
    # These are generic typed seeds, not mechanism-family templates.
    for position in range(8):
        population.append({"positions": [position], "reducer": "xor", "modulus": None})
    population.extend((
        {"positions": list(range(8)), "reducer": "xor", "modulus": None},
        {"positions": list(range(8)), "reducer": "add", "modulus": 2},
        {"positions": list(range(8)), "reducer": "add", "modulus": 3},
        {"positions": list(range(8)), "reducer": "add", "modulus": 4},
        {"positions": list(range(8)), "reducer": "add", "modulus": 5},
    ))
    while len(population) < population_size:
        count = rng.randint(1, max_terms)
        population.append({"positions": sorted(rng.sample(range(8), count)),
                           "reducer": rng.choice(("xor", "add")),
                           "modulus": rng.choice((None, 2, 3, 4, 5, 6))})
    population = [_canonical_genome(item) for item in population]
    trace, found = [], {}
    for generation in range(iterations + 1):
        scored = []
        for genome in population:
            distance, exact, relation, mask, _values = _fitness(genome, chars, target_mask, other_mask)
            scored.append((distance, len(_compile(genome)), canonical(genome), genome, exact, relation, mask))
            if exact:
                final_relation, constant = relation
                predicate = {"op": final_relation,
                             "left": {"op": "stack", "instructions": _compile(genome)},
                             "right": constant}
                if mask == other_mask:
                    predicate = {"op": "not", "arg": predicate}
                key = canonical(predicate)
                found.setdefault(key, {"kind": "ord_expr", "expr": predicate,
                                       "complexity": len(key), "mutation_source": "counterexample_guided",
                                       "mutation_genome": genome})
        scored.sort(key=lambda row: (row[0], row[1], row[2]))
        trace.append({"generation": generation, "best_distance": scored[0][0],
                      "best_genome": scored[0][3], "population": len(population),
                      "exact_count": sum(row[4] for row in scored)})
        if generation == iterations:
            break
        elites = [row[3] for row in scored[:max(8, population_size // 4)]]
        next_population = list(elites)
        while len(next_population) < population_size:
            parent = rng.choice(elites)
            child, _action = _mutate(parent, rng, max_terms)
            next_population.append(child)
        population = next_population
    return sorted(found.values(), key=lambda row: (row["complexity"], canonical(row["expr"])))[:512], trace
