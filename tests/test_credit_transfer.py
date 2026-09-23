import random

from credit_transfer import scrambled_paired_table, table_from_v10
from rsi.operators import initial_catalog, select


def _pairs():
    return [
        {"edit": "absolute_cost_down", "measurement_n": 16, "immediate": 0,
         "total_descendant": 0, "later_improvement": 2},
        {"edit": "absolute_cost_down", "measurement_n": 16, "immediate": 0,
         "total_descendant": 0, "later_improvement": 2},
        {"edit": "absolute_cost_up", "measurement_n": 16, "immediate": 1,
         "total_descendant": 0, "later_improvement": 0},
    ]


def test_credit_tables_keep_immediate_and_later_quantities_separate():
    immediate = table_from_v10(_pairs(), "immediate_only")
    paired = table_from_v10(_pairs(), "paired_credit")
    assert immediate["absolute_cost_down"]["gain_sum"] == 0
    assert "paired_gain_sum" not in immediate["absolute_cost_down"]
    assert paired["absolute_cost_down"]["paired_gain_sum"] == 0.25


def test_selector_can_use_paired_credit_without_changing_immediate_effect():
    catalog = initial_catalog()
    table = {op["name"]: {"trials": 1, "beneficial": 0, "accepted": 0,
                           "gain_sum": 0.0, "paired_trials": 1,
                           "paired_gain_sum": 0.0} for op in catalog}
    table["absolute_cost_down"]["paired_gain_sum"] = 10.0
    trace = {}
    selected = select(catalog, table, random.Random(9), trace=trace,
                      credit_mode="paired_credit")
    assert selected["name"] == "absolute_cost_down"
    assert trace["credit_mode"] == "paired_credit"
    assert all(row["credit_mode"] == "paired_later_improvement" for row in trace["scores"])


def test_scrambling_preserves_records_but_changes_assignment():
    pairs = _pairs() * 4
    original = table_from_v10(pairs, "paired_credit")
    scrambled = scrambled_paired_table(pairs, 771)
    assert sorted(original.values(), key=str) == sorted(scrambled.values(), key=str)
    assert original != scrambled
