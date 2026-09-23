from collections import Counter
import pytest

from rsi.frontier_training import build_pool, draw_schedule, harvest_arm


def test_frontier_controls_separate_selected_from_first_verified_and_all():
    frontier = [{"program": "bad", "oracle_correct": False}, {"program": "good1", "oracle_correct": True}, {"program": "good2", "oracle_correct": True}]
    assert harvest_arm(frontier, "baseline_selected") == []
    assert harvest_arm(frontier, "corrected_selected") == []
    assert harvest_arm(frontier, "corrected_first_verified") == frontier[1:2]
    assert harvest_arm(frontier, "corrected_frontier") == frontier[1:]


def test_task_balance_ignores_program_multiplicity_and_preserves_anchor_draws():
    anchors = [{"stratum": "anchor", "task_id": f"a{i}"} for i in range(7)]
    small = anchors + [{"stratum": "harvest", "task_id": "one"}, {"stratum": "harvest", "task_id": "many"}]
    large = small + [{"stratum": "harvest", "task_id": "many"}] * 99
    a = draw_schedule(small, 19, 1000, 8, 4)
    b = draw_schedule(large, 19, 1000, 8, 4)
    assert a == draw_schedule(small, 19, 1000, 8, 4)
    assert [x[:4] for x in a] == [x[:4] for x in b]
    assert [[small[i]['task_id'] for i in step[4:]] for step in a] == [[large[i]['task_id'] for i in step[4:]] for step in b]
    counts = Counter(large[i]["task_id"] for step in b for i in step[4:])
    assert 1800 < counts["one"] < 2200


def test_training_pool_reverifies_instead_of_trusting_certificate():
    task = {"id": "t", "visible": [["a", "a"]], "hidden": [["bc", "b"]]}
    good = {"task_id": "t", "program": "Concat(Sub(C0,C1))", "oracle_correct": True}
    assert build_pool([good], [], {"t": task})[0]["stratum"] == "anchor"
    with pytest.raises(ValueError, match="Unverified"):
        build_pool([{**good, "program": "Concat('a')"}], [], {"t": task})
    assert draw_schedule(build_pool([good], [], {"t": task}), 1, 4, 8, 4) == []
    with pytest.raises(ValueError, match="overlap"):
        build_pool([good], [good], {"t": task})


def test_advancement_requires_beating_base_and_retaining_round_one():
    from run_frontier_distillation import advancement
    config = {"training_seeds": [17, 29, 43]}
    scores, selected = {}, {}
    for seed in config["training_seeds"]:
        selected[str(seed)] = {"corrected_frontier": {"1": f"s{seed}_f1", "2": f"s{seed}_f2"}, "corrected_selected": {"2": f"s{seed}_selected"}}
        for name, value in (("initial", .1), ("base", .2), ("selected", .2), ("f1", .3), ("f2", .4)):
            scores[f"s{seed}_{name}"] = {"pass_at_k": {"64": value}}
    assert advancement(scores, selected, config)["passed"]
    for seed in config["training_seeds"]:
        scores[f"s{seed}_base"]["pass_at_k"]["64"] = .5
    assert not advancement(scores, selected, config)["passed"]
    for seed in config["training_seeds"]:
        scores[f"s{seed}_base"]["pass_at_k"]["64"] = .2
        scores[f"s{seed}_f1"]["pass_at_k"]["64"] = .5
    assert not advancement(scores, selected, config)["passed"]
