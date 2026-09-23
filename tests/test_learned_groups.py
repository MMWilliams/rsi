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
