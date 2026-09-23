"""The learned-group agent's semantics written directly.

`rsi/family_reference.py` does this for syntactic families and is frozen by
the C-family protocol; this is the same check for
`rsi.learned_groups.LearnedFamilySimulator`: every task sorts the whole catalog
with `Harness.order_from_row_scores`, merges with `interleave`, and scans the
window as a list, with the group posterior over the agent's learned labels.
"""
from __future__ import annotations

import itertools

import numpy as np

from .mechanism_worlds import interleave

FLOOR = 1e-4


def group_terms(labels, evidence, weight, slip, per_world=3):
    """weight * log(FLOOR + P(atom's group is one of the world's groups)),
    uniform prior over every `per_world` groups, unseen atoms one extra group."""
    groups = int(labels.max()) + 1
    group_of = np.where(labels >= 0, labels, groups)
    triples = list(itertools.combinations(range(groups + 1), per_world))
    contains = np.zeros((len(triples), groups + 1))
    for row, triple in enumerate(triples):
        contains[row, list(triple)] = 1.
    log_prior = np.log(np.full(len(triples), 1. / len(triples)))
    observed = np.bincount(group_of[evidence > 0], minlength=groups + 1)
    posterior = log_prior + np.log(slip + (1 - slip) * contains) @ observed
    posterior = np.exp(posterior - posterior.max())
    posterior /= posterior.sum()
    return weight * np.log(FLOOR + posterior @ contains)[group_of]


def lifetime(harness, keys_of_row, views, prior, coach, budget, groups=None):
    """Per-task decisions (pick row or -1, hit) of an earned life; `groups` is
    (labels, weight, slip) for the learned-group agent, None for the plain one."""
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
    evidence = np.zeros(keys)
    decisions = []
    for view in views:
        if evidence.any():
            plain = coach.unknown * np.log(FLOOR + np.minimum(evidence, 1.))
        else:
            plain = np.zeros(keys)
        lifted = plain if groups is None else plain + group_terms(groups[0], evidence,
                                                                   *groups[1:])
        lifted, plain = np.append(lifted, 0.), np.append(plain, 0.)
        first = lifted[harness.left] + lifted[right]
        if constant is not None:
            first = first + constant
        order = harness.order_from_row_scores(first)
        if share:
            second = plain[harness.left] + plain[right]
            if coach.depth1:
                second = second + coach.depth1 * depth1
            order = interleave(order, harness.order_from_row_scores(second), share)
        rows = view['rows']
        candidates = np.flatnonzero(np.isin(rows, order[:budget]))
        pick = int(candidates[0]) if len(candidates) else -1
        decisions.append((int(rows[pick]) if pick >= 0 else -1,
                          int(pick >= 0 and view['good'][pick])))
        if pick >= 0:
            for key in keys_of_row[rows[pick]]:
                evidence[key] += 1.
    return decisions
