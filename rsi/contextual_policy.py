"""Visible-task feature extraction and nearest-neighbor policy selection."""

from __future__ import annotations

import math
from typing import Mapping, Sequence


def visible_features(task: Mapping[str, object]) -> tuple[float, ...]:
    examples = task["visible"]
    inputs = [str(pair[0]) for pair in examples]
    outputs = [str(pair[1]) for pair in examples]
    lengths = [len(value) for value in inputs + outputs]
    punctuation = sum(not char.isalnum() and not char.isspace() for value in outputs for char in value)
    digits = sum(char.isdigit() for value in inputs + outputs for char in value)
    return (
        float(len(examples)),
        float(sum(lengths) / max(1, len(lengths))),
        float(max(lengths, default=0)),
        float(sum(len(value) for value in inputs) / max(1, len(inputs))),
        float(sum(len(value) for value in outputs) / max(1, len(outputs))),
        float(punctuation),
        float(digits),
        float(len(set(outputs))),
    )


def _distance(left: Sequence[float], right: Sequence[float]) -> float:
    scales = (1.0, 8.0, 16.0, 8.0, 8.0, 4.0, 4.0, 1.0)
    return math.sqrt(sum(((a - b) / scale) ** 2 for a, b, scale in zip(left, right, scales)))


def select_policy(dev_tasks: Sequence[Mapping[str, object]], dev_rows: Mapping[str, Mapping[str, bool]], final_task: Mapping[str, object], policies: Sequence[str], neighbors: int = 7) -> str:
    """Choose the best policy by visible-feature nearest-neighbor evidence."""
    if not policies or not dev_tasks:
        raise ValueError("tasks and policies must be non-empty")
    target = visible_features(final_task)
    ranked = sorted(((_distance(target, visible_features(task)), task["id"]) for task in dev_tasks), key=lambda row: row[0])[:max(1, neighbors)]
    scores = {policy: 0.0 for policy in policies}
    weights = {policy: 0.0 for policy in policies}
    for distance, task_id in ranked:
        weight = 1.0 / (0.25 + distance)
        for policy in policies:
            scores[policy] += weight * float(dev_rows[policy][str(task_id)])
            weights[policy] += weight
    return max(policies, key=lambda policy: (scores[policy] / weights[policy], policy == "base", policy))
