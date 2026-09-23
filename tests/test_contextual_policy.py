from rsi.contextual_policy import select_policy, visible_features


def test_contextual_selector_uses_visible_features_only():
    tasks = [{"id": "a", "visible": [["x", "x"]]}, {"id": "b", "visible": [["long", "longer"]]}]
    rows = {"base": {"a": True, "b": False}, "evolved": {"a": False, "b": True}}
    assert len(visible_features(tasks[0])) == 8
    assert select_policy(tasks, rows, {"id": "c", "visible": [["x", "x"]]}, ["base", "evolved"], neighbors=1) == "base"
