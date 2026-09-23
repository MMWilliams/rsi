"""Build frozen inherited-credit tables from the audited V10 paired probe."""
from __future__ import annotations

import copy
import random

from rsi.operators import empty_stats, initial_catalog, shuffled_table


def _table():
    return {op["name"]: empty_stats() for op in initial_catalog()}


def table_from_v10(pairs, mode):
    """Aggregate V10 source effects without peeking at transfer outcomes."""
    if mode not in ("immediate_only", "observational_descendant", "paired_credit"):
        raise ValueError("unknown credit mode")
    table = _table()
    for row in pairs:
        name = row["edit"]
        if name not in table:
            raise ValueError(f"V10 operator is outside current catalog: {name}")
        stats = table[name]
        scale = 1.0 / row["measurement_n"]
        stats["trials"] += 1
        stats["beneficial"] += int(row["immediate"] > 0)
        stats["gain_sum"] += row["immediate"] * scale
        if mode == "observational_descendant":
            stats["descendant_trials"] = stats.get("descendant_trials", 0) + 1
            stats["descendant_gain_sum"] = stats.get("descendant_gain_sum", 0.0) + row["total_descendant"] * scale
        elif mode == "paired_credit":
            stats["paired_trials"] = stats.get("paired_trials", 0) + 1
            stats["paired_gain_sum"] = stats.get("paired_gain_sum", 0.0) + row["later_improvement"] * scale
    return table


def scrambled_paired_table(pairs, seed):
    names = sorted(_table())
    paired = table_from_v10(pairs, "paired_credit")
    records = [copy.deepcopy(paired[name]) for name in names]
    random.Random(seed).shuffle(records)
    return dict(zip(names, records))
