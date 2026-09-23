"""Offline, source-only edit-effect prediction. Not an online RSI policy."""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path

import numpy as np

from .common import digest
from .operators import initial_catalog
from .search import BOUNDS, validate_config

OPERATORS = sorted(op["name"] for op in initial_catalog())
PARENT_NAMES = sorted(BOUNDS)
VISIBLE_NAMES = ["input_length_mean", "output_length_mean", "input_length_std",
                 "output_length_std", "output_input_ratio", "substring", "prefix",
                 "suffix", "identity", "casefold_substring", "constant_output"]
VISIBLE_NAMES += [f"{side}_{kind}" for side in ("input", "output")
                 for kind in ("uppercase", "digit", "space", "separator", "tokens")]
MODELS = ["zero", "operator_mean", "parent", "context", "scrambled_context"]
ALPHAS = [1.0, 10.0, 100.0, 1000.0]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def visible_features(task):
    if set(task) != {"id", "visible"}:
        raise ValueError("Only public task id and visible examples are allowed")
    pairs = task["visible"]
    if not pairs or any(len(pair) != 2 or any(not isinstance(s, str) for s in pair) for pair in pairs):
        raise ValueError("Expected nonempty visible string pairs")
    inputs, outputs = zip(*pairs)
    il, ol = np.array(list(map(len, inputs))), np.array(list(map(len, outputs)))
    values = [il.mean() / 32, ol.mean() / 32, il.std() / 32, ol.std() / 32,
              np.mean(ol / np.maximum(il, 1))]
    for predicate in (lambda x, y: y in x, lambda x, y: x.startswith(y),
                      lambda x, y: x.endswith(y), lambda x, y: x == y,
                      lambda x, y: y.casefold() in x.casefold()):
        values.append(np.mean([predicate(x, y) for x, y in pairs]))
    values.append(float(len(set(outputs)) == 1))
    for strings in (inputs, outputs):
        for predicate in (str.isupper, str.isdigit, str.isspace,
                          lambda c: not c.isalnum() and not c.isspace()):
            values.append(np.mean([sum(predicate(c) for c in s) / max(1, len(s)) for s in strings]))
        values.append(np.mean([len(s.split()) for s in strings]) / 8)
    assert len(values) == len(VISIBLE_NAMES)
    return [float(x) for x in values]


def parent_features(config):
    validate_config(config)
    return [(config[k] - BOUNDS[k][0]) / (BOUNDS[k][1] - BOUNDS[k][0]) for k in PARENT_NAMES]


def source_evaluations(path):
    """Discard non-source events before touching their request or outcomes."""
    evaluations = {}
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event["kind"] != "evaluation":
                continue
            payload = event["payload"]
            if not payload["label"].startswith("balanced_source/"):
                continue
            if digest(payload["request"]) != payload["request_sha256"]:
                raise ValueError("Source request hash mismatch")
            key = (payload["label"], payload["request_sha256"])
            if key in evaluations:
                raise ValueError("Duplicate source evaluation")
            evaluations[key] = payload
    return evaluations


def extract(roots):
    rows, provenance = [], {}
    for root in map(Path, roots):
        read = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
        if read("audit.json")["status"] != "passed":
            raise ValueError("Source run has not passed its semantic audit")
        manifest = read("artifact_manifest.json")
        provenance[root.name] = {name: sha(root / name) for name in
                                 ("audit.json", "artifact_manifest.json", "events.jsonl", "source_trajectories.json")}
        for name in ("events.jsonl", "source_trajectories.json"):
            if provenance[root.name][name] != manifest[name]["sha256"]:
                raise ValueError("Source archive changed")
        evaluations = source_evaluations(root / "events.jsonl")
        for source in read("source_trajectories.json"):
            group = f"{root.name}/{source['seed']}"
            for decision in source["decisions"]:
                attempts = decision["attempts"]
                assert sorted(a["operator"]["name"] for a in attempts) == OPERATORS
                generation = decision["generation"]
                prefix = f"balanced_source/{source['seed']}/g{generation}"
                parent_hash = attempts[0]["parent_evaluation_request_sha256"]
                parent = evaluations[prefix + "/parent", parent_hash]
                tasks = parent["request"]["tasks"]
                parent_scores = {r["task_id"]: int(r["oracle_correct"]) for r in parent["results"]}
                assert len(parent_scores) == len(tasks)
                children, links = {}, {}
                for a in attempts:
                    op = a["operator"]["name"]
                    assert a["valid"] and a["parent_evaluation_request_sha256"] == parent_hash
                    assert a["parent_config"] == parent["request"]["config"]
                    child = evaluations[a["change_id"] + "/" + op, a["candidate_evaluation_request_sha256"]]
                    assert child["request"]["tasks"] == tasks
                    scores = {r["task_id"]: int(r["oracle_correct"]) for r in child["results"]}
                    assert scores.keys() == parent_scores.keys()
                    children[op] = {t: scores[t] - parent_scores[t] for t in scores}
                    assert abs(np.mean(list(children[op].values())) - a["development_gain"]) < 1e-12
                    links[op] = {"change_id": a["change_id"], "request_sha256": a["candidate_evaluation_request_sha256"]}
                for task in tasks:
                    visible_features(task)  # Refuse hidden/reference fields at extraction.
                    task_id = task["id"]
                    rows.append({"id": f"{group}/g{generation}/{task_id}", "group": group,
                                 "menu": f"{group}/g{generation}", "task": task,
                                 "parent_config": parent["request"]["config"],
                                 "parent_request_sha256": parent_hash, "candidate_links": links,
                                 "gains": [children[op][task_id] for op in OPERATORS]})
    rows.sort(key=lambda r: r["id"])
    assert len({r["id"] for r in rows}) == len(rows)
    return {"operators": OPERATORS, "rows": rows, "provenance": provenance}


def matrices(dataset):
    rows = dataset["rows"]
    return (np.array([visible_features(r["task"]) for r in rows]),
            np.array([parent_features(r["parent_config"]) for r in rows]),
            np.array([r["gains"] for r in rows], dtype=float))


def design(visible, parent, rows, indices, model, training):
    indices = list(map(int, indices))
    permutation = list(range(len(indices)))
    if model == "scrambled_context" and training:
        seed = int(digest([rows[i]["id"] for i in indices])[:16], 16)
        random.Random(seed).shuffle(permutation)
    x = parent[indices]
    if model in ("context", "scrambled_context"):
        x = np.column_stack((visible[np.array(indices)[permutation]], x))
    return x, permutation


def fit(x, y, alpha):
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale < 1e-12] = 1
    z = (x - mean) / scale
    intercept = y.mean(axis=0)
    coefficients = np.linalg.solve(z.T @ z + alpha * np.eye(x.shape[1]), z.T @ (y - intercept))
    return {"mean": mean.tolist(), "scale": scale.tolist(), "intercept": intercept.tolist(),
            "coefficients": coefficients.tolist(), "alpha": alpha}


def predict(x, fitted):
    return ((x - np.array(fitted["mean"])) / np.array(fitted["scale"])) @ np.array(fitted["coefficients"]) + np.array(fitted["intercept"])


def partition(rows, excluded_group, within=None):
    indices = range(len(rows)) if within is None else within
    return ([i for i in indices if rows[i]["group"] != excluded_group],
            [i for i in indices if rows[i]["group"] == excluded_group])


def evaluate_models(dataset, on_fold=None):
    rows = dataset["rows"]
    visible, parent, y = matrices(dataset)
    groups = sorted({r["group"] for r in rows})
    predictions = {name: np.zeros_like(y) for name in MODELS}
    records = []
    for group in groups:
        train, test = partition(rows, group)
        for model in MODELS:
            record = {"held_out_source": group, "model": model, "train_indices": train, "test_indices": test}
            if model in ("zero", "operator_mean"):
                mean = np.zeros(y.shape[1]) if model == "zero" else y[train].mean(axis=0)
                record["constant"] = mean.tolist()
                predictions[model][test] = mean
            else:
                inner = []
                for inner_group in groups:
                    if inner_group == group:
                        continue
                    inner_train, validation = partition(rows, inner_group, train)
                    x, permutation = design(visible, parent, rows, inner_train, model, True)
                    vx, _ = design(visible, parent, rows, validation, model, False)
                    scores = []
                    for alpha in ALPHAS:
                        fitted = fit(x, y[inner_train], alpha)
                        scores.append(float(np.mean((predict(vx, fitted) - y[validation]) ** 2)))
                    inner.append({"validation_source": inner_group, "train_indices": inner_train,
                                  "validation_indices": validation, "permutation": permutation, "mse_by_alpha": scores})
                mean_errors = np.mean([entry["mse_by_alpha"] for entry in inner], axis=0)
                chosen = min(range(len(ALPHAS)), key=lambda i: (mean_errors[i], -ALPHAS[i]))
                x, permutation = design(visible, parent, rows, train, model, True)
                tx, _ = design(visible, parent, rows, test, model, False)
                fitted = fit(x, y[train], ALPHAS[chosen])
                predictions[model][test] = predict(tx, fitted)
                record.update(inner=inner, mean_inner_mse=mean_errors.tolist(),
                              permutation=permutation, fitted=fitted)
            records.append(record)
        if on_fold:
            on_fold(group)
    return {"folds": records, "predictions": {k: v.tolist() for k, v in predictions.items()},
            "features": {"visible_names": VISIBLE_NAMES, "parent_names": PARENT_NAMES,
                         "visible": visible.tolist(), "parent": parent.tolist()}, "alphas": ALPHAS}


def summarize(dataset, analysis):
    rows, ops = dataset["rows"], dataset["operators"]
    y = np.array([r["gains"] for r in rows], dtype=float)
    predictions = {k: np.array(v) for k, v in analysis["predictions"].items()}
    menus = []
    for menu in sorted({r["menu"] for r in rows}):
        indices = [i for i, r in enumerate(rows) if r["menu"] == menu]
        gains = y[indices].mean(axis=0)
        pairs = list(itertools.combinations(range(len(ops)), 2))
        entry = {"menu": menu, "source": rows[indices[0]]["group"], "observed_gains": gains.tolist(),
                 "oracle_utility": float(max(0, gains.max())),
                 "random_utility": float(np.mean([max(0, gains[a], gains[b]) for a, b in pairs])), "models": {}}
        for name, prediction in predictions.items():
            scores = prediction[indices].mean(axis=0)
            selected = sorted(range(len(ops)), key=lambda i: (-scores[i], ops[i]))[:2]
            entry["models"][name] = {"scores": scores.tolist(), "selected": [ops[i] for i in selected],
                                     "utility": float(max(0, *gains[selected]))}
        menus.append(entry)
    by_source = {}
    for group in sorted({r["group"] for r in rows}):
        indices = [i for i, r in enumerate(rows) if r["group"] == group]
        source_menus = [m for m in menus if m["source"] == group]
        source = {}
        for name, prediction in predictions.items():
            errors = prediction[indices] - y[indices]
            nonzero = errors[y[indices] != 0]
            source[name] = {"mse": float(np.mean(errors ** 2)), "mae": float(np.mean(abs(errors))),
                            "nonzero_mse": float(np.mean(nonzero ** 2)) if len(nonzero) else None,
                            "utility": float(np.mean([m["models"][name]["utility"] for m in source_menus]))}
        for name in ("random", "oracle"):
            source[name] = {"utility": float(np.mean([m[name + "_utility"] for m in source_menus]))}
        by_source[group] = source
    overall = {name: {metric: float(np.mean([s[name][metric] for s in by_source.values() if s[name][metric] is not None]))
                      for metric in next(iter(by_source.values()))[name]} for name in [*MODELS, "random", "oracle"]}
    wins = sum(s["context"]["utility"] > s["operator_mean"]["utility"] for s in by_source.values())
    screen = {"context_mse_below_operator_mean": overall["context"]["mse"] < overall["operator_mean"]["mse"],
              "context_utility_above_controls": all(overall["context"]["utility"] > overall[n]["utility"]
                                                    for n in ("operator_mean", "parent", "scrambled_context")),
              "source_wins": wins, "required_source_wins": len(by_source) // 2 + 1}
    screen["passed"] = screen["context_mse_below_operator_mean"] and screen["context_utility_above_controls"] and wins >= screen["required_source_wins"]
    return {"contexts": len(rows), "task_edit_observations": int(y.size), "nonzero_labels": int(np.count_nonzero(y)),
            "menus": menus, "by_source": by_source, "overall": overall, "screen": screen}
