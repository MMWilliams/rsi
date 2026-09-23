from __future__ import annotations

import random
import re

from .common import digest
from .oracle import correct
from trapdoor import make_task


def template(program: str) -> str:
    return re.sub(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", "'LITERAL'", program)


def create_banks(config: dict, excluded_templates=()) -> tuple[dict, dict]:
    rng = random.Random(config["bank_seed"])
    seen_programs, seen_templates = set(), set(excluded_templates)
    banks, metadata = {}, {}
    for split, count in config["bank_counts"].items():
        rows, own_templates = [], set()
        attempts = 0
        while len(rows) < count:
            attempts += 1
            if attempts > count * 10000:
                raise RuntimeError("Cannot fill disjoint task bank")
            task = make_task(rng, n_examples=config["visible_examples"] + config["hidden_examples"], max_atoms=config["max_atoms"])
            if task is None or task.program_text in seen_programs or template(task.program_text) in seen_templates:
                continue
            examples = [list(pair) for pair in task.examples]
            if not correct(task.program_text, examples):
                raise AssertionError("Independent oracle disagrees with task generator")
            seen_programs.add(task.program_text)
            own_templates.add(template(task.program_text))
            cut = config["visible_examples"]
            rows.append({"id": digest([split, task.program_text, examples])[:20], "reference": task.program_text,
                         "visible": examples[:cut], "hidden": examples[cut:]})
        seen_templates.update(own_templates)
        banks[split] = rows
        metadata[split] = {"count": len(rows), "templates": len(own_templates), "sha256": digest(rows), "attempts": attempts}
    return banks, metadata


def public_task(task: dict) -> dict:
    return {"id": task["id"], "visible": task["visible"]}
