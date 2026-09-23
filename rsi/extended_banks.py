"""Synthetic shifted-domain banks requiring variable-length delimiter semantics."""

from __future__ import annotations

import random

from .common import digest


def _examples(rng, family, count):
    if family == "email":
        return [f"{rng.choice(['ana','zoe','li','omar','priya'])}.{rng.choice(['smith','khan','ito','lee'])}{rng.randint(1,99)}@{rng.choice(['example.com','research.org','lab.net'])}" for _ in range(count)], "@"
    if family == "code":
        return ["".join(rng.choice("ABCDEFGH") for _ in range(rng.randint(2,5))) + "-" + str(rng.randint(10,99999)) for _ in range(count)], "-"
    if family == "iso":
        return [f"{rng.randint(1990,2035):04d}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}" for _ in range(count)], "-"
    if family == "slash":
        return [f"{rng.randint(1,28):02d}/{rng.randint(1,12):02d}/{rng.randint(1990,2035)}" for _ in range(count)], "/"
    if family == "path":
        return [f"/srv/{rng.choice(['alpha','beta','gamma','delta'])}/{rng.choice(['raw','clean','out'])}/{rng.randint(1,999)}" for _ in range(count)], "/"
    return [f"{rng.choice(['id','key','tag','mode'])}={rng.choice(['alpha','beta','gamma','delta'])}{rng.randint(1,99)}" for _ in range(count)], "="


def make_task(rng, split, index, visible_examples=3, hidden_examples=13):
    family = rng.choice(("email", "code", "iso", "slash", "path", "equals"))
    inputs, delimiter = _examples(rng, family, visible_examples + hidden_examples)
    op = rng.choice(("Before", "After"))
    occurrences = [text.count(delimiter) for text in inputs]
    ordinal = rng.choice([1, 2]) if min(occurrences) >= 2 else 1
    outputs = []
    for text in inputs:
        positions = [i for i in range(len(text)) if text.startswith(delimiter, i)]
        index = positions[ordinal - 1]
        outputs.append(text[:index] if op == "Before" else text[index + len(delimiter):])
    reference = f'{op}("{delimiter}",{ordinal})'
    examples = list(zip(inputs, outputs))
    return {"id": digest([split, index, reference, examples])[:20], "reference": reference,
            "operator_family": op.lower(), "visible": examples[:visible_examples],
            "hidden": examples[visible_examples:]}


def create_extended_banks(config):
    rng = random.Random(config["bank_seed"])
    banks = {}
    metadata = {}
    seen = set()
    for split, count in config["bank_counts"].items():
        rows = []
        attempts = 0
        while len(rows) < count:
            attempts += 1
            task = make_task(rng, split, len(rows) + attempts, config["visible_examples"], config["hidden_examples"])
            key = (task["reference"], tuple(tuple(pair) for pair in task["visible"] + task["hidden"]))
            if key in seen:
                continue
            seen.add(key)
            rows.append(task)
        banks[split] = rows
        metadata[split] = {"count": len(rows), "sha256": digest(rows), "attempts": attempts}
    return banks, metadata
