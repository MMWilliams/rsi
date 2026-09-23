"""Interactive CEGIS: resolve visible-equivalent hypotheses with oracle queries."""

from __future__ import annotations

from .common import ROOT, digest  # noqa: F401 - installs the pinned vendor import path

from dsl import PosError, run
from parse import ParseError, parse

from .version_space import enumerate_candidates
from .cegis_search import solve as cegis_solve
from .search import BASE_CONFIG


def active_solve(task: dict, oracle_examples: list[list[str]], macros: list[str] | None = None,
                 synthesize_constants: bool = False, max_queries: int = 8,
                 candidate_limit: int = 64) -> dict:
    candidates = enumerate_candidates({"id": task["id"], "visible": task["visible"]},
                                      macros=macros, synthesize_constants=synthesize_constants,
                                      limit=candidate_limit)
    remaining = list(candidates)
    queried = 0
    for inp, target in oracle_examples[:max_queries]:
        if len(remaining) <= 1:
            break
        kept = []
        for row in remaining:
            try:
                value = run(parse(row["program"]), inp)
            except (ValueError, ParseError, PosError, RecursionError):
                continue
            if value == target:
                kept.append(row)
        remaining = kept
        queried += 1
        if not remaining:
            break
    selected = remaining[0] if remaining else (candidates[0] if candidates else None)
    return {"program": selected["program"] if selected else "", "queries": queried,
            "initial_candidates": len(candidates), "remaining_candidates": len(remaining),
            "resolved": bool(selected and len(remaining) == 1)}


def counterexample_guided_solve(task: dict, oracle_examples: list[list[str]],
                                config: dict | None = None, budget: int = 512,
                                max_atoms: int = 6, macros: list[str] | None = None,
                                synthesize_constants: bool = True, max_queries: int = 2) -> dict:
    """Re-synthesize after oracle counterexamples instead of filtering one version space.

    This is an interactive CEGIS arm: hidden examples are environment feedback,
    not passive holdout labels.  Each query is the first deterministic oracle
    counterexample to the current visible-only hypothesis.
    """
    if max_queries < 0:
        raise ValueError("max_queries must be non-negative")
    examples = list(task["visible"])
    queried = []
    current = None
    for _ in range(max_queries + 1):
        current = cegis_solve({"id": task["id"], "visible": examples}, config or BASE_CONFIG,
                              budget, max_atoms, macros or [], [],
                              synthesize_constants=synthesize_constants)
        counterexample = None
        for pair in oracle_examples:
            if pair in examples:
                continue
            try:
                output = run(parse(current["program"]), pair[0])
            except (ValueError, ParseError, PosError, RecursionError):
                output = None
            if output != pair[1]:
                counterexample = pair
                break
        if counterexample is None or len(queried) >= max_queries:
            break
        examples.append(counterexample)
        queried.append(counterexample)
    result = dict(current or {})
    result["interactive"] = True
    result["queries"] = len(queried)
    result["examples_used"] = len(examples)
    result["counterexamples"] = queried
    result["repair_trace_sha256"] = digest(queried)
    result["replay_sha256"] = digest(result)
    return result
