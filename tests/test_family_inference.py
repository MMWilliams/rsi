"""The family-inference agent must make the same decisions as its semantics
written directly, or its gains are gains of something else."""
from __future__ import annotations

import random

import numpy as np
import pytest

from rsi import coach_reference, family_reference
from rsi.family_inference import FamilySimulator
from rsi.growth_coach import CHAMPION, UNHEDGED, Coach, Prior, draw_worlds, observed_sets, triples
from rsi.mechanism_worlds import Harness


@pytest.fixture(scope='module')
def setup():
    harness = Harness()
    harness.set_tiebreak(611101 + 77)
    rng = random.Random(9)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    pool = triples(harness, seen, rng, 14, 130)
    worlds = draw_worlds(harness, pool, 3, rng, 14, 130, 30)
    reserved = {index for world in worlds for index in world['stream']}
    training = draw_worlds(harness, pool, 60, rng, 14, 130, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, 64, rng))
    simulator = FamilySimulator(harness, [], 2., .2)
    views = [simulator.views(world['stream'], rng) for world in worlds]
    return harness, simulator, prior, views


@pytest.mark.parametrize('coach', [UNHEDGED, CHAMPION, Coach(hedge=.25, hedge_slope=.17)])
@pytest.mark.parametrize('budget', [256, 1024])
def test_family_agent_matches_its_semantics(setup, coach, budget):
    harness, simulator, prior, views = setup
    keys_of_row = coach_reference.row_keys(harness)
    solved = 0
    for world_views in views:
        trace = []
        simulator.lifetime(coach, world_views, prior, budget, trace=trace)
        expected = family_reference.lifetime(harness, keys_of_row, world_views, prior, coach,
                                             budget, family=(2., .2))
        assert [(d['pick'], d['hit']) for d in trace] == expected
        solved += sum(d['hit'] for d in trace)
    assert solved > 0


def test_uniform_prior_and_posterior(setup):
    _harness, simulator, _prior, _views = setup
    evidence = np.zeros(simulator.keys)
    marginals = simulator.family_marginals(evidence)
    assert np.allclose(marginals, 3 / len(marginals))
    evidence[0] = 1.
    shifted = simulator.family_marginals(evidence)
    assert shifted[simulator.family_of[0]] > marginals[simulator.family_of[0]]
