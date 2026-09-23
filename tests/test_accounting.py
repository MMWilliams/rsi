from rsi.accounting import arm_cost_totals, compute_by_arm


def test_compute_is_split_between_shared_and_arms():
    arms = ["baseline_selected", "corrected_frontier"]
    result = compute_by_arm(
        [
            ("s17_base", {"generated_tokens": 10}),
            ("s17_baseline_selected_round1_parent", {"generated_tokens": 20}),
            ("s17_corrected_frontier_round1_candidate_final", {"generated_tokens": 30}),
        ],
        [
            {"arm": "baseline_selected", "training_cost": {"training_steps": 2}},
            {"arm": "corrected_frontier", "training_cost": {"training_steps": 3}},
        ],
        arms,
    )
    assert result == {
        "shared": {"generated_tokens": 10},
        "baseline_selected": {"generated_tokens": 20, "training_steps": 2},
        "corrected_frontier": {"generated_tokens": 30, "training_steps": 3},
    }
    assert arm_cost_totals(result, arms) == {
        "baseline_selected": 22,
        "corrected_frontier": 33,
    }


def test_unknown_sample_label_is_rejected():
    try:
        compute_by_arm([("s17_unknown", {"generated_tokens": 1})], [], ["arm"])
    except ValueError as exc:
        assert "s17_unknown" in str(exc)
    else:
        raise AssertionError("unknown sample labels must not be silently assigned")
