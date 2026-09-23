"""Visible-example operator invention for V59."""

from __future__ import annotations

import math


def invent_char_set_predicates(visible: list[list[str]]) -> list[dict]:
    """Invent two character-set predicates from visible target alignment."""
    target_chars = set()
    observed_chars = set()
    for text, target in visible:
        observed_chars.update(text)
        if text.startswith(target):
            target_chars.update(target)
        elif text.endswith(target):
            target_chars.update(target)
    other_chars = observed_chars - target_chars
    predicates = []
    for values in (target_chars, other_chars):
        if values:
            predicates.append({"kind": "char_set", "values": sorted(values)})
    return predicates


def invent_ord_mod_predicates(visible: list[list[str]], max_modulus: int = 8) -> list[dict]:
    """Synthesize modular ordinal predicates that generalize beyond seen glyphs."""
    target_chars = set()
    observed_chars = set()
    for text, target in visible:
        observed_chars.update(text)
        if text.startswith(target) or text.endswith(target):
            target_chars.update(target)
    other_chars = observed_chars - target_chars
    predicates = []
    for modulus in range(2, max_modulus + 1):
        for residue in range(modulus):
            direct = (target_chars and other_chars and
                      all(ord(char) % modulus == residue for char in target_chars) and
                      all(ord(char) % modulus != residue for char in other_chars))
            inverse = (target_chars and other_chars and
                       all(ord(char) % modulus != residue for char in target_chars) and
                       all(ord(char) % modulus == residue for char in other_chars))
            if direct or inverse:
                predicates.append({"kind": "ord_mod", "modulus": modulus, "residue": residue,
                                   "invert": bool(inverse)})
    return predicates


def invent_divisor_mod_predicates(visible: list[list[str]]) -> list[dict]:
    """Infer modular predicates from observed ordinal-difference divisors."""
    target_chars = set()
    observed_chars = set()
    for text, target in visible:
        observed_chars.update(text)
        if text.startswith(target) or text.endswith(target):
            target_chars.update(target)
    other_chars = observed_chars - target_chars
    differences = []
    ordered_target = sorted(target_chars, key=ord)
    ordered_other = sorted(other_chars, key=ord)
    for group in (ordered_target, ordered_other):
        for left, right in zip(group, group[1:]):
            difference = abs(ord(right) - ord(left))
            if difference > 1:
                differences.append(difference)
    moduli = set()
    for difference in differences:
        moduli.add(difference)
        for divisor in range(2, math.isqrt(difference) + 1):
            if difference % divisor == 0:
                moduli.add(divisor)
                moduli.add(difference // divisor)
    predicates = []
    for modulus in sorted(moduli):
        for residue in range(modulus):
            direct = (target_chars and other_chars and
                      all(ord(char) % modulus == residue for char in target_chars) and
                      all(ord(char) % modulus != residue for char in other_chars))
            inverse = (target_chars and other_chars and
                       all(ord(char) % modulus != residue for char in target_chars) and
                       all(ord(char) % modulus == residue for char in other_chars))
            if direct or inverse:
                predicates.append({"kind": "ord_mod", "modulus": modulus, "residue": residue,
                                   "invert": bool(inverse)})
    return predicates


def invent_bit_predicates(visible: list[list[str]]) -> list[dict]:
    """Synthesize a bit-position predicate from visible target alignment."""
    target_chars = set()
    observed_chars = set()
    for text, target in visible:
        observed_chars.update(text)
        if text.startswith(target) or text.endswith(target):
            target_chars.update(target)
    other_chars = observed_chars - target_chars
    if not target_chars or not other_chars:
        return []
    max_position = max(ord(char) for char in observed_chars).bit_length()
    predicates = []
    for position in range(max_position):
        direct = (all(((ord(char) >> position) & 1) == 1 for char in target_chars) and
                  all(((ord(char) >> position) & 1) == 0 for char in other_chars))
        inverse = (all(((ord(char) >> position) & 1) == 0 for char in target_chars) and
                   all(((ord(char) >> position) & 1) == 1 for char in other_chars))
        if direct or inverse:
            predicates.append({"kind": "ord_bit", "position": position, "invert": bool(inverse)})
    return predicates


def invent_universal_ord_predicates(visible: list[list[str]]) -> list[dict]:
    """Search one unified ordinal grammar rather than selecting a family arm."""
    predicates = invent_divisor_mod_predicates(visible) + invent_bit_predicates(visible)
    unique = {}
    for predicate in predicates:
        key = tuple(sorted(predicate.items()))
        unique[key] = predicate
    return [unique[key] for key in sorted(unique)]
