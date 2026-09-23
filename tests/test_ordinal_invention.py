from rsi.online_invention import invent_ord_mod_predicates
from rsi.semantic_invention import enumerate_semantic, evaluate_program


def test_ordinal_predicate_invention_generalizes_beyond_seen_characters():
    examples = [["αγεβ", "αγε"], ["ηιβ", "ηι"], ["οσδ", "οσ"]]
    predicates = invent_ord_mod_predicates(examples)
    assert any(predicate["kind"] == "ord_mod" for predicate in predicates)
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)
