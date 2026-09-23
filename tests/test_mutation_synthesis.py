import random

from rsi.evolving_domain import _mutation_input, _mutation_output
from rsi.meta_mutation import choose_candidate
from rsi.mutation_synthesis import synthesize_mutated_stack_programs


def test_mutation_synthesis_finds_visible_counterexample_solution():
    rng = random.Random(5)
    visible = []
    for index in range(40):
        text = _mutation_input(rng, "mutation_xor_parity", "special_other", index)
        visible.append([text, _mutation_output(text, "mutation_xor_parity", "special_other", True)])
    predicates, trace = synthesize_mutated_stack_programs(visible, iterations=4, seed=5)
    assert predicates
    assert trace[-1]["exact_count"] > 0
    assert all("mutation_genome" in predicate for predicate in predicates)


def test_mutation_trace_records_population_progress():
    rng = random.Random(6)
    visible = []
    for index in range(40):
        text = _mutation_input(rng, "mutation_sum_mod5", "special_other", index)
        visible.append([text, _mutation_output(text, "mutation_sum_mod5", "special_other", True)])
    _predicates, trace = synthesize_mutated_stack_programs(visible, iterations=3, seed=6)
    assert [row["generation"] for row in trace] == [0, 1, 2, 3]
    assert all(row["population"] > 0 for row in trace)


def test_mutation_policy_filters_by_term_budget():
    candidates = [
        {"program": "short", "mutation_terms": 2, "mutation_complexity": 2,
         "oracle_correct": True},
        {"program": "long", "mutation_terms": 8, "mutation_complexity": 8,
         "oracle_correct": False},
    ]
    architecture = {"max_terms": 2, "rank_mode": "shortest"}
    assert choose_candidate(candidates, architecture)["program"] == "short"
