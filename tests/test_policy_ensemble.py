from run_policy_ensemble import select_by_vote


def test_rank_discounted_vote_prefers_repeated_frontier_program():
    rows = [
        {"frontier_programs": ["A", "B"]},
        {"frontier_programs": ["B", "A"]},
    ]
    assert select_by_vote(rows) == "A" or select_by_vote(rows) == "B"
