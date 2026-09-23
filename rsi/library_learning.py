"""DreamCoder-style fragment library induction for the bounded DSL.

The learner sees labeled development programs, mines recurring contiguous
multi-atom fragments, and emits them as frozen macros.  It is deliberately
small and auditable: no hidden examples are consumed while solving admission
or final tasks, and the learner's entire output is serializable.
"""

from __future__ import annotations

from collections import Counter

from .common import ROOT  # noqa: F401 - installs the pinned vendor import path
from dsl import render_atom
from parse import parse


def mine_library(programs: list[str], max_library: int = 32, max_length: int = 3,
                 min_frequency: int = 2) -> dict:
    """Mine repeated contiguous fragments using a simple MDL proxy.

    A fragment's utility is frequency times the number of atoms saved by
    treating it as one reusable unit.  Each source program contributes at
    most once per fragment, preventing a single repeated atom sequence from
    dominating the library.
    """
    counts: Counter[str] = Counter()
    lengths: dict[str, int] = {}
    for text in programs:
        parsed = parse(text)
        atoms = tuple(render_atom(atom) for atom in parsed.atoms)
        seen: set[str] = set()
        for length in range(2, min(max_length, len(atoms)) + 1):
            for start in range(len(atoms) - length + 1):
                fragment = "Concat(" + ", ".join(atoms[start:start + length]) + ")"
                seen.add(fragment)
                lengths[fragment] = length
        for fragment in seen:
            counts[fragment] += 1

    eligible = [(fragment, count) for fragment, count in counts.items()
                if count >= min_frequency]
    eligible.sort(key=lambda row: (-(row[1] * (lengths[row[0]] - 1)), -row[1],
                                   -lengths[row[0]], row[0]))
    selected = eligible[:max_library]
    return {
        "macros": [fragment for fragment, _ in selected],
        "counts": {fragment: count for fragment, count in selected},
        "lengths": {fragment: lengths[fragment] for fragment, _ in selected},
        "source_programs": len(programs),
        "candidate_fragments": len(counts),
        "eligible_fragments": len(eligible),
        "parameters": {"max_library": max_library, "max_length": max_length,
                       "min_frequency": min_frequency},
    }
