"""Visible-only macro mining and replay for V74."""

from __future__ import annotations

from collections import defaultdict

from .common import canonical, digest
from .self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from .stack_program import evaluate_stack


def _stack_nodes(node):
    if isinstance(node, dict):
        if node.get("op") == "stack":
            yield node
        for value in node.values():
            yield from _stack_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _stack_nodes(value)


def mine_macro_library(tasks, max_macros=16):
    """Mine repeated parameterized stack bodies from visible examples only."""
    records = {}
    for task in tasks:
        predicates = synthesize_self_edit_predicates(task["visible"], SAFE_OPS)
        for predicate in predicates:
            for stack in _stack_nodes(predicate["expr"]):
                instructions = stack["instructions"]
                # Turn a trailing modulo constant into a macro argument.  This
                # is an MDL-style abstraction over repeated visible programs.
                body = instructions
                if (len(instructions) >= 2 and instructions[-1].get("op") == "mod"
                        and instructions[-2].get("op") == "const"):
                    body = instructions[:-2]
                key = canonical(body)
                record = records.setdefault(key, {"body": body, "uses": 0, "source_tasks": set()})
                record["uses"] += 1
                record["source_tasks"].add(task["id"])
    ordered = sorted(records.values(), key=lambda row: (-row["uses"], len(canonical(row["body"])), canonical(row["body"])))
    library = []
    for index, record in enumerate(ordered[:max_macros]):
        body = record["body"]
        library.append({"macro_id": "m" + digest(body)[:12], "body": body,
                        "uses": record["uses"], "source_tasks": sorted(record["source_tasks"]),
                        "body_instructions": len(body), "inline_bytes": len(canonical(body)),
                        "call_bytes": 48})
    return library


def synthesize_macro_predicates(visible, library):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    other = observed - target
    if not target or not other:
        return []
    chars = sorted(observed, key=ord)
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    predicates, seen = [], set()
    for macro in library:
        for modulus in range(2, 10):
            expr = {"op": "macro", "name": macro["macro_id"], "body": macro["body"],
                    "modulus": modulus}
            values = tuple(evaluate_stack([{"op": "macro", "body": macro["body"], "modulus": modulus}], char)
                           for char in chars)
            for relation in ("eq", "lt", "ge"):
                for constant in range(0, 10):
                    predicate = {"op": relation, "left": expr, "right": constant,
                                 "macro_id": macro["macro_id"]}
                    mask = 0
                    for index, value in enumerate(values):
                        result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                        if result:
                            mask |= 1 << index
                    if mask == target_mask:
                        final = predicate
                    elif mask == other_mask:
                        final = {"op": "not", "arg": predicate, "macro_id": macro["macro_id"]}
                    else:
                        continue
                    key = canonical(final)
                    if key not in seen:
                        seen.add(key)
                        predicates.append({"kind": "ord_expr", "expr": final,
                                           "complexity": len(key), "macro_id": macro["macro_id"],
                                           "macro_source": "mined_visible_only"})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]
