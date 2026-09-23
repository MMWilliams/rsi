"""Reflective character-predicate discovery for V58."""

from __future__ import annotations


def discover_reflective_predicates(visible: list[list[str]]) -> list[dict]:
    """Discover boolean character methods without naming their semantics.

    The runtime object model is treated as a searchable primitive library. A
    method is retained only if it is callable on characters, returns a Boolean,
    and is nonconstant on the observed stream.
    """
    chars = [char for text, _target in visible for char in text]
    predicates = []
    for name in sorted(dir("")):
        if not name.startswith("is"):
            continue
        values = []
        valid = True
        for char in chars:
            method = getattr(char, name, None)
            if not callable(method):
                valid = False
                break
            try:
                value = method()
            except (AttributeError, TypeError, ValueError):
                valid = False
                break
            if type(value) is not bool:
                valid = False
                break
            values.append(value)
        if valid and values and any(values) and not all(values):
            predicates.append({"kind": "method", "name": name})
    return predicates
