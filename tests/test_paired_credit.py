"""Guard the meaning of paired later improvement and edit admission."""
from paired_credit import branch, effects
from rsi.operators import apply, initial_catalog
from rsi.search import BASE_CONFIG


def test_later_improvement_can_reverse_the_terminal_effect():
    # Edited branch wins at the end, but improves less after its start.
    row = effects(base_start=5, base_end=9, edited_start=8, edited_end=10)
    assert row == {"immediate": 3, "total_descendant": 1, "later_improvement": -2}
    assert row["total_descendant"] == row["immediate"] + row["later_improvement"]


def test_both_branches_receive_same_future_menu_and_real_admission_gate():
    catalog = {op["name"]: op for op in initial_catalog()}
    names = ["absolute_cost_down", "absolute_cost_up"]
    down, up = (apply(catalog[name], BASE_CONFIG) for name in names)
    banks = {"s1_development": [{"id": "d"}], "s1_admission": [{"id": "a"}]}
    calls = []
    def evaluate(tasks, state, label, split):
        calls.append((split, label, state))
        if split.endswith("development"):
            score = 2 if state == down else 1 if state == up else 0
        else:
            score = -1 if state == down else 0
        return {"id": label, "correct": score}
    run = branch(evaluate, banks, {"development_per_round": 1, "admission_per_round": 1},
                 1, BASE_CONFIG, "test", [names])
    decision = run["decisions"][0]
    assert decision["chosen_operator"] == "absolute_cost_down"
    assert decision["development_gain_count"] == 2
    assert decision["admission_gain_count"] == -1
    assert decision["reason"] == "admission_regression"
    assert not decision["accepted"]
    assert run["terminal_config"] == BASE_CONFIG
    assert len(calls) == 5
