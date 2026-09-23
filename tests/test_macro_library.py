import random

from rsi.evolving_domain import _self_edit_input, _self_edit_output
from rsi.macro_library import mine_macro_library, synthesize_macro_predicates
from rsi.macro_composition import synthesize_composed_macro_predicates
from rsi.typed_body_editor import synthesize_body_editor_predicates
from rsi.internal_body_mutation import mutate_body
from rsi.lineage_library import evolve_lineage_library
from rsi.credit_lineage import evolve_credit_lineage
from rsi.internal_body_mutation import _rotate_body
from rsi.generic_body_evolution import enumerate_hierarchical_bodies
from rsi.stack_program import evaluate_stack
from rsi.meta_macro import choose_candidate
from rsi.semantic_invention import _eval_ord_expr


def test_macro_expression_replays_body_with_modulus():
    body = [{"op": "load_ord"}, {"op": "const", "value": 15}, {"op": "and"}]
    assert _eval_ord_expr({"op": "macro", "body": body, "modulus": 5}, "A") == (ord("A") & 15) % 5


def test_visible_only_macro_mining_produces_replayable_predicate():
    rng = random.Random(7)
    texts = [_self_edit_input(rng, "grammar_not", "special_other", index) for index in range(12)]
    visible = [[text, _self_edit_output(text, "grammar_not", "special_other", True)] for text in texts]
    task = {"id": "synthetic", "visible": visible}
    library = mine_macro_library([task], max_macros=4)
    assert library
    predicates = synthesize_macro_predicates(visible, library)
    assert predicates and predicates[0]["macro_id"] == library[0]["macro_id"]


def test_macro_arm_does_not_select_direct_or_legacy_candidates():
    candidates = [
        {"program": "legacy", "macro_source": "legacy", "macro_complexity": 1},
        {"program": "direct", "macro_source": "direct_grammar", "macro_complexity": 1},
        {"program": "macro", "macro_source": "mined_visible_only", "macro_ids": ["m"], "macro_complexity": 2},
    ]
    assert choose_candidate(candidates, "legacy")["program"] == "legacy"
    assert choose_candidate(candidates, "direct")["program"] == "direct"
    assert choose_candidate(candidates, "macro")["program"] == "macro"


def test_composition_preserves_composed_source_and_can_be_selected():
    visible = [["A!", "A"], ["B!", "B"], ["!A", "A"], ["!B", "B"]]
    library = [{"macro_id": "a", "body": [{"op": "load_ord"}]},
               {"macro_id": "b", "body": [{"op": "load_ord"}]}]
    predicates = synthesize_composed_macro_predicates(visible, library)
    assert predicates and predicates[0]["macro_source"] == "composed_mutation"
    candidate = {"program": "x", "macro_source": "composed_mutation",
                 "macro_ids": ["a", "b"], "macro_complexity": 2}
    assert choose_candidate([candidate], "composed")["program"] == "x"


def test_body_editor_returns_serialized_typed_candidates():
    visible = [["A!", "A"], ["B!", "B"], ["!A", "A"], ["!B", "B"]]
    predicates = synthesize_body_editor_predicates(visible, [], seed=4)
    assert all(row["macro_source"] == "body_editor" for row in predicates)


def test_internal_mutation_keeps_parent_body_and_adds_balanced_grafts():
    body = [{"op": "load_ord"}, {"op": "const", "value": 15}, {"op": "and"}]
    variants = mutate_body(body, max_variants=40, reserve_grafts=True)
    assert variants[0][1] == "identity"
    assert any(edit.startswith("const:") for _body, edit in variants)
    assert any(edit.startswith("graft:") for _body, edit in variants)


def test_lineage_library_preserves_parent_ids():
    base = [{"macro_id": "parent", "body": [{"op": "load_ord"}], "uses": 1,
             "source_tasks": [], "body_instructions": 1, "inline_bytes": 20, "call_bytes": 48}]
    evolved, events = evolve_lineage_library([], base, max_library=4)
    assert [row["macro_id"] for row in evolved] == ["parent"]
    assert events == []


def test_credit_lineage_requires_multiple_support_tasks():
    base = [{"macro_id": "parent", "body": [{"op": "load_ord"}], "uses": 1,
             "source_tasks": [], "body_instructions": 1, "inline_bytes": 20, "call_bytes": 48}]
    evolved, events = evolve_credit_lineage([], base, generations=2, min_support=2)
    assert evolved == base
    assert events == [{"generation": 1, "parent_library_size": 1, "candidate_children": 0,
                       "eligible_children": 0, "children_added": [], "library_size": 1,
                       "min_support": 2}]


def test_rotate_body_is_balanced_and_exact_on_eight_bits():
    value = evaluate_stack(_rotate_body(), chr(65))
    assert value == (((65 << 3) | (65 >> 5)) & 255)


def test_hierarchical_generic_search_reaches_deeper_typed_bodies():
    rows = enumerate_hierarchical_bodies(list("AB!"), max_nodes=11,
                                         max_states_per_size=8,
                                         target={"A", "B"}, other={"!"})
    assert rows and max(row["nodes"] for row in rows) == 11
    assert all(row["body"][-1]["op"] in {"add", "sub", "mul", "xor", "and", "or", "shl", "shr", "mod"}
               for row in rows if row["nodes"] > 1)
