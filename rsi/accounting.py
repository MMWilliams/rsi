"""Compute accounting helpers for neural frontier experiments.

The experiment ledger is global, but comparisons need the cost of each arm
separated from shared bootstrap work.  These helpers keep that split explicit
without assigning shared work to every arm.
"""

from __future__ import annotations

from typing import Iterable, Mapping


def bucket_for_sample_label(label: str, arms: Iterable[str]) -> str:
    """Return ``shared`` for common checkpoints or the owning arm."""
    parts = label.split("_")
    if len(parts) >= 2 and parts[1] in {"base", "initial"}:
        return "shared"
    for arm in arms:
        if f"_{arm}_" in label:
            return arm
    raise ValueError(f"Cannot assign sample label to an arm: {label}")


def accumulate_cost(target: dict[str, float], cost: Mapping[str, int | float]) -> None:
    """Add one cost vector into an existing bucket in place."""
    for key, value in cost.items():
        target[key] = target.get(key, 0) + value


def compute_by_arm(
    sample_costs: Iterable[tuple[str, Mapping[str, int | float]]],
    changes: Iterable[Mapping[str, object]],
    arms: Iterable[str],
) -> dict[str, dict[str, int | float]]:
    """Separate unique sampling and training costs into shared and arm buckets."""
    arm_names = list(arms)
    buckets: dict[str, dict[str, int | float]] = {"shared": {}}
    buckets.update({arm: {} for arm in arm_names})

    for label, cost in sample_costs:
        accumulate_cost(buckets[bucket_for_sample_label(label, arm_names)], cost)
    for change in changes:
        arm = str(change["arm"])
        if arm not in buckets:
            raise ValueError(f"Unknown change arm: {arm}")
        accumulate_cost(buckets[arm], change["training_cost"])
    return buckets


def arm_cost_totals(
    compute: Mapping[str, Mapping[str, int | float]],
    arms: Iterable[str],
) -> dict[str, int | float]:
    """Return a transparent scalar only for display, never for matching.

    The scalar is the sum of recorded ledger fields and is not a FLOP estimate.
    Vector fields remain authoritative for budget checks.
    """
    return {
        arm: sum(value for key, value in compute.get(arm, {}).items() if key != "seconds")
        for arm in arms
    }
