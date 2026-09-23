from rsi.meta_search import cost_frontier, map_elites_frontier, novelty_cost_frontier


def candidates():
    return [
        {"program": "Concat(ConstStr('a'))", "cost": 1.0, "source": "baseline", "visible_outputs": ["a"]},
        {"program": "Concat(SubStr(CPos(0), CPos(1)))", "cost": 2.0, "source": "partial", "visible_outputs": ["a"]},
        {"program": "Concat(Case('upper', SubStr(CPos(0), CPos(1))))", "cost": 3.0, "source": "partial", "visible_outputs": ["a"]},
    ]


def test_portfolio_selectors_are_visible_only_and_bounded():
    rows = candidates()
    assert cost_frontier(rows, 2)[0]["cost"] == 1.0
    assert len(map_elites_frontier(rows, 2)) == 2
    assert len(novelty_cost_frontier(rows, 2)) == 2
    assert all("oracle_correct" not in row for row in map_elites_frontier(rows, 2))
