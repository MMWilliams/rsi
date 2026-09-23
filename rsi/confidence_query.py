"""Bayesian structural confidence gate for active synthesis.

The model intentionally drops literal constant-value features so it must
generalize over program structure instead of memorizing development strings.
"""

from __future__ import annotations

import math
from collections import Counter

from dsl import PosError, run
from parse import ParseError, parse

from .cegis_search import solve as cegis_solve
from .common import digest
from .meta_ranker import program_features


def _bucket(value: int, width: int = 4) -> str:
    return str(min(8, max(0, int(value) // width)))


def structural_features(result: dict, query_count: int) -> set[str]:
    features: set[str] = {f"query:{query_count}"}
    program = result.get("program", "")
    try:
        raw = program_features(program)
    except (ValueError, ParseError, PosError, RecursionError):
        raw = {}
    for name, value in raw.items():
        # Literal values are deliberately omitted; numeric magnitudes are kept
        # only as coarse structural indicators.
        if name.startswith("atom:const:value:"):
            continue
        if name.endswith(":length"):
            features.add(f"{name}:{_bucket(int(value), 2)}")
        elif value:
            features.add(name)
    cost = result.get("cost", {})
    if isinstance(cost, dict):
        features.add(f"candidate_count:{_bucket(cost.get('candidate_count', 9999))}")
        features.add(f"transition_count:{_bucket(cost.get('transition_count', 9999), 16)}")
        features.add(f"expanded:{_bucket(cost.get('expansions', 9999), 64)}")
    return features


class BayesianConfidence:
    def __init__(self, smoothing: float = 1.0):
        self.smoothing = smoothing
        self.class_counts = Counter()
        self.feature_counts = {True: Counter(), False: Counter()}
        self.feature_vocab: set[str] = set()
        self.samples = 0

    def fit(self, rows: list[tuple[dict, int, bool]]) -> dict:
        for result, query_count, label in rows:
            y = bool(label)
            feats = structural_features(result, query_count)
            self.class_counts[y] += 1
            self.feature_vocab.update(feats)
            self.feature_counts[y].update(feats)
            self.samples += 1
        return {"samples": self.samples, "positive": self.class_counts[True],
                "negative": self.class_counts[False], "features": len(self.feature_vocab),
                "model_sha256": digest(self.to_dict())}

    def probability(self, result: dict, query_count: int) -> float:
        if not self.samples:
            return 0.5
        feats = structural_features(result, query_count)
        total_features = len(self.feature_vocab)
        logs = {}
        for y in (True, False):
            prior = (self.class_counts[y] + self.smoothing) / (self.samples + 2 * self.smoothing)
            value = math.log(prior)
            n = self.class_counts[y]
            for feature in self.feature_vocab:
                present = self.feature_counts[y][feature]
                p = (present + self.smoothing) / (n + 2 * self.smoothing)
                value += math.log(p if feature in feats else (1.0 - p))
            logs[y] = value
        gap = max(-60.0, min(60.0, logs[True] - logs[False]))
        return 1.0 / (1.0 + math.exp(-gap))

    def to_dict(self) -> dict:
        return {"smoothing": self.smoothing, "class_counts": dict(self.class_counts),
                "feature_counts": {str(k): dict(sorted(v.items())) for k, v in self.feature_counts.items()},
                "feature_vocab": sorted(self.feature_vocab), "samples": self.samples}

    @classmethod
    def from_dict(cls, data: dict) -> "BayesianConfidence":
        model = cls(float(data["smoothing"]))
        model.class_counts.update({(str(key).lower() in {"true", "1"}): value
                                   for key, value in data["class_counts"].items()})
        for key, values in data["feature_counts"].items():
            model.feature_counts[str(key).lower() in {"true", "1"}].update(values)
        model.feature_vocab = set(data["feature_vocab"])
        model.samples = int(data["samples"])
        return model


def _counterexample(program: str, examples: list[list[str]], used: list[list[str]]):
    for pair in examples:
        if pair in used:
            continue
        try:
            output = run(parse(program), pair[0])
        except (ValueError, ParseError, PosError, RecursionError):
            output = None
        if output != pair[1]:
            return pair
    return None


def synth(task: dict, examples: list[list[str]], config: dict, macros: list[str]) -> dict:
    return cegis_solve({"id": task["id"], "visible": examples}, config,
                       config["budget"], config["max_atoms"], macros, [],
                       synthesize_constants=True)


def trajectory(task: dict, config: dict, macros: list[str], max_queries: int = 2):
    """Collect all states encountered by a fixed query-until-limit episode."""
    examples = list(task["visible"])
    rows = []
    for query_count in range(max_queries + 1):
        result = synth(task, examples, config, macros)
        rows.append((result, query_count))
        if query_count >= max_queries:
            break
        counterexample = _counterexample(result["program"], task["hidden"], examples)
        if counterexample is None:
            break
        examples.append(counterexample)
    return rows


def solve(task: dict, model: BayesianConfidence, threshold: float, config: dict,
          macros: list[str], max_queries: int = 2) -> dict:
    examples = list(task["visible"])
    trace = []
    query_count = 0
    for step in range(max_queries + 1):
        result = synth(task, examples, config, macros)
        probability = model.probability(result, query_count)
        action = "query" if step < max_queries and probability < threshold else "stop"
        trace.append({"query_count": query_count, "probability": probability,
                      "threshold": threshold, "action": action})
        if action == "stop":
            break
        counterexample = _counterexample(result["program"], task["hidden"], examples)
        query_count += 1
        if counterexample is None:
            break
        examples.append(counterexample)
    result = dict(result)
    result.update({"queries": query_count, "examples_used": len(examples), "trace": trace,
                   "confidence_model_sha256": digest(model.to_dict())})
    result["replay_sha256"] = digest(result)
    return result
