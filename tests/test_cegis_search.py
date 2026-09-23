from rsi.cegis_search import solve


def test_cegis_shortest_path_is_deterministic_and_visible_only():
    task = {"id": "t", "visible": [["a b c", "c"], ["x y z", "z"]]}
    proposal = "Concat(Sub(M(WORD,3,start),M(WORD,3,end)))"
    first = solve(task, proposals=[proposal])
    second = solve(task, proposals=[proposal])
    assert first == second
    assert first["visible_fit"] is True
    assert first["neural_transition_count"] >= 1
    assert first["program"].startswith("Concat(")


def test_cegis_keeps_epsilon_compatible_atoms():
    task = {"id": "t", "visible": [["a", "a-"], ["b", "b-"]]}
    result = solve(task)
    assert result["visible_fit"] is True
    assert result["program"].startswith("Concat(")


def test_cegis_accepts_verified_epsilon_macro_extension():
    task = {"id": "t", "visible": [["abcd", "ad"], ["wxyz", "wz"]]}
    result = solve(task, budget=32, max_atoms=4, epsilon_macros=["Concat(Sub(C1,C1))"])
    assert result["epsilon_transition_count"] == 1
    assert result["visible_fit"] is True


def test_version_space_accepts_retained_epsilon_macro():
    from rsi.version_space import enumerate_candidates

    task = {"id": "t", "visible": [["abcd", "ad"], ["wxyz", "wz"]]}
    rows = enumerate_candidates(task, max_atoms=6, budget=64, epsilon_macros=["Concat(Sub(C1,C-3))"])
    assert any("Sub(C1,C-3)" in row["program"] for row in rows)
