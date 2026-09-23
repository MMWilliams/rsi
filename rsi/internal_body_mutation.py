"""Typed grow/edit mutations of retained stack bodies for V78."""

from __future__ import annotations

from itertools import product

from .common import canonical, digest
from .stack_program import evaluate_stack


EDIT_VALUES = (0, 1, 2, 3, 4, 5, 7, 8, 15, 31, 63, 127, 255)
BINARY_OPS = ("add", "sub", "mul", "xor", "and", "or", "shl", "shr")


def _graft(mask, shift, op):
    """A stack-balanced fragment that combines a parent result with raw bits."""
    return [{"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
            {"op": "const", "value": shift}, {"op": "shr"}, {"op": op}]


def _rotate_body(mask=255, left_shift=3, right_shift=5):
    """A stack-balanced two-branch rotate fragment."""
    return [{"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
            {"op": "const", "value": left_shift}, {"op": "shl"},
            {"op": "const", "value": mask}, {"op": "and"},
            {"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
            {"op": "const", "value": right_shift}, {"op": "shr"}, {"op": "or"}]


def mutate_body(body, max_variants=256, reserve_grafts=False, reserve_rotate=False):
    """Enumerate bounded typed edits, deduplicated by canonical body."""
    seen, variants = set(), []
    graft_budget = min(max(8, max_variants // 3), max_variants - 1) if reserve_grafts else 0
    rotate_budget = min(max(8, max_variants // 4), max_variants - 1 - graft_budget) if reserve_rotate else 0
    local_budget = max_variants - graft_budget - rotate_budget if (reserve_grafts or reserve_rotate) else max_variants

    def add(candidate, edit, limit=max_variants):
        key = canonical(candidate)
        if key not in seen and len(variants) < limit:
            seen.add(key)
            variants.append((candidate, edit))

    add(body, "identity")
    for index, instruction in enumerate(body):
        if len(variants) >= max_variants:
            break
        if instruction.get("op") == "const":
            for value in EDIT_VALUES:
                if value != instruction.get("value"):
                    candidate = [dict(item) for item in body]
                    candidate[index] = {"op": "const", "value": value}
                    add(candidate, f"const:{index}:{value}", local_budget)
        elif instruction.get("op") in BINARY_OPS:
            for op in BINARY_OPS:
                if op != instruction["op"]:
                    candidate = [dict(item) for item in body]
                    candidate[index] = {"op": op}
                    add(candidate, f"op:{index}:{op}", local_budget)

    if reserve_rotate:
        for mask, left_shift, right_shift in ((255, 3, 5), (255, 1, 7), (255, 2, 6),
                                               (127, 3, 5), (63, 2, 6)):
            add(_rotate_body(mask, left_shift, right_shift),
                f"replace:rotate:{mask}:{left_shift}:{right_shift}")
            if len(variants) >= max_variants:
                break
    # Grow the parent with a balanced raw-bit fragment.  This is the only
    # operation that can introduce a new data path into an existing body.
    for mask, shift, op in product((15, 31, 63, 127, 255), range(1, 8), ("xor", "or", "add")):
        add(body + _graft(mask, shift, op), f"graft:{mask}:{shift}:{op}")
        if len(variants) >= max_variants - rotate_budget:
            break
    return variants


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def synthesize_internal_mutation_predicates(visible, library, max_variants=256, reserve_grafts=False,
                                            reserve_rotate=False):
    """Select exact visible separators from mutated retained bodies."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    predicates, seen = [], set()
    for macro in library:
        for body, edit in mutate_body(macro["body"], max_variants=max_variants,
                                      reserve_grafts=reserve_grafts, reserve_rotate=reserve_rotate):
            try:
                raw_values = tuple(evaluate_stack(body, char) for char in chars)
            except (IndexError, ValueError, ZeroDivisionError):
                continue
            for modulus in range(2, 10):
                values = tuple(value % modulus for value in raw_values)
                for relation in ("eq", "lt", "ge"):
                    for constant in range(0, 10):
                        mask = 0
                        for index, value in enumerate(values):
                            result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                            if result:
                                mask |= 1 << index
                        if mask == target_mask:
                            final = {"op": relation, "left": {"op": "stack", "instructions": body},
                                     "right": constant}
                        elif mask == other_mask:
                            final = {"op": "not", "arg": {"op": relation,
                                     "left": {"op": "stack", "instructions": body},
                                     "right": constant}}
                        else:
                            continue
                        key = canonical(final)
                        if key in seen:
                            continue
                        seen.add(key)
                        predicates.append({"kind": "ord_expr", "expr": final,
                                           "complexity": len(key), "macro_source": "internal_mutation",
                                           "parent_macro_id": macro["macro_id"],
                                           "mutation_edit": edit, "mutation_body_digest": digest(body)})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]


def mine_successful_mutated_bodies(visible, library, max_variants=128, max_children=8,
                                   reserve_grafts=False, reserve_rotate=False):
    """Return visible-consistent child bodies without deleting their parents."""
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    found, seen = [], set()
    for macro in library:
        for body, edit in mutate_body(macro["body"], max_variants=max_variants,
                                      reserve_grafts=reserve_grafts, reserve_rotate=reserve_rotate):
            if body == macro["body"]:
                continue
            try:
                raw_values = tuple(evaluate_stack(body, char) for char in chars)
            except (IndexError, ValueError, ZeroDivisionError):
                continue
            for modulus in range(2, 10):
                values = tuple(value % modulus for value in raw_values)
                for constant in range(0, 10):
                    for relation in ("eq", "lt", "ge"):
                        mask = 0
                        for index, value in enumerate(values):
                            result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                            if result:
                                mask |= 1 << index
                        if mask not in (target_mask, other_mask):
                            continue
                        key = canonical(body)
                        if key not in seen:
                            seen.add(key)
                            found.append({"macro_id": "child" + digest(body)[:12], "body": body,
                                          "uses": 1, "source_tasks": [],
                                          "body_instructions": len(body),
                                          "inline_bytes": len(canonical(body)), "call_bytes": 48,
                                          "parent_macro_id": macro["macro_id"],
                                          "mutation_edit": edit})
                        break
                    else:
                        continue
                    break
                else:
                    continue
                break
            if len(found) >= max_children:
                return found
    return found
