"""A mutable executable grammar for V73.

The safe sandbox contains primitive stack instructions.  Grammar genomes decide
which instruction symbols are available to the proposer; programs themselves
are synthesized from behavior signatures and carry their required symbols in
the serialized predicate for replay.
"""

from __future__ import annotations

from .common import canonical
from .stack_program import evaluate_stack


SAFE_OPS = ("and", "shr", "xor", "add", "sub", "mul", "or", "not", "mod")


def _not_program(modulus):
    return [{"op": "load_ord"}, {"op": "const", "value": 255}, {"op": "and"},
            {"op": "not"}, {"op": "const", "value": 255}, {"op": "and"},
            {"op": "const", "value": modulus}, {"op": "mod"}], {"and", "not", "mod"}


def _nibble_program(modulus):
    return [{"op": "load_ord"}, {"op": "const", "value": 15}, {"op": "and"},
            {"op": "load_ord"}, {"op": "const", "value": 4}, {"op": "shr"},
            {"op": "const", "value": 15}, {"op": "and"}, {"op": "xor"},
            {"op": "const", "value": modulus}, {"op": "mod"}], {"and", "shr", "xor", "mod"}


def _subfold_program(modulus):
    instructions = []
    for position in range(8):
        instructions.extend(({"op": "load_ord"}, {"op": "const", "value": 1 << position},
                             {"op": "and"}, {"op": "const", "value": position}, {"op": "shr"}))
        if position:
            instructions.append({"op": "add"})
    instructions.extend(({"op": "const", "value": 1}, {"op": "add"},
                         {"op": "const", "value": modulus}, {"op": "mod"}))
    return instructions, {"and", "shr", "add", "mod"}


def _aligned(visible):
    target, observed = set(), set()
    for text, value in visible:
        observed.update(text)
        if text.startswith(value) or text.endswith(value):
            target.update(value)
    return target, observed - target, sorted(observed, key=ord)


def synthesize_self_edit_predicates(visible, enabled_ops=SAFE_OPS):
    target, other, chars = _aligned(visible)
    if not target or not other:
        return []
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other)
    programs = []
    for modulus in range(2, 10):
        programs.append(_not_program(modulus))
        programs.append(_nibble_program(modulus))
        programs.append(_subfold_program(modulus))
    predicates, seen = [], set()
    for instructions, required in programs:
        if not required <= set(enabled_ops):
            continue
        values = tuple(evaluate_stack(instructions, char) for char in chars)
        for relation in ("eq", "lt", "ge"):
            for constant in range(0, 10):
                predicate = {"op": relation, "left": {"op": "stack", "instructions": instructions},
                             "right": constant, "grammar_ops": sorted(required)}
                mask = 0
                for index, value in enumerate(values):
                    result = value == constant if relation == "eq" else value < constant if relation == "lt" else value >= constant
                    if result:
                        mask |= 1 << index
                if mask == target_mask:
                    final = predicate
                elif mask == other_mask:
                    final = {"op": "not", "arg": predicate, "grammar_ops": sorted(required | {"not"})}
                else:
                    continue
                key = canonical(final)
                if key not in seen:
                    seen.add(key)
                    predicates.append({"kind": "ord_expr", "expr": final,
                                       "complexity": len(key), "grammar_ops": sorted(required)})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]
