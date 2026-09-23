import random

from rsi.evolving_domain import _self_edit_input, _self_edit_output
from rsi.meta_self_edit import choose_candidate
from rsi.self_editing_grammar import SAFE_OPS, synthesize_self_edit_predicates
from rsi.stack_program import evaluate_stack


def test_sandbox_supports_dormant_not_instruction():
    program = [{"op": "load_ord"}, {"op": "const", "value": 255}, {"op": "and"},
               {"op": "not"}, {"op": "const", "value": 255}, {"op": "and"},
               {"op": "const", "value": 5}, {"op": "mod"}]
    assert evaluate_stack(program, chr(0xD01)) == (~(0xD01 & 255) & 255) % 5


def test_self_editing_grammar_proposes_enabled_operator_signature():
    rng = random.Random(7)
    visible = []
    for index in range(40):
        text = _self_edit_input(rng, "grammar_not", "special_other", index)
        visible.append([text, _self_edit_output(text, "grammar_not", "special_other", True)])
    predicates = synthesize_self_edit_predicates(visible, SAFE_OPS)
    assert predicates
    assert any("not" in predicate["grammar_ops"] for predicate in predicates)


def test_grammar_editor_filters_required_operations():
    candidates = [
        {"program": "old", "required_ops": ["and"], "grammar_complexity": 2,
         "oracle_correct": False},
        {"program": "new", "required_ops": ["and", "not"], "grammar_complexity": 3,
         "oracle_correct": True},
    ]
    architecture = {"enabled_ops": ["and", "not"], "max_complexity": 999,
                    "rank_mode": "novelty"}
    assert choose_candidate(candidates, architecture)["program"] == "new"
