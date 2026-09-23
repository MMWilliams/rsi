import random

from rsi.evolving_domain import _raw_stack_input, _raw_stack_output
from rsi.meta_raw_stack import choose_candidate
from rsi.raw_stack_program import synthesize_raw_stack_programs
from rsi.stack_program import evaluate_stack


def test_raw_program_computes_bit_parity_without_fold_instruction():
    instructions = []
    for position in range(8):
        instructions.extend(({"op": "load_ord"}, {"op": "const", "value": 1 << position},
                             {"op": "and"}, {"op": "const", "value": position}, {"op": "shr"}))
        if position:
            instructions.append({"op": "xor"})
    assert evaluate_stack(instructions, chr(0xB01)) == ((0xB01 & 255).bit_count() % 2)
    assert all(instruction["op"] != "fold_bits" for instruction in instructions)


def test_raw_stack_synthesis_finds_bit_reduce_family():
    rng = random.Random(4)
    visible = []
    for index in range(40):
        text = _raw_stack_input(rng, "raw_xor_parity", "special_other", index)
        visible.append([text, _raw_stack_output(text, "raw_xor_parity", "special_other", True)])
    predicates = synthesize_raw_stack_programs(visible, ("bit_reduce",))
    assert predicates
    assert any(predicate.get("raw_stack_family") == "bit_reduce" for predicate in predicates)


def test_raw_architecture_selects_only_enabled_family():
    candidates = [
        {"program": "reduce", "raw_families": ["bit_reduce"], "raw_complexity": 2,
         "oracle_correct": True},
        {"program": "mix", "raw_families": ["bitmix"], "raw_complexity": 2,
         "oracle_correct": False},
    ]
    architecture = {"enabled_families": ["bit_reduce"], "max_complexity": 999,
                    "rank_mode": "shortest"}
    assert choose_candidate(candidates, architecture)["program"] == "reduce"
