"""Symbolic search kernel augmented with visible-only neural fragment macros."""

from __future__ import annotations

from dsl import Concat, PosError, render, run
from parse import ParseError, parse

from .common import digest
from .search_diagnostic import solve as diagnostic_solve


def fragment_programs(proposals: list[str], visible: list[list[str]], max_atoms: int = 4) -> list[str]:
    """Extract contiguous proposal fragments that are compatible substrings.

    No hidden data are inspected. A fragment is admitted only when it produces
    a non-empty substring of every visible target, matching the host pool's
    pruning contract. The original proposal text is never trusted as a label.
    """
    found = set()
    for raw in proposals[:64]:
        text = raw.strip().splitlines()[0] if raw.strip() else ""
        try:
            program = parse(text)
            atoms = tuple(program.atoms)
        except (ValueError, ParseError, PosError, RecursionError):
            continue
        for start in range(len(atoms)):
            for stop in range(start + 1, min(len(atoms), start + max_atoms) + 1):
                fragment = Concat(atoms[start:stop])
                values = []
                valid = True
                for inp, target in visible:
                    try:
                        value = run(fragment, inp)
                    except (ValueError, PosError, RecursionError):
                        valid = False
                        break
                    if not value or value not in target:
                        valid = False
                        break
                    values.append(value)
                if valid and values:
                    found.add(render(fragment))
    return sorted(found)


def solve(task: dict, config: dict, budget: int, max_atoms: int = 4, macros: list[str] | None = None,
          proposals: list[str] | None = None) -> dict:
    visible = task["visible"]
    extra = fragment_programs(proposals or [], visible, max_atoms=max_atoms)
    merged = list(macros or [])
    for text in extra:
        if text not in merged:
            merged.append(text)
    result = diagnostic_solve(task, config, budget, max_atoms, merged, proposals, pool_mode="baseline")
    result["kernel"] = "neural_fragment_macro_v1"
    result["neural_fragment_count"] = len(extra)
    result["neural_fragments_sha256"] = digest(extra)
    return result
