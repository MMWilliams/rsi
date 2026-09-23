"""Compositional mutation of retained executable macros for V76."""

from __future__ import annotations

from .common import canonical
from .semantic_invention import _eval_ord_expr


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def _macro_expr(macro, modulus):
    return {"op": "macro", "name": macro["macro_id"], "body": macro["body"],
            "modulus": modulus, "macro_id": macro["macro_id"]}


def synthesize_composed_macro_predicates(visible, library, max_pairs=128):
    """Compose retained macros using only visible target-separation behavior."""
    target, other, chars = _aligned(visible)
    if not target or not other or not library:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    components = []
    for macro in library:
        for modulus in range(2, 10):
            components.append(_macro_expr(macro, modulus))
    # Include both ordered directions because subtraction and non-commutative
    # composition can express a useful relation in only one orientation.
    expressions = []
    for left in components:
        expressions.append((left, (left["macro_id"],)))
    pairs = 0
    for left in components:
        for right in components:
            if pairs >= max_pairs:
                break
            pairs += 1
            for op in ("add", "sub", "xor", "and", "or", "mul"):
                combined = {"op": op, "left": left, "right": right}
                for modulus in range(2, 10):
                    expressions.append(({"op": "mod", "arg": combined, "modulus": modulus},
                                        (left["macro_id"], right["macro_id"])))
        if pairs >= max_pairs:
            break
    predicates, seen = [], set()
    for expr, ids in expressions:
        values = tuple(_eval_ord_expr(expr, char) for char in chars)
        for relation in ("eq", "lt", "ge"):
            for constant in range(0, 10):
                mask = 0
                for index, value in enumerate(values):
                    result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                    if result:
                        mask |= 1 << index
                if mask == target_mask:
                    final = {"op": relation, "left": expr, "right": constant}
                elif mask == other_mask:
                    final = {"op": "not", "arg": {"op": relation, "left": expr, "right": constant}}
                else:
                    continue
                key = canonical(final)
                if key in seen:
                    continue
                seen.add(key)
                predicates.append({"kind": "ord_expr", "expr": final,
                                   "complexity": len(key), "macro_ids": sorted(set(ids)),
                                   "macro_source": "composed_mutation", "composition_depth": 2})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]
