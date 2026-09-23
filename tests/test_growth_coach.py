"""The coach simulator must reproduce the audited earned-loop arms exactly, or
every comparison against them is a comparison against something else."""
from __future__ import annotations

import random

import numpy as np
import pytest

from rsi.growth_coach import (BLIND, CHAMPION, FLOOR, UNHEDGED, Coach, Prior, Simulator,
                              draw_worlds, observed_sets, triples)
from rsi import coach_reference
from rsi.mechanism_worlds import Harness, interleave, ranks_of


@pytest.fixture(scope='module')
def setup():
    harness = Harness()
    harness.set_tiebreak(611101 + 77)
    simulator = Simulator(harness)
    rng = random.Random(5)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    pool = triples(harness, seen, rng, 14, 130)
    worlds = draw_worlds(harness, pool, 3, rng, 14, 130, 40)
    reserved = {index for world in worlds for index in world['stream']}
    training = draw_worlds(harness, pool, 60, rng, 14, 130, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, 64, rng))
    views = [simulator.views(world['stream'], rng) for world in worlds]
    return harness, simulator, prior, views


def reference(harness, views, prior, budget, arm):
    """A port of the loop in `mechanism_hedged_start.py`, full sorts and all."""
    keys = len(harness.key_names)
    neutral = np.zeros(harness.catalog.size)
    prior_rows = prior.pair_rows

    def order_for(known_rows):
        if arm in ('blind', 'revealed', 'static'):
            return harness.order_from_row_scores(known_rows)
        prior_order = harness.order_from_row_scores(known_rows + prior_rows)
        if arm == 'warm':
            return prior_order
        return interleave(prior_order, harness.order_from_row_scores(known_rows), .5)

    known, known_rows = set(), neutral
    position = ranks_of(order_for(known_rows))
    hits = []
    for view in views:
        ranked = position[view['rows']]
        inside = np.flatnonzero(ranked < budget)
        pick = int(inside[0]) if len(inside) else -1
        hits.append(int(pick >= 0 and view['good'][pick]))
        if arm == 'static':
            continue
        if arm == 'revealed':
            learned = view['mechanism']
        elif pick >= 0:
            learned = int(view['rows'][pick])
        else:
            continue
        fresh = {harness.key_index[key] for key in harness.catalog.keys(learned)} - known
        if not fresh:
            continue
        known |= fresh
        score = np.zeros(keys)
        score[sorted(known)] = 1.
        known_rows = harness.row_scores(np.log(score + FLOOR))
        position = ranks_of(order_for(known_rows))
    return np.array(hits)


@pytest.mark.parametrize('arm,coach,mode', [
    ('static', BLIND, 'static'), ('blind', BLIND, 'earned'), ('warm', UNHEDGED, 'earned'),
    ('warm_hedge50', CHAMPION, 'earned'), ('revealed', BLIND, 'revealed')])
@pytest.mark.parametrize('budget', [256, 1024])
def test_reproduces_the_original_arms(setup, arm, coach, mode, budget):
    harness, simulator, prior, views = setup
    for world_views in views:
        expected = reference(harness, world_views, prior, budget, arm)
        got = simulator.lifetime(coach, world_views, prior, budget, arm=mode)
        assert np.array_equal(got, expected)


def test_windows_match_full_sorts(setup):
    harness, simulator, _prior, _views = setup
    rng = np.random.default_rng(3)
    n = harness.catalog.size
    for trial in range(6):
        first = rng.integers(0, 40, n).astype(np.float64)
        second = rng.integers(0, 7, n).astype(np.float64)
        rows = rng.choice(n, 60, replace=False)
        for budget in (1, 128, 1024, 4096):
            order = ranks_of(harness.order_from_row_scores(first))
            assert np.array_equal(simulator.inside(rows, first, budget), order[rows] < budget)
            top = simulator.top(first, budget)
            assert np.array_equal(top, harness.order_from_row_scores(first)[:budget])
            for share in (.25, .5, .75):
                merged = ranks_of(interleave(harness.order_from_row_scores(first),
                                             harness.order_from_row_scores(second), share))
                assert np.array_equal(
                    simulator.inside_hedged(rows, first, second, share, budget),
                    merged[rows] < budget)
                assert np.array_equal(
                    simulator.ranked((first, second), budget, share),
                    interleave(harness.order_from_row_scores(first),
                               harness.order_from_row_scores(second), share)[:budget])


def test_levers_change_behaviour(setup):
    _harness, simulator, prior, views = setup
    base = sum(simulator.lifetime(CHAMPION, v, prior, 1024).sum() for v in views)
    assert base >= 0
    for coach in (Coach(count=1.), Coach(affinity=1.), Coach(soft=1.), Coach(pick=1.),
                  Coach(depth1=3.), Coach(unknown=.5), Coach(tilt=.5),
                  Coach(hedge_slope=-.25), Coach(rotate=.5), Coach(rotate=.3, tilt=.5)):
        for world_views in views:
            hits = simulator.lifetime(coach, world_views, prior, 1024)
            assert hits.shape == (len(world_views),)


def test_vector_round_trip():
    coach = Coach(unknown=.7, pair=1.3, count=.2, depth1=-1., affinity=.4, soft=.3,
                  pick=.5, hedge=.4, hedge_slope=-.1, tilt=.3, rotate=.2)
    assert Coach.from_vector(coach.vector()) == coach
    assert Coach(soft=3., hedge=2., unknown=-1.).clipped() == Coach(soft=1., hedge=.95,
                                                                    unknown=0.)


def test_allocation_keeps_the_total():
    for tilt in (-.9, -.3, .4, .9):
        allotted = Coach(tilt=tilt).budgets(256, 100)
        assert abs(sum(allotted) - 256 * 100) <= 100
        assert (allotted[0] > allotted[-1]) == (tilt > 0)
    assert Coach().budgets(256, 100) == [256] * 100
    assert Coach(hedge_slope=-.25).share(4096) == .0
    assert Coach(hedge_slope=-.25).share(256) == .95
    assert CHAMPION.share(128) == .5


def test_guard_changes_only_the_hedged_half(setup):
    _harness, simulator, prior, views = setup
    for world_views in views:
        for budget in (256, 1024):
            assert np.array_equal(
                simulator.lifetime(CHAMPION, world_views, prior, budget, arm='guarded'),
                simulator.lifetime(CHAMPION, world_views, prior, budget))
    coach = Coach(count=1., depth1=-2.)
    guarded = sum(simulator.lifetime(coach, v, prior, 1024, arm='guarded').sum() for v in views)
    assert guarded >= 0


@pytest.mark.parametrize('coach,arm', [
    (Coach(count=.6, affinity=1.2, pick=.3, depth1=-1., tilt=.7, hedge=.25,
           hedge_slope=.17), 'earned'),
    (Coach(count=.6, affinity=1.2, pick=.3, depth1=-1., tilt=.7), 'guarded'),
    (Coach(unknown=1.5, pair=.7, soft=.4, depth1=1.2, hedge=0.), 'earned'),
    (Coach(rotate=.3, count=.2, hedge_slope=-.1), 'earned')])
def test_trained_levers_match_the_direct_semantics(setup, coach, arm):
    harness, simulator, prior, views = setup
    keys_of_row = coach_reference.row_keys(harness)
    for world_views in views[:2]:
        short = world_views[:25]
        for budget in (256, 1024):
            expected = coach_reference.lifetime(harness, keys_of_row, short, prior, coach,
                                                budget, arm)
            trace = []
            simulator.lifetime(coach, short, prior, budget, arm=arm, trace=trace)
            assert [(d['pick'], d['hit']) for d in trace] == expected, (coach, arm, budget)


def test_soft_retention_keeps_the_hedge(setup):
    """Soft credit once overwrote the hedge share inside `lifetime`, so any
    coach with soft retention silently dropped its hedge after its first
    window with several consistent candidates."""
    harness, simulator, prior, views = setup
    keys_of_row = coach_reference.row_keys(harness)
    coach = Coach(soft=.5, count=-.1, affinity=-.02, pick=.02, tilt=.01)
    exercised = 0
    for world_views in views:
        trace = []
        simulator.lifetime(coach, world_views, prior, 4096, trace=trace)
        exercised += sum(d['window_consistent'] > 1 and d['pick'] >= 0 for d in trace)
        expected = coach_reference.lifetime(harness, keys_of_row, world_views, prior, coach, 4096)
        assert [(d['pick'], d['hit']) for d in trace] == expected
    assert exercised
