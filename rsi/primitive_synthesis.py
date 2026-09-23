"""Failure-driven primitive extension for V65."""

from __future__ import annotations

from .expression_synthesis import synthesize_ordinal_expressions


def invent_transform_expressions(visible: list[list[str]]) -> list[dict]:
    """Propose transform atoms, then let the generic synthesizer compose them."""
    ordinal = {"op": "ord"}
    extra = []
    for divisor in range(2, 9):
        quotient = {"op": "div", "left": ordinal, "divisor": divisor}
        for modulus in range(2, 9):
            reduced = {"op": "mod", "arg": quotient, "modulus": modulus}
            for residue in range(modulus):
                extra.append({"op": "eq", "left": reduced, "right": residue})
    gray = {"op": "xor", "left": ordinal, "right": {"op": "shr", "arg": ordinal, "position": 1}}
    for position in range(2, 8):
        extra.extend(({"op": "eq", "left": {"op": "bit", "arg": gray, "position": position}, "right": 0},
                      {"op": "eq", "left": {"op": "bit", "arg": gray, "position": position}, "right": 1}))
    for shift in range(1, 7):
        shifted = {"op": "shr", "arg": ordinal, "position": shift}
        field = {"op": "mask", "arg": shifted, "mask": 3}
        for value in range(4):
            extra.append({"op": "eq", "left": field, "right": value})
    return synthesize_ordinal_expressions(visible, extra_expressions=extra, compose=False)
