"""Signature-indexed typed AST synthesis for V66."""

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


def _constants(chars):
    values = {0, 1, 2, 3, 4, 5, 7, 8, 11, 13, 16, 17, 31, 63, 85, 127}
    codes = [ord(char) for char in chars]
    values.update(abs(right - left) for left, right in zip(codes, codes[1:]) if 1 < abs(right - left) <= 31)
    return sorted(value for value in values if value >= 0)


def _numeric_layers(chars, max_depth=3, keep_per_signature=128):
    constants = _constants(chars)
    ordinal = {"op": "ord"}
    expressions = [ordinal]
    small = sorted(set(constants).intersection(set(range(0, 18))))
    for multiplier in range(1, 10):
        for addend in small:
            affine = {"op": "add", "left": {"op": "mul", "left": ordinal, "right": multiplier}, "right": addend}
            for divisor in range(2, 10):
                expressions.append({"op": "div", "left": affine, "divisor": divisor})
    for constant in constants:
        expressions.extend(({"op": "add", "left": ordinal, "right": constant},
                            {"op": "sub", "left": ordinal, "right": constant},
                            {"op": "mul", "left": ordinal, "right": constant},
                            {"op": "xor", "left": ordinal, "right": constant}))
    return expressions


def _op_path(expression):
    op = expression.get("op") if isinstance(expression, dict) else "const"
    child = expression.get("arg") if isinstance(expression, dict) and "arg" in expression else expression.get("left") if isinstance(expression, dict) else None
    return ((op,) + _op_path(child)) if isinstance(child, dict) else (op,)


def synthesize_general_ast(visible: list[list[str]], max_depth: int = 3) -> list[dict]:
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    predicates = []
    expressions = _numeric_layers(chars, max_depth=max_depth)
    constants = _constants(chars)
    for expression in expressions:
        views = [expression]
        views.extend({"op": "mod", "arg": expression, "modulus": modulus} for modulus in range(2, 10))
        views.extend({"op": "mask", "arg": {"op": "shr", "arg": expression, "position": shift}, "mask": 3}
                     for shift in range(1, 5))
        for view in views:
            values = tuple(_eval_ord_expr(view, char) for char in chars)
            for constant in constants:
                for op in ("eq", "lt", "ge"):
                    predicate = {"op": op, "left": view, "right": constant}
                    mask = 0
                    for index, value in enumerate(values):
                        result = value == constant if op == "eq" else value < constant if op == "lt" else value >= constant
                        if result:
                            mask |= 1 << index
                    if mask == target_mask:
                        predicates.append({"kind": "ord_expr", "expr": predicate,
                                           "complexity": len(canonical(predicate))})
                    elif mask == other_mask:
                        predicates.append({"kind": "ord_expr", "expr": {"op": "not", "arg": predicate},
                                           "complexity": len(canonical(predicate)) + 1})
    unique = {canonical(predicate["expr"]): predicate for predicate in predicates}
    return sorted(unique.values(), key=lambda predicate: (predicate["complexity"], canonical(predicate["expr"])))[:512]
