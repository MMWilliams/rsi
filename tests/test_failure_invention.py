import math
import random

from rsi.evolving_domain import _novel_input, _novel_output
from rsi.failure_invention import synthesize_failure_driven_ast
from rsi.meta_constructor import choose_candidate
from rsi.semantic_invention import _eval_ord_expr


def test_typed_novel_operators_are_executable():
    char = chr(0x900)
    assert _eval_ord_expr({"op": "popcount", "arg": {"op": "and", "left": {"op": "ord"}, "right": 255}}, char) == (ord(char) & 255).bit_count()
    assert _eval_ord_expr({"op": "parity", "arg": {"op": "ord"}}, char) == ord(char).bit_count() % 2
    assert _eval_ord_expr({"op": "gcd", "left": {"op": "ord"}, "right": 30}, char) == math.gcd(ord(char), 30)


def test_failure_driven_layer_proposes_popcount_predicate():
    rng = random.Random(1)
    visible = []
    for index in range(40):
        text = _novel_input(rng, "popcount_parity", "special_other", index)
        visible.append([text, _novel_output(text, "popcount_parity", "special_other", True)])
    predicates = synthesize_failure_driven_ast(visible, enabled=("popcount",))
    assert predicates
    assert any("popcount" in str(predicate["expr"]) for predicate in predicates)


def test_constructor_architecture_can_retain_only_invented_family():
    candidates = [
        {"program": "legacy", "constructor_ops": [], "constructor_complexity": 1,
         "oracle_correct": False},
        {"program": "popcount", "constructor_ops": ["popcount"], "constructor_complexity": 2,
         "oracle_correct": True},
    ]
    architecture = {"enabled_constructors": ["popcount"], "max_complexity": 999,
                    "rank_mode": "novelty"}
    assert choose_candidate(candidates, architecture)["program"] == "popcount"
