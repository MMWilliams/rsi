"""The coach's semantics written directly, as the check on `growth_coach`.

`rsi.growth_coach.Simulator` is fast because it scores atom pairs in a table,
keeps partial orders and recomputes a window only when its inputs change. None
of that is used here: every task sorts the whole catalog with
`Harness.order_from_row_scores`, merges with `interleave`, and scans the
window as a list. It shares only the harness and the coach's field meanings,
so an agreement between the two, decision for decision, is evidence that the
fast one computes what the coach says.
"""
from __future__ import annotations

import numpy as np

from .mechanism_worlds import interleave

FLOOR = 1e-4
ROTATION = 16


def row_keys(harness):
    left, right = harness.left, harness.right
    return [(int(left[i]),) if right[i] < 0 else (int(left[i]), int(right[i]))
            for i in range(harness.catalog.size)]


def lifetime(harness, keys_of_row, views, prior, coach, budget, arm='earned'):
    """Per-task decisions of one life: (pick row or -1, hit)."""
    keys = len(harness.key_names)
    depth1 = (harness.right < 0).astype(np.float64)
    right = np.where(harness.right >= 0, harness.right, keys)
    constant = None
    if coach.pair:
        constant = coach.pair * prior.pair_rows
    if coach.depth1:
        extra = coach.depth1 * depth1
        constant = extra if constant is None else constant + extra
    share = coach.share(budget)
    allotted = coach.budgets(budget, len(views))
    evidence = np.zeros(keys)
    decisions = []
    for step, view in enumerate(views):
        if evidence.any():
            base = coach.unknown * np.log(FLOOR + np.minimum(evidence, 1.))
            if coach.count:
                base = base + coach.count * np.log1p(evidence)
            lifted = base
            if coach.affinity:
                known = np.flatnonzero(evidence > 0)
                lifted = base + coach.affinity * np.where(
                    evidence > 0, 0., prior.log_conditional[known].max(axis=0))
            plain = base if arm != 'guarded' else np.log(FLOOR + np.minimum(evidence, 1.))
        else:
            lifted = plain = np.zeros(keys)
        lifted, plain = np.append(lifted, 0.), np.append(plain, 0.)
        first = lifted[harness.left] + lifted[right]
        if constant is not None:
            first = first + constant
        order = harness.order_from_row_scores(first)
        if share:
            second = plain[harness.left] + plain[right]
            if coach.depth1 and arm != 'guarded':
                second = second + coach.depth1 * depth1
            order = interleave(order, harness.order_from_row_scores(second), share)
        scans = allotted[step]
        if coach.rotate:
            head = round((1 - coach.rotate) * scans)
            width = scans - head
            start = head + (step % ROTATION) * width
            window = np.concatenate([order[:head], order[start:start + width]])
        else:
            window = order[:scans]
        rows = view['rows']
        candidates = np.flatnonzero(np.isin(rows, window))
        pick = -1
        if len(candidates):
            pick = int(candidates[0])
            if coach.pick:
                known = [sum(evidence[k] > 0 for k in keys_of_row[rows[c]]) for c in candidates]
                pick = int(candidates[np.argmin(np.arange(len(candidates))
                                                - coach.pick * 10. * np.array(known))])
        decisions.append((int(rows[pick]) if pick >= 0 else -1,
                          int(pick >= 0 and view['good'][pick])))
        if pick < 0:
            continue
        for key in keys_of_row[rows[pick]]:
            evidence[key] += 1.
        if coach.soft and len(candidates) > 1:
            for c in candidates:
                if c != pick:
                    for key in keys_of_row[rows[c]]:
                        evidence[key] += coach.soft / len(candidates)
    return decisions
