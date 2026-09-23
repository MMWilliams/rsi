import json

from rsi.common import ROOT, digest
from rsi.search import solve as original
from rsi.search_reopen import solve


def fixture():
    return json.loads((ROOT / "tests/fixtures/macro-cheaper-route.json").read_text())


def test_later_cheaper_macro_route_replaces_first_arrival_cost():
    case = fixture()
    args = (case["task"], case["config"], case["budget"], case["max_atoms"], case["macros"], [])
    assert original(*args) == case["recorded_result"]
    details = {}
    result = solve(*args, diagnostics=details)
    # Observed old route cost 2.55; declared macro cost is 25% lower.
    assert abs(details["best_costs"]["Concat(' ', '/')"] - 1.9125) < 1e-12
    assert details["reopened_states"] >= 1
    assert result["program"] != case["recorded_result"]["program"]


def test_reopening_replays_exactly_and_certifies_extended_payload():
    case = fixture()
    args = (case["task"], case["config"], case["budget"], case["max_atoms"], case["macros"], [])
    left, right = solve(*args), solve(*args)
    assert left == right
    assert digest({k: v for k, v in left.items() if k != "replay_sha256"}) == left["replay_sha256"]


def test_primitive_only_search_keeps_the_existing_result_and_trace():
    case = fixture()
    args = (case["task"], case["config"], case["budget"], case["max_atoms"], [], [])
    old, new = original(*args), solve(*args)
    ignored = {"replay_sha256", "kernel", "reopened_states"}
    assert {k: v for k, v in old.items() if k not in ignored} == {k: v for k, v in new.items() if k not in ignored}
    assert new["reopened_states"] == 0
