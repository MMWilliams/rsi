"""Typed low-level body editing for V77.

The editor exposes only serialized stack programs.  It can reconstruct a body
from primitive bit fragments, bit mixing, and bounded reducers; it never sees
hidden examples.  The retained macro library is passed as provenance so the
run can measure whether low-level invention is needed beyond replay.
"""

from __future__ import annotations

from .raw_stack_program import synthesize_raw_stack_programs


def synthesize_body_editor_predicates(visible, library, seed=0):
    predicates = synthesize_raw_stack_programs(
        visible, families=("bit_reduce", "bitmix"))
    trace = {"families": ["bit_reduce", "bitmix"], "candidate_count": len(predicates)}
    parent_ids = [macro["macro_id"] for macro in library]
    result = []
    for predicate in predicates:
        row = dict(predicate)
        row["macro_source"] = "body_editor"
        row["body_editor_seed"] = int(seed)
        row["parent_macro_ids"] = parent_ids
        row["body_editor_trace"] = trace
        result.append(row)
    return result
