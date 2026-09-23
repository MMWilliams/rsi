from rsi.meta_grammar import (architecture_allows, candidate_complexity, candidate_operations,
                               choose_architecture_candidate)
from rsi.semantic_invention import render_span


def _candidate(program, complexity=164):
    return {"program": program, "grammar_ops": list(candidate_operations(program)),
            "grammar_complexity": complexity, "oracle_correct": True}


def test_meta_grammar_extracts_typed_operator_signature():
    expression = {"op": "mod", "arg": {"op": "div", "left": {"op": "mul",
                 "left": {"op": "ord"}, "right": 3}, "divisor": 5}, "modulus": 7}
    left = {"kind": "run", "ordinal": 1,
            "predicate": {"kind": "ord_expr", "complexity": 164,
                           "expr": expression}, "side": "start"}
    program = "Concat(" + render_span(left, {"kind": "end"}) + ")"
    assert candidate_operations(program) == ("div", "mod", "mul")
    assert candidate_complexity(program) == 164


def test_meta_grammar_filters_and_ranks_deterministically():
    candidates = [_candidate("short div mul"), _candidate("long div mul xor", 165)]
    architecture = {"enabled_ops": ["div", "mul"], "max_complexity": 164,
                    "rank_mode": "shortest"}
    assert architecture_allows(candidates[0], architecture)
    assert not architecture_allows(candidates[1], architecture)
    assert choose_architecture_candidate(candidates, architecture)["program"] == "short div mul"
