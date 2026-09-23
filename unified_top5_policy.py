"""Typed visible-only dispatcher for V67/V70/V72/V73/V86 components.

The caller declares the task lane. No hidden examples or oracle labels enter this policy.
"""
from __future__ import annotations

from rsi.generic_body_evolution import synthesize_encoding_adaptive_library_predicates
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from run_ast_v66 import _direct_ast_candidates
from run_policy_transfer import ARMS, SETS, select
from stitch_ten import source_candidates


def select_semantic(rows, weights):
    public_rows = [{key: value for key, value in row.items() if key != "oracle_correct"} for row in rows]
    return select(public_rows, SETS["top4_semantic"], weights)


def select_encoded(rows_by_source):
    source = "direct_grammar" if rows_by_source["direct_grammar"] else "adaptive_lineage"
    rows = rows_by_source[source]
    return (source, min(rows, key=lambda row: (len(row["program"]), row["program"]))) if rows else (source, None)


def predict(public_task, lane, *, semantic_weights, lineage_library, semantic_candidate_cap=8,
            adaptive_encodings=("identity", "xor55", "affine5", "rotate3")):
    """Return a program and source from visible examples and a declared task lane."""
    public = {"id": public_task["id"], "visible": public_task["visible"]}
    if lane == "semantic":
        rows = [row for arm in ARMS for row in source_candidates(public, arm, {}, semantic_candidate_cap)]
        chosen = select_semantic(rows, semantic_weights)
        return {"program": chosen["program"] if chosen else "", "source": chosen["source"] if chosen else "none"}
    if lane == "encoded":
        visible = public["visible"]
        direct = _direct_ast_candidates(public, synthesize_self_edit_predicates(visible, SAFE_OPS))
        adaptive = _direct_ast_candidates(public, synthesize_encoding_adaptive_library_predicates(
            visible, lineage_library, adaptive_encodings))
        source, chosen = select_encoded({"direct_grammar": direct, "adaptive_lineage": adaptive})
        return {"program": chosen["program"] if chosen else "", "source": source if chosen else "none"}
    raise ValueError(f"unknown lane: {lane}")
