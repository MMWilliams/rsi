import copy
import json

import numpy as np
import pytest

from audit_context_diagnostic import audit_analysis
from rsi.contextual import (OPERATORS, evaluate_models, fit, predict, source_evaluations,
                            summarize, visible_features)
from rsi.search import BASE_CONFIG


def test_public_features_reject_hidden_fields_and_ignore_ids():
    task = {"id": "one", "visible": [["Ab 12", "12"], ["Cd 34", "34"]]}
    assert visible_features(task) == visible_features({**task, "id": "unrelated"})
    for field in ("hidden", "reference", "oracle_correct"):
        with pytest.raises(ValueError, match="Only public"):
            visible_features({**task, field: "secret"})
    assert np.all(np.isfinite(visible_features({"id": "empty", "visible": [["", ""]]})))


def test_ridge_recovers_signed_relation_and_handles_constant_features():
    x = np.column_stack((np.arange(-10, 11), np.ones(21)))
    y = np.column_stack((x[:, 0] * 0.1 + 0.2, -x[:, 0] * 0.2))
    fitted = fit(x, y, 0.000001)
    np.testing.assert_allclose(predict(x, fitted), y, atol=1e-6)
    assert np.isfinite(fitted["coefficients"]).all()


def test_final_events_are_discarded_without_inspecting_outcomes(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"kind": "evaluation", "payload": {"label": "final/ancestor", "request": "deliberately invalid"}}) + "\n", encoding="utf-8")
    assert source_evaluations(path) == {}


@pytest.fixture(scope="module")
def synthetic_analysis():
    rows = []
    for group in range(4):
        for state in range(2):
            for index in range(5):
                # Each held-out source contains both contexts; identity versus
                # suffix cues determine which edit's known effect is beneficial.
                gains = [0] * len(OPERATORS)
                gains[state] = 1
                gains[1 - state] = -1
                rows.append({"id": f"{group}/{state}/{index}", "group": str(group), "menu": f"{group}/{state}",
                             "task": {"id": str(index), "visible": [["ABC12", "ABC12" if state else "12"]]},
                             "parent_config": BASE_CONFIG, "gains": gains})
    dataset = {"operators": OPERATORS, "rows": rows}
    analysis = evaluate_models(dataset)
    return dataset, analysis, summarize(dataset, analysis)


def test_whole_source_predictions_and_independent_audit(synthetic_analysis):
    dataset, analysis, results = synthetic_analysis
    assert results["overall"]["context"]["mse"] < results["overall"]["operator_mean"]["mse"] / 10
    assert audit_analysis(dataset, analysis, results)["status"] == "passed"
    for fold in analysis["folds"]:
        train = {dataset["rows"][i]["group"] for i in fold["train_indices"]}
        assert fold["held_out_source"] not in train


@pytest.mark.parametrize("corruption", ["prediction", "inner_split", "ranking"])
def test_semantic_audit_rejects_forgery(synthetic_analysis, corruption):
    dataset, original, summary = synthetic_analysis
    analysis, results = copy.deepcopy(original), copy.deepcopy(summary)
    if corruption == "prediction":
        analysis["predictions"]["context"][0][0] += 0.1
    elif corruption == "inner_split":
        fold = next(f for f in analysis["folds"] if f["model"] == "context")
        fold["inner"][0]["train_indices"].append(fold["test_indices"][0])
    else:
        results["menus"][0]["models"]["context"]["selected"] = ["forged", "choice"]
    with pytest.raises(AssertionError):
        audit_analysis(dataset, analysis, results)
