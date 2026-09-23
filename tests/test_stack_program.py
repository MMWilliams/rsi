import random

from rsi.evolving_domain import _stack_input, _stack_output
from rsi.meta_stack import choose_candidate
from rsi.stack_program import evaluate_stack, synthesize_stack_programs


def test_generic_fold_reconstructs_bit_count_parity_without_named_operator():
    program = [
        {"op": "load_ord"}, {"op": "const", "value": 255}, {"op": "and"},
        {"op": "fold_bits", "width": 8, "map": "bit", "reduce": "add"},
        {"op": "const", "value": 2}, {"op": "mod"},
    ]
    assert evaluate_stack(program, chr(0xA01)) == ((0xA01 & 255).bit_count() % 2)


def test_stack_synthesis_transfers_fold_family_on_visible_examples():
    rng = random.Random(3)
    visible = []
    for index in range(40):
        text = _stack_input(rng, "fold_parity", "special_other", index)
        visible.append([text, _stack_output(text, "fold_parity", "special_other", True)])
    predicates = synthesize_stack_programs(visible, ("fold",))
    assert predicates
    assert any(predicate.get("stack_family") == "fold" for predicate in predicates)


def test_stack_architecture_filters_to_selected_family():
    candidates = [
        {"program": "fold", "stack_families": ["fold"], "stack_complexity": 2,
         "oracle_correct": True},
        {"program": "bitmix", "stack_families": ["bitmix"], "stack_complexity": 2,
         "oracle_correct": False},
    ]
    architecture = {"enabled_families": ["fold"], "max_complexity": 999,
                    "rank_mode": "shortest"}
    assert choose_candidate(candidates, architecture)["program"] == "fold"
