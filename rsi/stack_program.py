"""Small typed stack-machine substrate for V70.

Programs use dictionaries rather than Python callables so they can be
serialized, mutated, replayed, and embedded in the existing ordinal AST
language.  The important reduction is generic ``fold_bits``; it is not a
named popcount primitive.
"""

from __future__ import annotations

from .common import canonical


def _encode_ord(code, encoding="identity"):
    if encoding == "identity":
        return code
    if encoding == "xor55":
        return code ^ 0x55
    if encoding == "affine5":
        return (5 * code + 17) & 0xff
    if encoding == "rotate3":
        value = code & 0xff
        return ((value << 3) | (value >> 5)) & 0xff
    if encoding == "bit_reverse":
        value = code & 0xff
        return int(f"{value:08b}"[::-1], 2)
    raise ValueError(f"unknown code-point encoding: {encoding}")


def evaluate_stack(instructions: list[dict], char: str):
    stack = []
    for instruction in instructions:
        op = instruction["op"]
        if op == "load_ord":
            stack.append(_encode_ord(ord(char), instruction.get("encoding", "identity")))
        elif op == "const":
            stack.append(int(instruction["value"]))
        elif op == "not":
            stack.append(~stack.pop())
        elif op == "macro":
            value = evaluate_stack(instruction["body"], char)
            if instruction.get("modulus") is not None:
                value %= int(instruction["modulus"])
            stack.append(value)
        elif op in ("add", "sub", "mul", "xor", "and", "or", "shl", "shr", "mod"):
            right, left = stack.pop(), stack.pop()
            if op == "add":
                stack.append(left + right)
            elif op == "sub":
                stack.append(left - right)
            elif op == "mul":
                stack.append(left * right)
            elif op == "xor":
                stack.append(left ^ right)
            elif op == "and":
                stack.append(left & right)
            elif op == "or":
                stack.append(left | right)
            elif op == "shl":
                stack.append(left << right)
            elif op == "shr":
                stack.append(left >> right)
            else:
                stack.append(left % right)
        elif op == "fold_bits":
            value = int(stack.pop())
            width = int(instruction["width"])
            mapped = []
            for position in range(width):
                bit = (value >> position) & 1
                mapped.append(1 - bit if instruction["map"] == "invert_bit" else bit)
            if instruction["reduce"] == "add":
                stack.append(sum(mapped))
            elif instruction["reduce"] == "xor":
                result = 0
                for bit in mapped:
                    result ^= bit
                stack.append(result)
            elif instruction["reduce"] == "or":
                stack.append(int(any(mapped)))
            else:
                raise ValueError("unknown fold reducer")
        else:
            raise ValueError(f"unknown stack instruction: {op}")
    if len(stack) != 1:
        raise ValueError("stack program did not leave one value")
    return stack[0]


def _fold_program(mask, width, mapping, reducer, modulus):
    return [
        {"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
        {"op": "fold_bits", "width": width, "map": mapping, "reduce": reducer},
        {"op": "const", "value": modulus}, {"op": "mod"},
    ]


def _bitmix_program(mask, left_shift, right_shift, modulus):
    return [
        {"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
        {"op": "const", "value": left_shift}, {"op": "shl"},
        {"op": "load_ord"}, {"op": "const", "value": mask}, {"op": "and"},
        {"op": "const", "value": right_shift}, {"op": "shr"}, {"op": "or"},
        {"op": "const", "value": mask}, {"op": "and"},
        {"op": "const", "value": modulus}, {"op": "mod"},
    ]


def synthesize_stack_programs(visible: list[list[str]], modes=("fold", "bitmix")) -> list[dict]:
    """Enumerate typed stack programs and retain visible target separators."""
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
    programs = []
    if "fold" in modes:
        for mask, width in ((15, 4), (31, 5), (63, 6), (127, 7), (255, 8)):
            for mapping in ("bit", "invert_bit"):
                for reducer in ("add", "xor", "or"):
                    for modulus in range(2, 10):
                        programs.append(("fold", _fold_program(mask, width, mapping, reducer, modulus)))
    if "bitmix" in modes:
        for shift in range(1, 8):
            for modulus in range(2, 10):
                programs.append(("bitmix", _bitmix_program(255, shift, 8 - shift, modulus)))
    predicates = []
    seen = set()
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
                                       "complexity": len(key), "stack_family": family})
    return sorted(predicates, key=lambda row: (row["complexity"], canonical(row["expr"])))[:512]
