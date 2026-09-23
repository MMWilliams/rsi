"""Independent regression and ranking reconstruction for the v6 diagnostic.

Shares source extraction and feature definitions, but never calls the trainer,
predictor, cross-validation or summarizer. Regression uses augmented least
squares instead of the trainer's normal-equation solve.
"""
import argparse
import itertools
import json
import random
from pathlib import Path

import numpy as np

from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.contextual import ALPHAS, MODELS, extract, matrices, sha


def close(actual, expected, label):
    if not np.allclose(actual, expected, rtol=1e-9, atol=1e-12):
        raise AssertionError(label)


def audit_analysis(dataset, analysis, results):
    rows = dataset["rows"]
    visible, parent, y = matrices(dataset)
    groups = sorted({row["group"] for row in rows})
    assert analysis["alphas"] == ALPHAS
    close(analysis["features"]["visible"], visible, "Visible features changed")
    close(analysis["features"]["parent"], parent, "Parent features changed")
    predictions = {name: np.zeros_like(y) for name in MODELS}
    seen, fit_count = set(), 0

    def build(indices, model, permutation=None):
        x = parent[indices]
        if model in ("context", "scrambled_context"):
            positions = indices if permutation is None else [indices[j] for j in permutation]
            x = np.column_stack((visible[positions], x))
        return x

    def expected_permutation(indices, model):
        order = list(range(len(indices)))
        if model == "scrambled_context":
            random.Random(int(digest([rows[i]["id"] for i in indices])[:16], 16)).shuffle(order)
        return order

    def regress(x, labels, tx, alpha):
        nonlocal fit_count
        fit_count += 1
        mu, sd = np.mean(x, axis=0), np.std(x, axis=0)
        sd[sd < 1e-12] = 1
        z = (x - mu) / sd
        intercept = labels.mean(axis=0)
        augmented = np.vstack((z, np.sqrt(alpha) * np.eye(z.shape[1])))
        target = np.vstack((labels - intercept, np.zeros((z.shape[1], labels.shape[1]))))
        coefficients = np.linalg.lstsq(augmented, target, rcond=None)[0]
        prediction = ((tx - mu) / sd) @ coefficients + intercept
        return prediction, (mu, sd, intercept, coefficients)

    for fold in analysis["folds"]:
        group, model = fold["held_out_source"], fold["model"]
        assert group in groups and model in MODELS and (group, model) not in seen
        seen.add((group, model))
        train = [i for i, r in enumerate(rows) if r["group"] != group]
        test = [i for i, r in enumerate(rows) if r["group"] == group]
        assert fold["train_indices"] == train and fold["test_indices"] == test, "Outer source leakage"
        if model in ("zero", "operator_mean"):
            expected = np.zeros(y.shape[1]) if model == "zero" else y[train].mean(axis=0)
            close(fold["constant"], expected, "Baseline mismatch")
            predictions[model][test] = expected
            continue
        inner_groups, inner_errors = set(), []
        for inner in fold["inner"]:
            validation_group = inner["validation_source"]
            assert validation_group in groups and validation_group != group and validation_group not in inner_groups
            inner_groups.add(validation_group)
            itrain = [i for i in train if rows[i]["group"] != validation_group]
            validation = [i for i in train if rows[i]["group"] == validation_group]
            assert inner["train_indices"] == itrain and inner["validation_indices"] == validation, "Inner source leakage"
            order = expected_permutation(itrain, model)
            assert inner["permutation"] == order, "Inner permutation mismatch"
            x, vx = build(itrain, model, order), build(validation, model)
            errors = []
            for alpha in ALPHAS:
                prediction, _ = regress(x, y[itrain], vx, alpha)
                errors.append(float(np.mean((prediction - y[validation]) ** 2)))
            close(inner["mse_by_alpha"], errors, "Nested validation MSE mismatch")
            inner_errors.append(errors)
        assert inner_groups == set(groups) - {group}
        mean_errors = np.mean(inner_errors, axis=0)
        close(fold["mean_inner_mse"], mean_errors, "Nested MSE aggregation mismatch")
        chosen = min(range(len(ALPHAS)), key=lambda i: (mean_errors[i], -ALPHAS[i]))
        fitted = fold["fitted"]
        assert fitted["alpha"] == ALPHAS[chosen], "Wrong nested alpha"
        order = expected_permutation(train, model)
        assert fold["permutation"] == order, "Outer permutation mismatch"
        prediction, parts = regress(build(train, model, order), y[train], build(test, model), fitted["alpha"])
        for key, expected in zip(("mean", "scale", "intercept", "coefficients"), parts):
            close(fitted[key], expected, "Fitted " + key + " mismatch")
        predictions[model][test] = prediction
    assert seen == set(itertools.product(groups, MODELS))
    for model in MODELS:
        close(analysis["predictions"][model], predictions[model], "Held-out prediction mismatch")
    # Rankings use archived predictions after numerical validation above, avoiding
    # a last-bit solver difference changing a mathematical tie.
    recorded = {k: np.array(v) for k, v in analysis["predictions"].items()}
    menu_values, seen_menus = {}, set()
    for entry in results["menus"]:
        menu = entry["menu"]
        assert menu not in seen_menus
        seen_menus.add(menu)
        indices = [i for i, row in enumerate(rows) if row["menu"] == menu]
        assert indices and entry["source"] == rows[indices[0]]["group"]
        gains = y[indices].mean(axis=0)
        close(entry["observed_gains"], gains, "Observed menu gains mismatch")
        values = {"oracle": max(0, max(gains)),
                  "random": np.mean([max(0, gains[a], gains[b]) for a, b in itertools.combinations(range(len(gains)), 2)])}
        for model in MODELS:
            scores = recorded[model][indices].mean(axis=0)
            names = dataset["operators"]
            chosen = sorted(range(len(names)), key=lambda i: (-scores[i], names[i]))[:2]
            result = entry["models"][model]
            assert result["selected"] == [names[i] for i in chosen], "Wrong selected edits"
            close(result["scores"], scores, "Ranking scores mismatch")
            values[model] = max(0, *(gains[i] for i in chosen))
            close(result["utility"], values[model], "Ranking utility mismatch")
        for model in ("random", "oracle"):
            close(entry[model + "_utility"], values[model], "Control utility mismatch")
        menu_values[menu] = values
    assert seen_menus == {r["menu"] for r in rows}
    by_source = {}
    for group in groups:
        indices = [i for i, row in enumerate(rows) if row["group"] == group]
        menus = {rows[i]["menu"] for i in indices}
        source = {}
        for model in [*MODELS, "random", "oracle"]:
            values = {"utility": float(np.mean([menu_values[m][model] for m in menus]))}
            if model in MODELS:
                errors = recorded[model][indices] - y[indices]
                nonzero = errors[y[indices] != 0]
                values.update(mse=float(np.mean(errors ** 2)), mae=float(np.mean(abs(errors))),
                              nonzero_mse=float(np.mean(nonzero ** 2)) if len(nonzero) else None)
            source[model] = values
            for key, value in values.items():
                if value is None:
                    assert results["by_source"][group][model][key] is None
                else:
                    close(results["by_source"][group][model][key], value, "Source metric mismatch")
        by_source[group] = source
    overall = {}
    for model in [*MODELS, "random", "oracle"]:
        overall[model] = {}
        for metric in by_source[groups[0]][model]:
            value = np.mean([s[model][metric] for s in by_source.values() if s[model][metric] is not None])
            overall[model][metric] = value
            close(results["overall"][model][metric], value, "Overall metric mismatch")
    wins = sum(s["context"]["utility"] > s["operator_mean"]["utility"] for s in by_source.values())
    expected_screen = {
        "context_mse_below_operator_mean": bool(overall["context"]["mse"] < overall["operator_mean"]["mse"]),
        "context_utility_above_controls": all(overall["context"]["utility"] > overall[n]["utility"] for n in ("operator_mean", "parent", "scrambled_context")),
        "source_wins": wins, "required_source_wins": len(groups) // 2 + 1}
    expected_screen["passed"] = bool(expected_screen["context_mse_below_operator_mean"] and expected_screen["context_utility_above_controls"] and wins >= expected_screen["required_source_wins"])
    assert results["screen"] == expected_screen, "Advancement screen mismatch"
    assert results["contexts"] == len(rows) and results["task_edit_observations"] == y.size
    assert results["nonzero_labels"] == np.count_nonzero(y)
    return {"status": "passed", "contexts": len(rows), "outer_model_folds": len(seen),
            "regressions_independently_reconstructed": fit_count, "menus": len(menu_values),
            "predictions_checked": y.size * len(MODELS),
            "limits": "Shares audited source extraction and feature definitions; reuses prior oracle labels. Checks arithmetic, not host authenticity, online causal benefit or unseen-template transfer."}


def audit(root):
    root = Path(root)
    read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    manifest = read("artifact_manifest.json")
    for name, entry in manifest.items():
        assert sha(root / name) == entry["sha256"] and (root / name).stat().st_size == entry["bytes"], "Archive changed"
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    count = verify_journal(root / "events.jsonl")
    assert events[0]["kind"] == "started" and events[-1]["kind"] == "completed"
    started = events[0]["payload"]
    for name, value in started["source_hashes"].items():
        assert sha(root / "source" / name) == value
        assert sha(ROOT / name) == value, "Run audit with archived source versions"
    dataset = extract([ROOT / p for p in started["source_paths"]])
    assert dataset == read("dataset.json"), "Sanitized source extraction mismatch"
    assert len(dataset["rows"]) == 864
    assert events[1]["payload"]["dataset_sha256"] == sha(root / "dataset.json")
    audit_result = audit_analysis(dataset, read("analysis.json"), read("results.json"))
    audit_result.update(artifacts_hashed=len(manifest), journal_events=count)
    assert events[-1]["payload"]["screen"] == read("results.json")["screen"]
    write_json(root / "audit.json", audit_result)
    return audit_result


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("Audit assertions must be enabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("run")
    print(json.dumps(audit(parser.parse_args().run), indent=2))
