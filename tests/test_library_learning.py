from rsi.library_learning import mine_library


def test_mine_library_is_deterministic_and_keeps_repeated_fragments():
    programs = [
        "Concat(Sub(C1,C2), '-')",
        "Concat(Sub(C1,C2), '-')",
        "Concat(Sub(C1,C2), '/', Sub(C3,C4))",
    ]
    first = mine_library(programs, max_library=4, max_length=3, min_frequency=2)
    second = mine_library(programs, max_library=4, max_length=3, min_frequency=2)
    assert first == second
    assert first["macros"]
    assert first["counts"][first["macros"][0]] >= 2
