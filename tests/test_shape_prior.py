from rsi.shape_prior import choose, program_shape_bonus


def test_shape_prior_rewards_a_learned_fragment_shape():
    library = {"templates": [{"shape": [{"kind": "substr", "start": "C", "end": "C"},
                                          {"kind": "const"}], "count": 3}]}
    program = "Concat(Sub(C1,C2), '-')"
    assert program_shape_bonus(program, library) > 0
    candidates = [{"program": "Concat(Sub(C1,C2), '-')", "cost": 1.0},
                  {"program": "Concat(Sub(C1,C2))", "cost": 1.0}]
    assert choose(candidates, library, beta=3.0)["program"] == program
