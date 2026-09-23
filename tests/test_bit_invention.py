from rsi.online_invention import invent_bit_predicates
from rsi.semantic_invention import enumerate_semantic, evaluate_program


def test_bit_predicate_invention_generalizes_hidden_symbols():
    examples = [[chr(0x508) + chr(0x510), chr(0x508)],
                [chr(0x518) + chr(0x520), chr(0x518)],
                [chr(0x528) + chr(0x530), chr(0x528)]]
    predicates = invent_bit_predicates(examples)
    assert predicates
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)
