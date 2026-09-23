"""Task-conditioned retrieval of verified synthesis programs."""

from __future__ import annotations

import re


def _bucket(value: float) -> int:
    return min(8, max(0, int(value) // 4))


def signature(visible: list[list[str]]) -> tuple:
    inputs = [str(pair[0]) for pair in visible]
    targets = [str(pair[1]) for pair in visible]
    combined = inputs + targets
    return (
        len(visible),
        _bucket(sum(map(len, inputs)) / max(1, len(inputs))),
        _bucket(sum(map(len, targets)) / max(1, len(targets))),
        int(any(" " in text for text in combined)),
        int(any(any(char.isdigit() for char in text) for text in combined)),
        int(any(any(char.isalpha() for char in text) for text in combined)),
        int(any(any(not char.isalnum() and not char.isspace() for char in text) for text in combined)),
        int(any("@" in text for text in combined)),
        int(any("-" in text or "/" in text for text in combined)),
        int(any(text.isupper() for text in combined if text)),
    )


def similarity(left: tuple, right: tuple) -> float:
    if not left or not right:
        return 0.0
    return sum(float(a == b) for a, b in zip(left, right)) / min(len(left), len(right))


def retrieve(memory: list[dict], visible: list[list[str]], limit: int = 8) -> list[str]:
    target = signature(visible)
    ranked = sorted(memory, key=lambda row: (-similarity(target, tuple(row["signature"])), row["task_id"]))
    output, seen = [], set()
    for row in ranked[:limit]:
        program = row.get("program", "")
        if program and program not in seen:
            output.append(program)
            seen.add(program)
    return output
