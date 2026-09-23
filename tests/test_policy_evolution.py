import random

from rsi.search import BASE_CONFIG
from run_policy_evolution import mutate, rank


def test_policy_mutation_stays_inside_search_contract():
    policy = mutate(BASE_CONFIG, random.Random(17), 0.25)
    assert set(policy) == set(BASE_CONFIG)
    assert all(0.0 < value for value in policy.values())


def test_policy_rank_prefers_coverage_then_selection_then_cost():
    assert rank({"coverage64": 2, "selected_correct": 1, "expansions": 5, "generated_nodes": 5}) > rank({"coverage64": 1, "selected_correct": 5, "expansions": 1, "generated_nodes": 1})
