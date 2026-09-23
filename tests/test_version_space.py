from rsi.version_space import enumerate_candidates


def test_version_space_retains_multiple_visible_equivalent_candidates():
    task = {"id": "t", "visible": [["abc", "a"], ["xyz", "x"]]}
    rows = enumerate_candidates(task, limit=8, state_beam=8)
    assert rows
    assert len({row["program"] for row in rows}) >= 2
    assert all(row["program"].startswith("Concat(") for row in rows)
