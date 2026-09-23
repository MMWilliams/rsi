from rsi.epsilon_library import mine_epsilon_macros


def test_mine_epsilon_macros_keeps_only_hidden_useful_fragments():
    rows = [("Concat(Sub(C1,C-3), Sub(C0,C1))",
             [["abcd", "a"]],
             [["abcde", "ab"]])]
    result = mine_epsilon_macros(rows)
    assert result["macros"] == ["Concat(Sub(C1,C-3))"]
