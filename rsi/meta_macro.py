"""Replay metadata and selection for mined macros."""

from __future__ import annotations

import json

from .common import canonical
from .invented_space import _split_atoms
from .semantic_invention import parse_span


def _walk(node, ids):
    if isinstance(node, dict):
        if isinstance(node.get("macro_id"), str):
            ids.add(node["macro_id"])
        for value in node.values():
            _walk(value, ids)
    elif isinstance(node, list):
        for value in node:
            _walk(value, ids)


def macro_ids(program):
    ids = set()
    if program.startswith("Concat(") and program.endswith(")"):
        for atom in _split_atoms(program[7:-1]):
            span = parse_span(atom)
            if span is not None:
                for boundary in span:
                    _walk(boundary.get("predicate"), ids)
    return tuple(sorted(ids))


def annotate_candidates(candidates):
    result = []
    for candidate in candidates:
        row = dict(candidate)
        row["macro_ids"] = list(macro_ids(candidate["program"]))
        if row["macro_ids"] and row.get("macro_source") not in ("composed_mutation", "lineage_library", "credit_lineage", "encoding_adaptive_lineage"):
            row["macro_source"] = "mined_visible_only"
        else:
            row["macro_source"] = row.get("macro_source", "legacy")
        row["macro_complexity"] = len(candidate["program"])
        result.append(row)
    return result


def choose_candidate(candidates, arm):
    if arm == "macro":
        eligible = [candidate for candidate in candidates if candidate.get("macro_ids")]
    elif arm == "direct":
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == "direct_grammar"]
    elif arm == "composed":
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == "composed_mutation"]
    elif arm == "body_editor":
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == "body_editor"]
    elif arm == "lineage":
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == "lineage_library"]
    elif arm == "credit_lineage":
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == "credit_lineage"]
    elif arm == "specialist_portfolio":
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") in ("direct_grammar", "encoding_adaptive_lineage")]
    elif arm in ("generic_body_evolution", "generic_lineage", "encoding_adaptive_lineage"):
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == arm]
    else:
        eligible = [candidate for candidate in candidates
                    if candidate.get("macro_source") == "legacy"]
    return min(eligible, key=lambda candidate: (candidate["macro_complexity"], canonical(candidate["program"]))) if eligible else None
