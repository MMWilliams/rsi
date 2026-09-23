from run_open_ended import normalize_operator


def test_normalize_list_updates_is_explicit_and_bounded():
    operator, repair = normalize_operator({
        "name": "candidate", "origin": "model",
        "updates": [{"name": "absolute_cost", "value": 0.3}, {"name": "widening", "value": 0.25}],
    })
    assert repair == "list_updates_to_field_map"
    assert operator["updates"] == {"absolute_cost": 0.3, "widening": 0.25}


def test_normalize_rejects_non_numeric_schema_repair():
    try:
        normalize_operator({"name": "bad", "origin": "model", "updates": [{"name": "absolute_cost", "value": [0.1, 0.9]}]})
    except ValueError as exc:
        assert "scalar numeric" in str(exc)
    else:
        raise AssertionError("non-scalar update was accepted")


def test_normalize_projects_out_of_bounds_scalar():
    operator, repair = normalize_operator({"name": "low", "origin": "model", "updates": {"match_cost": 0.03}})
    assert operator["updates"]["match_cost"] == 0.1
    assert "numeric_box_projection" in repair
