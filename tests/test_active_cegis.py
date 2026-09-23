from audit_results import published_correct
from rsi.active_cegis import counterexample_guided_solve


def test_counterexample_guided_solver_replays_and_returns_verified_program():
    task = {"id": "active-test", "visible": [["abcd", "ad"], ["wxyz", "wz"], ["pqrs", "ps"]]}
    hidden = []
    result = counterexample_guided_solve(task, hidden, budget=128, max_atoms=4, max_queries=0)
    assert result["program"]
    assert result["replay_sha256"]
    assert published_correct(result["program"], task["visible"] + hidden)
