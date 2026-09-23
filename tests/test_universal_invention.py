from rsi.online_invention import invent_universal_ord_predicates
from rsi.semantic_invention import enumerate_semantic, evaluate_program


def test_universal_ordinal_grammar_combines_modular_and_bitwise_predicates():
    examples = [[chr(0x400) + chr(0x408), chr(0x400)],
                [chr(0x40b) + chr(0x413), chr(0x40b)],
                [chr(0x416) + chr(0x41e), chr(0x416)]]
    predicates = invent_universal_ord_predicates(examples)
    assert predicates
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)
