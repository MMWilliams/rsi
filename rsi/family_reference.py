"""The family-inference agent's semantics written directly.

The check on `rsi.family_inference.FamilySimulator` and the fast simulator it
extends, in the way `rsi.coach_reference` checks the coach: every task sorts
the whole catalog with `Harness.order_from_row_scores`, merges with
`interleave`, and scans the window as a list. It supports the levers the
family confirmation uses (the unknown-atom penalty, the pair prior, the hedge
and its slope) and the family term; the posterior is the same formula, since
the machinery under test is the ordering, not the arithmetic of a product of
likelihoods.
"""
from __future__ import annotations

import itertools

import numpy as np

from .mechanism_worlds import interleave

FLOOR = 1e-4


def family_terms(harness, evidence, weight, slip):
    """weight * log(FLOOR + P(atom's family is one of the world's three)),
    under a uniform prior over every triple of families."""
    families = sorted(harness.by_family)
    family_of = np.array([families.index(key.split(':')[0]) for key in harness.key_names])
    triples = list(itertools.combinations(range(len(families)), 3))
    contains = np.zeros((len(triples), len(families)))
    for row, triple in enumerate(triples):
        contains[row, list(triple)] = 1.
    log_prior = np.log(np.ones(len(triples)) / len(triples))
    observed = np.bincount(family_of[evidence > 0], minlength=len(families))
    posterior = log_prior + np.log(slip + (1 - slip) * contains) @ observed
    posterior = np.exp(posterior - posterior.max())
    posterior /= posterior.sum()
    return weight * np.log(FLOOR + posterior @ contains)[family_of]


def lifetime(harness, keys_of_row, views, prior, coach, budget, family=None):
    """Per-task decisions (pick row or -1, hit) of an earned life; `family` is
    (weight, slip) for the family-inference agent, None for the plain one."""
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
        lifted = plain if family is None else plain + family_terms(harness, evidence, *family)
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
