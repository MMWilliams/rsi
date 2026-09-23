from rsi.findings import append_finding, load_ledger
from rsi.research_frameworks import apply_overrides, factorial_design, latin_hypercube, pareto_front, thompson_beta, ucb1


def test_designs_and_overrides_are_reproducible():
    space = {"lr": {"values": [0.0001, 0.0002]}, "arm": {"values": ["a", "b"]}}
    assert len(factorial_design(space)) == 4
    lhs = latin_hypercube({"lr": {"low": 0.0, "high": 1.0}, "arm": {"values": ["a", "b"]}}, 8, 17)
    assert lhs == latin_hypercube({"lr": {"low": 0.0, "high": 1.0}, "arm": {"values": ["a", "b"]}}, 8, 17)
    assert apply_overrides({"optimizer": {"lr": 1}}, {"optimizer.lr": 2}) == {"optimizer": {"lr": 2}}


def test_adaptive_allocators_and_pareto_front():
    assert ucb1([2, 0], [1.0, 0.0]) == 1
    assert thompson_beta([2.0, 1.0], [1.0, 2.0], 17) in {0, 1}
    assert pareto_front([{"coverage": 2, "cost": 3}, {"coverage": 3, "cost": 4}, {"coverage": 1, "cost": 2}], ["coverage"]) == [
        {"coverage": 3, "cost": 4}
    ]


def test_findings_ledger_rejects_duplicates(tmp_path):
    path = tmp_path / "findings.json"
    row = {"id": "f1", "status": "observed", "claim": "example", "scope": "exploratory", "source": ["x.md"]}
    append_finding(path, row)
    assert load_ledger(path)["findings"] == [row]
    try:
        append_finding(path, row)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate findings must be rejected")
