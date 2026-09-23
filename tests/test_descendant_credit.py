"""Check sensitivity arithmetic and the distinction between credits and observations."""
import copy

import pytest

from analyze_descendant_credit import reconstruct_credit, score_sensitivity


def test_descendant_term_can_flip_a_close_choice_without_changing_draws():
    trace = {"mode": "adaptive", "selected": "a", "available": ["a", "b"],
             "rng_before_sha256": "fixed", "table_sha256": "fixed", "scores": [
        {"name": "a", "productivity_draw": .4, "mean_gain": .01, "descendant_mean": .04, "score": .42},
        {"name": "b", "productivity_draw": .415, "mean_gain": 0., "descendant_mean": 0., "score": .415}]}
    original = copy.deepcopy(trace)
    row = score_sensitivity(trace)
    assert row["descendant_term_flips_local_choice"]
    assert row["without_descendant_term"] == "b"
    assert trace == original
    trace["scores"][0]["score"] = .9
    with pytest.raises(ValueError, match="arithmetic"):
        score_sensitivity(trace)


def repeated_lineage():
    initial = {"a": {"descendant_trials": 0, "descendant_gain_sum": 0.}}
    decisions = [
        {"generation": 1, "operator": "a", "accepted": True, "admission_gain": .1,
         "attempts": [{"accepted": True, "change_id": "first"}]},
        {"generation": 2, "operator": "a", "accepted": True, "admission_gain": .2,
         "attempts": [{"accepted": True, "change_id": "second"}]},
        {"generation": 3, "operator": "a", "accepted": False, "admission_gain": -.1,
         "attempts": [{"accepted": False, "change_id": "third"}]}]
    snapshots = {str(g): {"table": {"a": {"descendant_trials": n, "descendant_gain_sum": gain}}}
                 for g, n, gain in ((1, 0, 0.), (2, 1, .2), (3, 3, 0.))}
    return {"decisions": decisions, "snapshots": snapshots}, initial


def test_repeated_operator_credit_is_counted_per_ancestor_not_independent_observation():
    trajectory, initial = repeated_lineage()
    rows = reconstruct_credit(trajectory, initial)
    assert len(rows) == 3
    rejected = [r for r in rows if not r["later_candidate_accepted"]]
    assert len(rejected) == 2
    assert {r["ancestor_change_id"] for r in rejected} == {"first", "second"}
    assert {r["later_generation"] for r in rejected} == {3}
    assert all(r["same_operator_occurrences_in_lineage"] == 2 for r in rejected)


def test_credit_reconstruction_rejects_inflated_trial_count():
    trajectory, initial = repeated_lineage()
    trajectory["snapshots"]["3"]["table"]["a"]["descendant_trials"] = 4
    with pytest.raises(ValueError, match="reconstruction"):
        reconstruct_credit(trajectory, initial)
