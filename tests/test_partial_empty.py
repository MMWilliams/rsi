from rsi.atom_pool_partial import atom_pool as partial_pool
from rsi.common import canonical
from rsi.search import BASE_CONFIG, atom_pool
from rsi.search_diagnostic import solve
from rsi.search_reachability import reachable
from rsi.search_reopen import solve as baseline


TASK = {"id": "sometimes-empty", "visible": [["abcd", "bc-"], ["ab", "-"], ["aXb", "X-"]]}


def test_partial_empty_piece_recovers_a_visible_solution_removed_by_old_filter():
    assert not reachable(TASK, [], pool_mode="baseline")["reachable"]
    assert reachable(TASK, [], pool_mode="partial_empty")["reachable"]
    old = solve(TASK, BASE_CONFIG, 128, macros=[], pool_mode="baseline")
    new = solve(TASK, BASE_CONFIG, 128, macros=[], pool_mode="partial_empty")
    assert not old["visible_fit"] and new["visible_fit"]
    assert new["visible_outputs"] == [value for _, value in TASK["visible"]]


def test_new_filter_keeps_old_pool_and_only_adds_partial_empty_vectors():
    old, _ = atom_pool(canonical(TASK["visible"]), "[]")
    new, _ = partial_pool(canonical(TASK["visible"]), "[]")
    old_by_atoms = {canonical(r["atoms"]): r for r in old}
    new_by_atoms = {canonical(r["atoms"]): r for r in new}
    assert old_by_atoms.keys() <= new_by_atoms.keys()
    assert all(new_by_atoms[k] == v for k, v in old_by_atoms.items())
    added = [v for k, v in new_by_atoms.items() if k not in old_by_atoms]
    assert added and all(any(v["values"]) and "" in v["values"] for v in added)
    assert all(any(v["values"]) for v in new)


def test_frontier_logging_preserves_baseline_output_and_is_deterministic():
    task = {"id": "simple", "visible": [["AB", "AB-"], ["CD", "CD-"], ["EF", "EF-"]]}
    details, repeated = {}, {}
    result = solve(task, BASE_CONFIG, 128, macros=[], diagnostics=details)
    assert result == baseline(task, BASE_CONFIG, 128, macros=[])
    assert solve(task, BASE_CONFIG, 128, macros=[], diagnostics=repeated) == result
    assert details == repeated
    assert details["frontier"][0]["program"] == result["program"]
    assert len({r["program"] for r in details["frontier"]}) == len(details["frontier"])
