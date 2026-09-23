"""Learned groups must recover planted structure, and the agent built on them
must only change which atoms share a group."""
from __future__ import annotations

import random

import numpy as np
from sklearn.metrics import adjusted_rand_score

from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness


def test_recovers_planted_groups():
    rng = random.Random(1)
    keys, sizes = 60, (15, 15, 15, 15)
    truth = np.repeat(np.arange(len(sizes)), sizes)
    members = [np.flatnonzero(truth == g) for g in range(len(sizes))]
    worlds = []
    for _ in range(600):
        chosen = rng.sample(range(len(sizes)), 2)
        pool = [int(k) for g in chosen for k in members[g]]
        worlds.append(sorted(rng.sample(pool, 10)))
    labels, groups = learn_groups(worlds, keys + 5, choices=range(2, 8))
    assert groups == len(sizes)
    assert (labels[keys:] == -1).all()
    assert adjusted_rand_score(truth, labels[:keys]) == 1.


def test_likelihood_selects_the_planted_count():
    rng = random.Random(2)
    truth = np.repeat(np.arange(6), 12)
    members = [np.flatnonzero(truth == g) for g in range(6)]
    worlds = []
    for _ in range(800):
        pool = [int(k) for g in rng.sample(range(6), 3) for k in members[g]]
        worlds.append(sorted(rng.sample(pool, 14)))
    labels, groups = learn_groups(worlds, len(truth), choices=range(3, 10), select='likelihood')
    assert groups == 6
    assert adjusted_rand_score(truth, labels) == 1.


def test_learned_agent_matches_its_semantics():
    from rsi import coach_reference, learned_reference
    from rsi.growth_coach import (CHAMPION, UNHEDGED, Prior, draw_worlds, observed_sets,
                                  triples)
    harness = Harness()
    harness.set_tiebreak(611101 + 77)
    rng = random.Random(9)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    pool = triples(harness, seen, rng, 14, 130)
    worlds = draw_worlds(harness, pool, 3, rng, 14, 130, 30)
    reserved = {index for world in worlds for index in world['stream']}
    training = draw_worlds(harness, pool, 200, rng, 14, 130, 0)
    observed = observed_sets(harness, training, reserved, 64, rng)
    prior = Prior(harness, observed)
    labels, _groups = learn_groups(observed, len(harness.key_names), choices=range(3, 10),
                                   select='likelihood')
    agent = LearnedFamilySimulator(harness, labels, 2., .2)
    keys_of_row = coach_reference.row_keys(harness)
    solved = 0
    for world in worlds:
        views = agent.views(world['stream'], rng)
        for coach, budget in ((UNHEDGED, 256), (CHAMPION, 1024)):
            trace = []
            agent.lifetime(coach, views, prior, budget, trace=trace)
            expected = learned_reference.lifetime(harness, keys_of_row, views, prior, coach,
                                                  budget, groups=(labels, 2., .2))
            assert [(d['pick'], d['hit']) for d in trace] == expected
            solved += sum(d['hit'] for d in trace)
    assert solved > 0


def test_unseen_atoms_form_one_extra_group():
    harness = Harness()
    keys = len(harness.key_names)
    labels = np.full(keys, -1)
    labels[:100] = np.arange(100) % 4
    agent = LearnedFamilySimulator(harness, labels, 2., .2)
    assert set(agent.family_of[:100]) == {0, 1, 2, 3}
    assert (agent.family_of[100:] == 4).all()
    assert len(agent.triples) == 10 and agent.contains.sum(axis=1).tolist() == [3.] * 10
    evidence = np.zeros(keys)
    evidence[0] = 1.
    marginals = agent.family_marginals(evidence)
    assert marginals[0] > marginals[1]
