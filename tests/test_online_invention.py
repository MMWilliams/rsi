from rsi.online_invention import invent_char_set_predicates
from rsi.semantic_invention import enumerate_semantic, evaluate_program


def test_visible_examples_invent_character_set_operator():
    examples = [["αεηβγδ", "αεη"], ["ιουκλμ", "ιου"], ["ωαπρσ", "ωα"]]
    predicates = invent_char_set_predicates(examples)
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)
