from rsi.online_invention import invent_divisor_mod_predicates
from rsi.semantic_invention import enumerate_semantic, evaluate_program


def test_divisor_invention_discovers_modulus_outside_fixed_small_bound():
    examples = [[chr(1000) + chr(1001), chr(1000)],
                [chr(1011) + chr(1012), chr(1011)],
                [chr(1022) + chr(1023), chr(1022)]]
    predicates = invent_divisor_mod_predicates(examples)
    assert any(predicate["modulus"] == 11 for predicate in predicates)
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)
