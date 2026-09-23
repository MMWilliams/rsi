from rsi.generative_prior import choose, program_log_probability


def test_generator_prior_scores_valid_programs_and_rejects_invalid_literals():
    valid = "Concat(Sub(C1,C1), '-')"
    assert program_log_probability(valid) > float("-inf")
    assert program_log_probability("Concat('not-in-generator')") == float("-inf")


def test_generator_prior_choice_is_deterministic_and_prefers_generated_structure():
    candidates = [
        {"program": "Concat('not-in-generator')", "cost": 0.0},
        {"program": "Concat(Sub(C1,C1))", "cost": 1.0},
    ]
    first = choose(candidates)
    second = choose(candidates)
    assert first == second
    assert first["program"] == "Concat(Sub(C1,C1))"
