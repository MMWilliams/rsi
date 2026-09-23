"""Raw-instruction stack synthesis for V71.

Unlike V70, this module never emits ``fold_bits``.  A bit reduction is
constructed explicitly from repeated ordinal loads, masks, shifts, and an
associative reducer.  The resulting programs are longer, but their behavior
is recoverable from primitive stack instructions alone.
"""

from __future__ import annotations

from .common import canonical
from .stack_program import evaluate_stack


RAW_FAMILIES = ("bit_reduce", "bitmix")


def _bit_reduce_program(width, reducer, modulus=None):
    instructions = []
    for position in range(width):
        instructions.extend(({"op": "load_ord"}, {"op": "const", "value": 1 << position},
                             {"op": "and"}, {"op": "const", "value": position}, {"op": "shr"}))
        if position:
            instructions.append({"op": reducer})
    if modulus is not None:
        instructions.extend(({"op": "const", "value": modulus}, {"op": "mod"}))
    return instructions


def _bitmix_program(mask, left_shift, right_shift, modulus):
    return [
        {"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
        {"op": "const", "value": left_shift}, {"op": "shl"},
        {"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
        {"op": "const", "value": right_shift}, {"op": "shr"}, {"op": "or"},
        {"op": "const", "value": mask}, {"op": "and"},
        {"op": "const", "value": modulus}, {"op": "mod"},
    ]


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def synthesize_raw_stack_programs(visible: list[list[str]], families=RAW_FAMILIES):
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    programs = []
    if "bit_reduce" in families:
        for width in (4, 5, 6, 7, 8):
            for reducer in ("xor", "add"):
                for modulus in (None, 2, 3, 4, 5):
                    programs.append(("bit_reduce", _bit_reduce_program(width, reducer, modulus)))
    if "bitmix" in families:
        for shift in range(1, 8):
            for modulus in range(2, 10):
                programs.append(("bitmix", _bitmix_program(255, shift, 8 - shift, modulus)))
    predicates, seen = [], set()
    for family, instructions in programs:
        values = tuple(evaluate_stack(instructions, char) for char in chars)
        for constant in range(0, 10):
            for relation in ("eq", "lt", "ge"):
                predicate = {"op": relation, "left": {"op": "stack", "instructions": instructions},
                             "right": constant}
                mask = 0
                for index, value in enumerate(values):
                    result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
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
                                       "complexity": len(key), "raw_stack_family": family})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]
