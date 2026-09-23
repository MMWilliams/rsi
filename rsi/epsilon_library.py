"""Mine hidden-on-visible transitions revealed by active CEGIS episodes."""

from __future__ import annotations

from collections import Counter

from .common import ROOT  # noqa: F401 - installs the pinned vendor import path
from dsl import Concat, render, render_atom, run
from parse import parse


def mine_epsilon_macros(active_programs: list[tuple[str, list[list[str]], list[list[str]]]],
                        max_library: int = 32, max_length: int = 3, min_frequency: int = 1) -> dict:
    """Extract fragments empty on all visible examples but useful on hidden ones."""
    counts: Counter[str] = Counter()
    for program_text, visible, hidden in active_programs:
        parsed = parse(program_text)
        atoms = tuple(parsed.atoms)
        seen: set[str] = set()
        for length in range(1, min(max_length, len(atoms)) + 1):
            for start in range(len(atoms) - length + 1):
                fragment = Concat(atoms[start:start + length])
                visible_values = [run(fragment, inp) for inp, _ in visible]
                hidden_values = [run(fragment, inp) for inp, _ in hidden]
                if all(value == "" for value in visible_values) and any(hidden_values):
                    seen.add(render(fragment))
        for fragment in seen:
            counts[fragment] += 1
    eligible = [(fragment, count) for fragment, count in counts.items() if count >= min_frequency]
    eligible.sort(key=lambda row: (-row[1], -len(parse(row[0]).atoms), row[0]))
    selected = eligible[:max_library]
    return {"macros": [fragment for fragment, _ in selected],
            "counts": {fragment: count for fragment, count in selected},
            "source_programs": len(active_programs),
            "candidate_macros": len(counts),
            "eligible_macros": len(eligible),
            "parameters": {"max_library": max_library, "max_length": max_length, "min_frequency": min_frequency}}
