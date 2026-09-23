"""Re-score every arm the soft-retention bug touched.

Until 2026-09-23 `Simulator.lifetime` credited soft evidence through a local
named `share`, which is also the hedge share, so a coach with soft retention
dropped its hedge to soft/n after its first window with several consistent
candidates. The replay check of `audit_mechanism_coach_confirmation.py` found
it; `tests/test_growth_coach.py::test_soft_retention_keeps_the_hedge` fails on
the old code.

Every evaluated arm with soft retention above zero is re-scored here on the
same held-out worlds, rebuilt from each run's seed; the champion is re-scored
too and must reproduce the stored totals exactly, which checks the rebuild.
Coaches with soft exactly zero never reached the faulty line and are
unaffected, as are the other arms of these runs. Training runs whose
perturbations had soft above zero were affected in a way no re-scoring can
repair; that is recorded in `COACH-RESULTS-2026-09-23.md`.
"""
from __future__ import annotations

import json
import random
import sys
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import (CHAMPION, Coach, Pool, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-rescore-20260923.json'
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
BOOT = 20000


def screen_setup(harness, simulator, seed):
    rng = random.Random(seed)
    seen = [f for f in harness.by_family if f not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    held_pool = [t for t in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                    MINIMUM_MEMBERS) if set(t) & set(HELD_OUT_FAMILIES)]
    groups = {'seen': draw_worlds(harness, seen_pool, 32, rng, KEYS_PER_WORLD,
                                  MINIMUM_MEMBERS, 100),
              'new_family': draw_worlds(harness, held_pool, 16, rng, KEYS_PER_WORLD,
                                        MINIMUM_MEMBERS, 100)}
    return finish(harness, simulator, rng, seen_pool, groups)


def dev_setup(harness, simulator, seed):
    rng = random.Random(seed)
    seen = [f for f in harness.by_family if f not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    rng.shuffle(seen_pool)
    cut = max(1, round(.2 * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held_pool = [t for t in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                    MINIMUM_MEMBERS) if set(t) & set(HELD_OUT_FAMILIES)]
    groups = {g: draw_worlds(harness, p, 32, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS, 100)
              for g, p in (('seen_triple', train_triples), ('new_triple', new_triples),
                           ('new_family', held_pool))}
    return finish(harness, simulator, rng, train_triples, groups)


def finish(harness, simulator, rng, train_pool, groups):
    reserved = {i for worlds in groups.values() for w in worlds for i in w['stream']}
    training = draw_worlds(harness, train_pool, 400, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, 64, rng))
    views = {f'{g}:{n:02d}': simulator.views(w['stream'], rng)
             for g, worlds in groups.items() for n, w in enumerate(worlds)}
    return prior, views, {g: [k for k in views if k.startswith(g + ':')] for g in groups}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    load = lambda name: json.loads((ROOT / f'analysis/{name}.json').read_text())
    screen = load('mechanism-coach-screen-20260922')
    dev1 = load('mechanism-coach-dev-20260923')
    fixed = load('mechanism-coach-fixed-hedge-dev-20260923')
    practice = load('mechanism-coach-practice-dev-20260923')
    runs = [
        ('screen', 620101, screen_setup, screen,
         lambda block, arm: block[arm]['per_world'],
         {'soft=0.5': (Coach(soft=.5), BUDGETS), 'soft=1': (Coach(soft=1.), BUDGETS)}),
        ('dev', 621101, dev_setup, dev1, lambda block, arm: block['per_world'][arm],
         {'coach@10': (Coach(**dev1['checkpoints']['10']), BUDGETS),
          'per_budget@128': (Coach(**dev1['per_budget']['128']), (128,)),
          'per_budget@256': (Coach(**dev1['per_budget']['256']), (256,))}),
        ('fixed_hedge', 625101, dev_setup, fixed, lambda block, arm: block['per_world'][arm],
         {'random_search': (Coach(**fixed['random_search']), BUDGETS)}),
        ('practice', 626101, dev_setup, practice, lambda block, arm: block['per_world'][arm],
         {'both@10': (Coach(**practice['checkpoints']['both']['10']), BUDGETS),
          'both@40': (Coach(**practice['checkpoints']['both']['40']), BUDGETS)}),
    ]
    result = {'scope': 're-scoring arms affected by the soft-retention bug', 'runs': {}}
    for name, seed, setup, stored, stored_totals, arms in runs:
        harness = Harness()
        harness.set_tiebreak(seed + 77)
        simulator = Simulator(harness)
        prior, views, names = setup(harness, simulator, seed)
        pool = Pool(12, seed + 77, {'main': prior}, views, BUDGETS)
        block = {}
        for group, worlds in names.items():
            stored_group = stored['groups'][group]
            champion = np.array([[int(h.sum()) for h in r] for r in pool.map(
                [(CHAMPION, w, 'earned', 'main') for w in worlds])])
            reproduced = champion.tolist() == stored_totals(stored_group, 'champion')
            entry = {'champion_reproduced': reproduced, 'arms': {}}
            for arm, (coach, budgets) in arms.items():
                totals = np.array([[int(h.sum()) for h in r] for r in pool.map(
                    [(coach, w, 'earned', 'main', budgets) for w in worlds])])
                columns = [BUDGETS.index(b) for b in budgets]
                difference = totals - champion[:, columns]
                draws = np.random.default_rng(seed + 3).integers(0, len(worlds),
                                                                 (BOOT, len(worlds)))
                sums = difference[draws].sum(axis=1)
                key = arm.split('@')[0] if arm.startswith('per_budget') else arm
                old = np.array(stored_totals(stored_group, key))[:, columns]
                entry['arms'][arm] = {
                    'budgets': list(budgets), 'minus_champion': difference.sum(axis=0).tolist(),
                    'low': np.percentile(sums, 2.5, axis=0).tolist(),
                    'high': np.percentile(sums, 97.5, axis=0).tolist(),
                    'before_fix_minus_champion': (old - champion[:, columns]).sum(axis=0).tolist()}
            block[group] = entry
            print(f'{name} {group}: champion reproduced {reproduced}', flush=True)
            for arm, e in entry['arms'].items():
                print('  {:16s} now'.format(arm) + ''.join(
                    '{:+6.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(18)
                    for s, lo, hi in zip(e['minus_champion'], e['low'], e['high'])))
                print('  {:16s} was'.format('') + ''.join(
                    '{:+6.0f}'.format(s).rjust(18) for s in e['before_fix_minus_champion']))
        pool.close()
        result['runs'][name] = {'seed': seed, 'groups': block}
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
