"""Family inference outside the families and combinations it was trained on.

`mechanism-family-inference-probe-20260923.json`: inferring a world's family
triple from the agent's own evidence recovers about half of what a family
oracle buys at budgets 128-512, in support and unhedged. Every acquired prior
in this line of work has failed out of support, and unhedged priors worst of
all at generous budgets. This scores the same model on worlds of trained
combinations, untrained combinations and an untrained family, at every budget,
unhedged, half-hedged, and with the budget-dependent hedge the RL coach learned
in its first development run (none at 128-256, rising to 0.59 at 4096).
Development evidence.
"""
from __future__ import annotations

import multiprocessing
import random
import sys
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.family_inference import FamilySimulator
from rsi.growth_coach import (CHAMPION, UNHEDGED, Coach, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.mechanism_worlds import Harness
from mechanism_oracle_structure_probe import oracle

OUT = ROOT / 'analysis/mechanism-family-inference-support-20260923.json'
SEED = 629101
WORLDS = 32
STREAM = 100
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WEIGHT, SLIP = 2., .2
SLOPED = Coach(hedge=.25, hedge_slope=.17)
WORKERS = 4
BOOT = 20000
_STATE = {}


def setup():
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    plain = Simulator(harness)
    rng = random.Random(SEED)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    seen_pool = triples(harness, seen, rng, 14, 130)
    rng.shuffle(seen_pool)
    cut = max(1, round(.2 * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held = [t for t in triples(harness, harness.by_family, rng, 14, 130)
            if set(t) & {'popcount', 'xormod'}]
    groups = {g: draw_worlds(harness, p, WORLDS, rng, 14, 130, STREAM)
              for g, p in (('seen_triple', train_triples), ('new_triple', new_triples),
                           ('new_family', held))}
    reserved = {i for ws in groups.values() for w in ws for i in w['stream']}
    training = draw_worlds(harness, train_triples, 400, rng, 14, 130, 0)
    learned = Prior(harness, observed_sets(harness, training, reserved, 64, rng))
    views = {(g, n): plain.views(w['stream'], rng) for g, ws in groups.items()
             for n, w in enumerate(ws)}
    return harness, plain, learned, training, groups, views


def _init():
    harness, plain, learned, training, groups, views = setup()
    _STATE.update(harness=harness, plain=plain, learned=learned, groups=groups, views=views,
                  family=FamilySimulator(harness, [t['triple'] for t in training], WEIGHT, SLIP))


def _world(key):
    group, number = key
    s = _STATE
    world = s['groups'][group][number]
    families = oracle(s['harness'], s['learned'],
                      [k for f in world['triple'] for k in s['harness'].by_family[f]])
    runs = {'champion': (s['plain'], CHAMPION, s['learned']),
            'warm': (s['plain'], UNHEDGED, s['learned']),
            'family oracle': (s['plain'], UNHEDGED, families),
            'infer unhedged': (s['family'], UNHEDGED, s['learned']),
            'infer hedged': (s['family'], CHAMPION, s['learned']),
            'infer sloped hedge': (s['family'], SLOPED, s['learned'])}
    return {arm: [int(sim.lifetime(coach, s['views'][key], prior, b).sum()) for b in BUDGETS]
            for arm, (sim, coach, prior) in runs.items()}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    keys = [(g, n) for g in ('seen_triple', 'new_triple', 'new_family') for n in range(WORLDS)]
    with multiprocessing.get_context('spawn').Pool(WORKERS, initializer=_init) as pool:
        rows = pool.map(_world, keys, chunksize=1)
    arms = list(rows[0])
    result = {'scope': 'family inference in and out of support', 'seed': SEED,
              'weight': WEIGHT, 'slip': SLIP, 'budgets': list(BUDGETS), 'groups': {}}
    draws = np.random.default_rng(SEED + 3).integers(0, WORLDS, (BOOT, WORLDS))
    for group in ('seen_triple', 'new_triple', 'new_family'):
        totals = {arm: np.array([row[arm] for key, row in zip(keys, rows) if key[0] == group])
                  for arm in arms}
        block = {'mean_by_budget': {a: v.mean(axis=0).tolist() for a, v in totals.items()},
                 'per_world': {a: v.tolist() for a, v in totals.items()}, 'contrasts': {}}
        for arm in arms[1:]:
            difference = totals[arm] - totals['champion']
            sums = difference[draws].sum(axis=1)
            block['contrasts'][arm] = {'sum': difference.sum(axis=0).tolist(),
                                       'low': np.percentile(sums, 2.5, axis=0).tolist(),
                                       'high': np.percentile(sums, 97.5, axis=0).tolist()}
        result['groups'][group] = block
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)
    for group, block in result['groups'].items():
        print(f'\n== {group}: mean solved of 100 by budget {BUDGETS}; minus champion [interval]')
        for arm in arms:
            line = '  {:20s}'.format(arm) + ''.join('{:6.1f}'.format(v)
                                                    for v in block['mean_by_budget'][arm])
            if arm in block['contrasts']:
                e = block['contrasts'][arm]
                line += ' |' + ''.join('{:+5.0f}[{:.0f},{:.0f}]'.format(s, lo, hi).rjust(16)
                                       for s, lo, hi in zip(e['sum'], e['low'], e['high']))
            print(line)


if __name__ == '__main__':
    sys.exit(main())
