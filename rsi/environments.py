"""Environments drawn from a meta-distribution (Phase 2).

In the mechanism environment every world is a union of three syntactic
families, so the structure a representation learner must find is the same in
every environment and a researcher can write the right learner down. Here the
structure is itself drawn: an environment partitions the atoms at random into
`groups` groups, each world picks `per_world` of them and draws its atoms from
their union, each atom slipping to a uniformly random atom with probability
`slip`. A held-out environment is then a random variable, and which level-2
configuration suits it is something a learner could only know from experience
of environments.
"""
from __future__ import annotations

import random

import numpy as np

from .learned_groups import _affinity, _cluster, log_likelihood
from .mechanism_space import world_members

GROUP_COUNTS = (6, 9, 12)
PER_WORLD = (2, 3, 4)
SLIPS = (0., .15)


def make_environment(harness, seed, theta=None):
    """`theta` fixes the environment's parameters; otherwise they are drawn.
    `skew` > 0 draws group sizes from a symmetric Dirichlet with that
    concentration (smaller is more uneven); 0 makes them equal."""
    rng = random.Random(seed)
    if theta is None:
        theta = {'groups': rng.choice(GROUP_COUNTS), 'per_world': rng.choice(PER_WORLD),
                 'slip': rng.choice(SLIPS), 'skew': 0.}
    keys = list(range(len(harness.key_names)))
    rng.shuffle(keys)
    groups = theta['groups']
    if theta.get('skew'):
        shares = np.random.default_rng(seed).dirichlet([theta['skew']] * groups)
        # every group keeps at least 14 atoms, so a world can always be drawn
        sizes = 14 + np.floor(shares * (len(keys) - 14 * groups)).astype(int)
        sizes[-1] = len(keys) - sizes[:-1].sum()
    else:
        sizes = np.full(groups, len(keys) // groups)
        sizes[:len(keys) % groups] += 1
    labels = np.repeat(np.arange(groups), sizes)[np.argsort(keys)]
    return {'seed': seed, 'theta': theta, 'labels': labels}


def sample_world(harness, environment, rng, keys_per_world, minimum, attempts=40):
    theta, labels = environment['theta'], environment['labels']
    everything = len(harness.key_names)
    for _ in range(attempts):
        chosen = rng.sample(range(theta['groups']), theta['per_world'])
        pool = [k for k in range(everything) if labels[k] in chosen]
        keys = set()
        while len(keys) < keys_per_world:
            keys.add(rng.randrange(everything) if rng.random() < theta['slip']
                     else rng.choice(pool))
        names = sorted(harness.key_names[k] for k in keys)
        members = world_members(harness.catalog, harness.by_key, names)
        if len(members) >= minimum:
            return {'keys': tuple(names), 'groups': tuple(sorted(chosen)), 'members': members}
    return None


def draw(harness, environment, count, rng, keys_per_world, minimum, stream):
    out = []
    while len(out) < count:
        world = sample_world(harness, environment, rng, keys_per_world, minimum)
        if world is None:
            continue
        members = list(world['members'])
        rng.shuffle(members)
        world['stream'] = members[:stream]
        out.append(world)
    return out


def learn(observed_sets, keys, per_world, choices=range(3, 13), seed=0):
    """`learned_groups.learn_groups(select='likelihood')` with the per-world
    group count of its likelihood as a parameter; that module is frozen."""
    cut = len(observed_sets) * 4 // 5
    fit_seen, fit_affinity = _affinity(observed_sets[:cut], keys)
    choices = [g for g in choices if g > per_world and g < len(fit_seen)]
    scores = {g: log_likelihood(observed_sets[cut:],
                                _cluster(fit_seen, fit_affinity, g, keys, seed),
                                per_world=per_world)
              for g in choices}
    groups = max(scores, key=scores.get)
    seen, affinity = _affinity(observed_sets, keys)
    return _cluster(seen, affinity, groups, keys, seed), groups
