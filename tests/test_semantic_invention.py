from rsi.extended_banks import create_extended_banks
from rsi.semantic_invention import (evaluate_program, enumerate_semantic, induce_ord_range_predicates,
                                    induce_signature_predicates, parse_semantic, render_span)


def test_semantic_operator_roundtrip_and_hidden_correctness():
    program = 'Concat(After("-",1))'
    assert parse_semantic('After("-",1)') == ("after", "-", 1)
    examples = [["AA-17", "17"], ["BBBB-903", "903"], ["C-4", "4"]]
    assert evaluate_program(program, examples)
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("after",))
    assert rows and rows[0]["program"] == program


def test_shifted_bank_replay_is_deterministic():
    config = {"bank_seed": 9090, "bank_counts": {"train": 2, "final": 2},
              "visible_examples": 3, "hidden_examples": 4}
    first, first_meta = create_extended_banks(config)
    second, second_meta = create_extended_banks(config)
    assert first == second
    assert first_meta == second_meta


def test_generic_span_schema_recovers_variable_delimiter_slices():
    examples = [["AA-17", "AA"], ["BBBB-903", "BBBB"], ["C-4", "C"]]
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",))
    assert rows and rows[0]["semantic_atoms"] == 1
    assert evaluate_program(rows[0]["program"], examples)


def test_generic_span_schema_can_use_character_class_transitions():
    examples = [["AB12", "AB"], ["xyz903", "xyz"], ["Q7", "Q"]]
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",), include_transitions=True)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)


def test_generic_span_schema_can_use_run_predicates():
    examples = [["AB12", "AB"], ["xyz903", "xyz"], ["Q7", "Q"]]
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",), include_runs=True)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)


def test_induced_signature_predicates_transfer_without_named_classes():
    train = [["AB-17", "AB"], ["xyz-903", "xyz"], ["Q-4", "Q"]]
    predicates = induce_signature_predicates(train)
    assert predicates and all(predicate["kind"] == "category_family" for predicate in predicates)
    examples = [["AB12", "AB"], ["xyz903", "xyz"], ["Q7", "Q"]]
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)


def test_raw_ord_range_predicates_transfer_without_unicode_taxonomy():
    train = [["AB-17", "AB"], ["xyz-903", "xyz"], ["Q-4", "Q"]]
    predicates = induce_ord_range_predicates(train)
    assert {tuple((predicate["lo"], predicate["hi"])) for predicate in predicates} >= {(48, 57), (65, 122)}
    examples = [["AB12", "AB"], ["xyz903", "xyz"], ["Q7", "Q"]]
    rows = enumerate_semantic({"id": "x", "visible": examples}, operators=("span",),
                              induced_predicates=predicates)
    assert any(row["semantic_atoms"] and evaluate_program(row["program"], examples) for row in rows)
