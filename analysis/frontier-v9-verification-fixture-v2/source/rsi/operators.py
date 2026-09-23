"""Mutable operator catalog expressed as bounded arithmetic, never Python eval."""
from __future__ import annotations

import copy
import math
import random

from .common import digest
from .search import BASE_CONFIG, BOUNDS, validate_config


def expression(tree, config, depth=0):
    if depth > 6:
        raise ValueError("Expression depth")
    if type(tree) in (int, float) and math.isfinite(tree) and abs(tree) <= 20:
        return float(tree)
    if type(tree) is str and tree in BOUNDS:
        return config[tree]
    if not isinstance(tree, list) or len(tree) != 3 or tree[0] not in ("add", "sub", "mul", "min", "max"):
        raise ValueError("Invalid expression")
    left = expression(tree[1], config, depth + 1)
    right = expression(tree[2], config, depth + 1)
    return {"add": lambda: left + right, "sub": lambda: left - right, "mul": lambda: left * right,
            "min": lambda: min(left, right), "max": lambda: max(left, right)}[tree[0]]()


def validate_operator(operator):
    if not isinstance(operator, dict) or set(operator) != {"name", "updates", "origin"}:
        raise ValueError("Operator fields")
    if not isinstance(operator["name"], str) or not 1 <= len(operator["name"]) <= 80:
        raise ValueError("Operator name")
    if operator["origin"] not in ("initial", "model", "composition"):
        raise ValueError("Operator origin")
    if not isinstance(operator["updates"], dict) or not 1 <= len(operator["updates"]) <= 4 or not set(operator["updates"]) <= set(BOUNDS):
        raise ValueError("Forbidden edit target")
    for tree in operator["updates"].values():
        expression(tree, BASE_CONFIG)
    return operator


def apply(operator, config):
    validate_operator(operator)
    result = dict(config)
    for field, tree in operator["updates"].items():
        result[field] = round(expression(tree, config), 9)
    return validate_config(result)


def initial_catalog():
    result = []
    for field in ("absolute_cost", "match_cost", "constant_cost", "case_cost", "progress_weight", "widening"):
        lo, hi = BOUNDS[field]
        for factor, suffix in ((0.65, "down"), (1.4, "up")):
            result.append({"name": f"{field}_{suffix}", "updates": {field: ["min", hi, ["max", lo, ["mul", field, factor]]]}, "origin": "initial"})
    return result


def empty_stats():
    return {"trials": 0, "beneficial": 0, "accepted": 0, "gain_sum": 0.0, "descendant_trials": 0, "descendant_gain_sum": 0.0}


def select(catalog, table, rng, mode="adaptive", exclude=(), trace=None, credit_mode=None):
    available = [op for op in catalog if op["name"] not in exclude]
    if not available:
        available = catalog
    if trace is not None:
        trace.update(policy="operator_effect_v1", mode=mode, excluded=list(exclude),
                     available=[op["name"] for op in available], table_sha256=digest(table),
                     rng_before_sha256=digest(rng.getstate()), scores=[])
        if credit_mode is not None:
            trace["credit_mode"] = credit_mode
    if mode == "random":
        chosen = rng.choice(available)
        if trace is not None:
            trace.update(selected=chosen["name"], rng_after_sha256=digest(rng.getstate()),
                         reason="uniform_choice_from_available_operators")
        return chosen
    # Untried operators receive exploration; inherited data changes this ranking.
    scores = []
    for op in available:
        stats = table.get(op["name"], empty_stats())
        positive = stats.get("beneficial", stats["accepted"])
        productivity = rng.betavariate(1 + positive, 1 + stats["trials"] - positive)
        effect = stats["gain_sum"] / max(1, stats["trials"])
        descendant = stats.get("descendant_gain_sum", 0.0) / max(1, stats.get("descendant_trials", 0))
        paired = stats.get("paired_gain_sum", 0.0) / max(1, stats.get("paired_trials", 0))
        if credit_mode == "immediate_only":
            credit, credit_label = 0.0, "immediate_only"
        elif credit_mode == "paired_credit":
            credit, credit_label = paired, "paired_later_improvement"
        else:
            credit, credit_label = descendant, "observational_descendant"
        score = productivity + effect + 0.25 * credit
        scores.append((score, op["name"], op))
        if trace is not None:
            row = {"name": op["name"], "alpha": 1 + positive,
                   "beta": 1 + stats["trials"] - positive, "productivity_draw": productivity,
                   "mean_gain": effect, "descendant_mean": descendant, "score": score}
            if credit_mode is not None:
                row.update(credit_mode=credit_label, credit_mean=credit)
            trace["scores"].append(row)
    chosen = max(scores, key=lambda row: (row[0], row[1]))[2]
    if trace is not None:
        reason = ("maximum_sampled_productivity_plus_mean_gain_plus_quarter_" +
                  ("paired_later_improvement" if credit_mode == "paired_credit" else
                   "immediate_only" if credit_mode == "immediate_only" else "descendant_mean") +
                  "; lexical_name_tiebreak") if credit_mode is not None else \
                 "maximum_sampled_productivity_plus_mean_gain_plus_quarter_descendant_mean; lexical_name_tiebreak"
        trace.update(selected=chosen["name"], rng_after_sha256=digest(rng.getstate()), reason=reason)
    return chosen


def shuffled_table(table, rng):
    names = sorted(table)
    records = [copy.deepcopy(table[name]) for name in names]
    rng.shuffle(records)
    return dict(zip(names, records))


def compose_catalog_operator(first, second):
    """Fallback hypothesis generator; origin is recorded and never called LLM invention."""
    updates = copy.deepcopy(first["updates"])
    def substitute(tree):
        if isinstance(tree, str) and tree in updates:
            return copy.deepcopy(updates[tree])
        if isinstance(tree, list):
            return [tree[0], substitute(tree[1]), substitute(tree[2])]
        return tree
    for field, tree in second["updates"].items():
        updates[field] = substitute(tree)
    operator = {"name": "composed_" + digest(updates)[:10], "updates": updates, "origin": "composition"}
    return validate_operator(operator)
