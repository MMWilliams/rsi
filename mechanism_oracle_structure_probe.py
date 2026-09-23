"""How much could any representation of worlds buy at tight budgets?

`COACH-RESULTS-2026-09-23.md` §4 puts the earned loop's tight-budget gap down to
information: no policy over its evidence recovers more than about 2% of the gap
at budget 256, and the learned pair prior stops improving at about 400 training
worlds. The remaining question is whether a *better representation* of worlds
could cross it, or whether the generator itself leaves nothing to learn.

A world is 14 keys drawn uniformly from the keys of three families, so the most
any learner could ever know about a world before solving in it is which three
families it uses; within them nothing distinguishes one key from another. This
gives the agent that knowledge outright, per world, as an oracle prior (a row
scores 1 if both its atoms belong to the world's families, FLOOR otherwise), and
compares it with the learned pair prior at every budget. A second oracle gives
the world's 14 keys themselves at the start, which is the revealed ceiling's
knowledge without its per-task answers.

If the family oracle barely moves budgets 128-512, no representation can: the
wall is a property of the generator. If it moves them a lot, inferring families
early is the target. In-support worlds only, unhedged oracles, the learned
prior both hedged (champion) and unhedged. Development evidence.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, FLOOR, UNHEDGED, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-oracle-structure-probe-20260923.json'
SEED = 628101
WORLDS = 32
STREAM = 100
BUDGETS = (128, 256, 512, 1024)
BOOT = 20000


def oracle(harness, base, allowed):
    """A prior that knows which atoms the world may use."""
    clone = object.__new__(Prior)
    keys = len(harness.key_names)
    member = np.zeros(keys)
    member[[harness.key_index[k] for k in allowed]] = 1.
    clone._derive(harness, np.outer(member, member))
    clone.log_conditional = base.log_conditional
    return clone


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    simulator = Simulator(harness)
    rng = random.Random(SEED)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    pool = triples(harness, seen, rng, 14, 130)
    worlds = draw_worlds(harness, pool, WORLDS, rng, 14, 130, STREAM)
    reserved = {i for w in worlds for i in w['stream']}
    training = draw_worlds(harness, pool, 400, rng, 14, 130, 0)
    learned = Prior(harness, observed_sets(harness, training, reserved, 64, rng))

    arms = ('champion', 'warm', 'family oracle', 'key oracle', 'revealed')
    totals = {arm: np.zeros((WORLDS, len(BUDGETS))) for arm in arms}
    for number, world in enumerate(worlds):
        views = simulator.views(world['stream'], rng)
        families = oracle(harness, learned,
                          [k for f in world['triple'] for k in harness.by_family[f]])
        keys = oracle(harness, learned, world['keys'])
        setups = {'champion': (CHAMPION, learned, 'earned'), 'warm': (UNHEDGED, learned, 'earned'),
                  'family oracle': (UNHEDGED, families, 'earned'),
                  'key oracle': (UNHEDGED, keys, 'earned'),
                  'revealed': (BLIND, learned, 'revealed')}
        for arm, (coach, prior, mode) in setups.items():
            for b, budget in enumerate(BUDGETS):
                totals[arm][number, b] = simulator.lifetime(coach, views, prior, budget,
                                                            arm=mode).sum()
        print('world', number, 'done', round(time.perf_counter() - wall), 's', flush=True)

    draws = np.random.default_rng(SEED + 3).integers(0, WORLDS, (BOOT, WORLDS))
    result = {'scope': 'what knowing a world\'s families or keys buys the earned loop',
              'seed': SEED, 'budgets': list(BUDGETS), 'worlds': WORLDS,
              'mean_by_budget': {arm: v.mean(axis=0).tolist() for arm, v in totals.items()},
              'per_world': {arm: v.tolist() for arm, v in totals.items()}, 'contrasts': {}}
    for left in ('family oracle', 'key oracle', 'warm'):
        difference = totals[left] - totals['champion']
        sums = difference[draws].sum(axis=1)
        result['contrasts'][f'{left} - champion'] = {
            'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist()}
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)
    print('\nmean tasks solved of 100 by budget', BUDGETS)
    for arm, values in result['mean_by_budget'].items():
        print('  {:14s}'.format(arm) + ''.join('{:8.1f}'.format(v) for v in values))
    for name, entry in result['contrasts'].items():
        print('  {:24s}'.format(name) + ''.join(
            '{:+6.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(18)
            for s, lo, hi in zip(entry['sum'], entry['low'], entry['high'])))


if __name__ == '__main__':
    sys.exit(main())
