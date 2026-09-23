"""Failure-driven typed constructor invention for V69.

The proposer starts with a small legacy ordinal grammar.  When that grammar
cannot separate the visible target class, it synthesizes additional typed
constructors from generic bit-vector and number-theoretic reductions.  No
hidden family label is passed to the proposer.
"""

from __future__ import annotations

from .common import canonical
from .semantic_invention import _eval_ord_expr


NOVEL_CONSTRUCTORS = ("popcount", "parity", "rotl", "gcd")


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def _constants(chars):
    codes = [ord(char) for char in chars]
    values = set(range(0, 33)) | {37, 41, 43, 47, 53, 255}
    values.update(abs(right - left) for left, right in zip(codes, codes[1:]) if 1 < abs(right - left) <= 31)
    return sorted(value for value in values if value >= 0)


def _base_expressions(chars):
    ordinal = {"op": "ord"}
    constants = _constants(chars)
    expressions = [ordinal, {"op": "and", "left": ordinal, "right": 255}]
    # Failure-driven search deliberately widens the substrate in stages.  The
    # first stage uses a compact affine/bitwise basis; it does not replay the
    # quadratic V64 composition search after every failure.
    for multiplier in range(1, 6):
        for addend in (0, 1, 3, 7):
            affine = {"op": "add", "left": {"op": "mul", "left": ordinal, "right": multiplier},
                      "right": addend}
            expressions.extend((affine, {"op": "div", "left": affine, "divisor": 2 + (addend % 6)}))
    for constant in constants[:24]:
        expressions.extend(({"op": "xor", "left": ordinal, "right": constant},
                            {"op": "and", "left": ordinal, "right": constant}))
    return expressions


def _novel_expressions(chars, enabled):
    expressions = []
    for base in _base_expressions(chars):
        if "popcount" in enabled:
            count = {"op": "popcount", "arg": base}
            expressions.extend((count, {"op": "mod", "arg": count, "modulus": 2}))
        if "parity" in enabled:
            expressions.append({"op": "parity", "arg": base})
        if "rotl" in enabled:
            for shift in range(1, 8):
                expressions.append({"op": "rotl", "arg": {"op": "and", "left": base, "right": 255},
                                    "shift": shift, "width": 8})
        if "gcd" in enabled:
            for constant in (6, 10, 12, 15, 18, 20, 24, 30, 36, 42, 60):
                expressions.append({"op": "gcd", "left": base, "right": constant})
    return expressions


def synthesize_failure_driven_ast(visible: list[list[str]], enabled=None,
                                  legacy_predicates: list[dict] | None = None) -> list[dict]:
    """Propose predicates after a visible legacy-grammar failure.

    ``legacy_predicates`` is deliberately accepted as an explicit diagnostic:
    callers can record whether the prior grammar found a visible solution
    before opening the constructor-invention layer.
    """
    enabled = set(enabled or NOVEL_CONSTRUCTORS)
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    expressions = _novel_expressions(chars, enabled)
    predicates = []
    seen = set()
    for expression in expressions:
        values = tuple(_eval_ord_expr(expression, char) for char in chars)
        for constant in _constants(chars):
            for op in ("eq", "lt", "ge"):
                predicate = {"op": op, "left": expression, "right": constant}
                mask = 0
                for index, value in enumerate(values):
                    result = value == constant if op == "eq" else value < constant if op == "lt" else value >= constant
                    if result:
                        mask |= 1 << index
                if mask == target_mask:
                    final = predicate
                elif mask == other_mask:
                    final = {"op": "not", "arg": predicate}
                else:
                    continue
                key = canonical(final)
                if key not in seen:
                    seen.add(key)
                    predicates.append({"kind": "ord_expr", "expr": final,
                                       "complexity": len(key), "failure_driven": True})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]
