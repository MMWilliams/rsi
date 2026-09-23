from stitch_ten import envelope, rank, selected_score


def test_candidate_envelope_contains_no_hidden_grade_or_reference():
    task = {"id": "x", "visible": [["abc", "a"]], "hidden": [["xyz", "WRONG"]], "reference": "secret"}
    row = envelope(task, "v67", {"program": "Concat(Sub(C0,C1))", "cost": 1.0})
    assert row is not None
    assert "hidden" not in row and "reference" not in row and "correct" not in row


def test_router_filters_sources_without_grades():
    rows = [{"task_id": "x", "source": source, "program": program, "cost": 1.0,
             "complexity": len(program), "visible_signature": "same", "required_operations": []}
            for source, program in (("a", "Concat(Sub(C0,C1))"), ("b", "Concat(Sub(C0,C2))"))]
    assert rank(rows, {"a", "b"}, ["b", "a"], 1)[0]["source"] == "b"
    assert rank(rows, {"a"}, ["b", "a"], 1)[0]["source"] == "a"
