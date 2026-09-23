from rsi.cegis_search import solve


def test_visible_constant_synthesis_admits_multicharacter_separator():
    task = {"id": "separator", "visible": [["a", "- "], ["b", "- "]]}
    result = solve(task, synthesize_constants=True)
    assert result["visible_fit"] is True
    assert result["program"] == "Concat('- ')"
    assert result["constant_transition_count"] >= 1
