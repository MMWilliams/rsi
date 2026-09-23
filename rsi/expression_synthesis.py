"""Generic typed expression synthesis for V64.

The solver receives one expression grammar and searches its parameter space;
there are no separate modulus, bitwise, or threshold controller arms.
"""

from __future__ import annotations

from .common import canonical
from .semantic_invention import _char_predicate


def _aligned_classes(visible):
    target_chars, observed_chars = set(), set()
    for text, target in visible:
        observed_chars.update(text)
        if text.startswith(target) or text.endswith(target):
            target_chars.update(target)
    return target_chars, observed_chars - target_chars, observed_chars


def _eq(left, right):
    return {"op": "eq", "left": left, "right": right}


def _ord():
    return {"op": "ord"}


def _candidate_expressions(observed):
    ordinal = _ord()
    expressions = []
    max_modulus = min(20, max(2, max(ord(char) for char in observed) - min(ord(char) for char in observed) + 1))
    for modulus in range(2, max_modulus + 1):
        residue = {"op": "mod", "arg": ordinal, "modulus": modulus}
        for value in range(modulus):
            expressions.append(_eq(residue, value))
    max_position = max(ord(char) for char in observed).bit_length()
    for position in range(max_position):
        bit = {"op": "bit", "arg": ordinal, "position": position}
        expressions.extend((_eq(bit, 0), _eq(bit, 1)))
    codes = sorted({ord(char) for char in observed})
    for left, right in zip(codes, codes[1:]):
        if right - left > 1:
            cut = left + 1
            expressions.extend(({"op": "lt", "left": ordinal, "right": cut},
                                {"op": "ge", "left": ordinal, "right": cut}))
    return expressions


def synthesize_ordinal_expressions(visible: list[list[str]], extra_expressions=None, compose: bool = True) -> list[dict]:
    """Infer executable predicates from a single generic ordinal grammar."""
    target_chars, other_chars, observed = _aligned_classes(visible)
    if not target_chars or not other_chars:
        return []
    chars = sorted(observed, key=ord)
    target_mask = sum(1 << index for index, char in enumerate(chars) if char in target_chars)
    other_mask = sum(1 << index for index, char in enumerate(chars) if char in other_chars)
    expressions = _candidate_expressions(observed) + list(extra_expressions or [])
    predicates = []
    for expr in expressions:
        mask = sum(1 << index for index, char in enumerate(chars) if _eval(expr, char))
        direct = mask == target_mask
        inverse = mask == other_mask
        if direct or inverse:
            final = {"op": "not", "arg": expr} if inverse else expr
            predicates.append({"kind": "ord_expr", "expr": final, "complexity": _complexity(final)})
    # Compose only atoms that are false on every observed negative character.
    # Truth masks make the search proportional to distinct observed behaviors,
    # rather than the square of the full arithmetic parameter space.
    if compose:
        masks = {}
        for expr in expressions:
            mask = sum(1 << index for index, char in enumerate(chars) if _eval(expr, char))
            if mask and not (mask & other_mask):
                masks.setdefault(mask, expr)
        target_only = sorted(masks.items())
        for left_mask, left in target_only:
            for right_mask, right in target_only:
                if left_mask >= right_mask or (left_mask | right_mask) != target_mask:
                    continue
                expr = {"op": "bool_or", "left": left, "right": right}
                predicates.append({"kind": "ord_expr", "expr": expr, "complexity": _complexity(expr)})
        negative_masks = {}
        for expr in expressions:
            mask = sum(1 << index for index, char in enumerate(chars) if _eval(expr, char))
            if mask and not (mask & target_mask):
                negative_masks.setdefault(mask, expr)
        for left_mask, left in sorted(negative_masks.items()):
            for right_mask, right in sorted(negative_masks.items()):
                if left_mask >= right_mask or (left_mask | right_mask) != other_mask:
                    continue
                expr = {"op": "not", "arg": {"op": "bool_or", "left": left, "right": right}}
                predicates.append({"kind": "ord_expr", "expr": expr, "complexity": _complexity(expr)})
    unique = {canonical(predicate["expr"]): predicate for predicate in predicates}
    return sorted(unique.values(), key=lambda predicate: (predicate["complexity"], canonical(predicate["expr"])))


def _eval(expr, char):
    op = expr.get("op")
    if op == "ord":
        return ord(char)
    if op == "mod":
        return _eval(expr["arg"], char) % expr["modulus"]
    if op == "bit":
        return (_eval(expr["arg"], char) >> expr["position"]) & 1
    if op in ("add", "sub", "mul", "xor", "and", "or"):
        left, right = _eval(expr["left"], char), _eval(expr["right"], char)
        return {"add": left + right, "sub": left - right, "mul": left * right,
                "xor": left ^ right, "and": left & right, "or": left | right}[op]
    if op == "div":
        return _eval(expr["left"], char) // expr["divisor"]
    if op == "shr":
        return _eval(expr["arg"], char) >> expr["position"]
    if op == "mask":
        return _eval(expr["arg"], char) & expr["mask"]
    if op in ("lt", "ge", "eq"):
        left, right = _eval(expr["left"], char), expr["right"]
        return {"lt": left < right, "ge": left >= right, "eq": left == right}[op]
    if op == "not":
        return not _eval(expr["arg"], char)
    if op in ("bool_or", "bool_and", "bool_xor"):
        left, right = bool(_eval(expr["left"], char)), bool(_eval(expr["right"], char))
        return {"bool_or": left or right, "bool_and": left and right,
                "bool_xor": left != right}[op]
    raise ValueError("unsupported synthesis expression")


def _complexity(expr):
    if not isinstance(expr, dict):
        return 1
    return 1 + sum(_complexity(value) for key, value in expr.items() if key in ("arg", "left", "right") and isinstance(value, dict))
