from rsi.automl_architecture import candidate_id, factorial_candidates, normalize, promotion_order


def test_factorial_space_is_unique_and_normalized():
    candidates = factorial_candidates()
    assert len(candidates) == 180
    assert len({row["id"] for row in candidates}) == 180
    assert all(row["id"] == candidate_id(row) for row in candidates)
    assert all((row["engine"] == "cegis" or not row["synthesize_constants"]) for row in candidates)


def test_promotion_keeps_forced_control_and_pareto_candidates():
    rows = [{"architecture": {"id": "slow", "budget": 512, "max_atoms": 6}, "correct": 8},
            {"architecture": {"id": "fast", "budget": 128, "max_atoms": 4}, "correct": 7},
            {"architecture": {"id": "best", "budget": 256, "max_atoms": 5}, "correct": 9}]
    selected = promotion_order(rows, 2, {"fast"})
    assert {row["architecture"]["id"] for row in selected} == {"fast", "best"}


def test_normalize_canonicalizes_irrelevant_cegis_controls():
    row = normalize({"engine": "cegis", "budget": 128, "max_atoms": 4,
                     "synthesize_constants": False, "progress_weight": 0.75, "widening": 0.4})
    assert row["progress_weight"] == 1.0
    assert row["widening"] == 0.5
