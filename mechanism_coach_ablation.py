"""Which of the trained coach's levers costs it at tight budgets?

`mechanism-coach-fixed-hedge-dev-20260923.json`: the coach trained with the
hedge share fixed improves every budget from 1024 up on every split and loses
96 [29, 169] at budget 128 on untrained family combinations, more with
training. This resets one lever at a time to its champion value, on the same
held-out worlds and seed, and reports the change at the three tight budgets.
Development evidence.
"""
from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import replace

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import (CHAMPION, Coach, Pool, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-ablation-20260923.json'
DEV = ROOT / 'analysis/mechanism-coach-fixed-hedge-dev-20260923.json'
SEED = 625101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 32
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512)
LEVERS = ('unknown', 'pair', 'count', 'depth1', 'affinity', 'soft', 'pick', 'tilt')
BOOT = 20000


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    dev = json.loads(DEV.read_text())
    coach = Coach(**dev['checkpoints']['40'])

    # The dev run's setup, reproduced draw for draw up to the evaluation views.
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    simulator = Simulator(harness)
    rng = random.Random(SEED)
    seen = [family for family in harness.by_family if family not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    rng.shuffle(seen_pool)
    cut = max(1, round(NEW_TRIPLE_SHARE * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {name: draw_worlds(harness, pool_, EVAL_WORLDS, rng, KEYS_PER_WORLD,
                                MINIMUM_MEMBERS, STREAM)
              for name, pool_ in (('seen_triple', train_triples), ('new_triple', new_triples),
                                  ('new_family', held_pool))}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, train_triples, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, PRIOR_SOLVED, rng))
    # The dev run built its practice priors here; they draw nothing from `rng`.
    views ={f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}

    arms = {'champion': CHAMPION, 'coach': coach}
    arms.update({f'reset {lever}': replace(coach, **{lever: getattr(CHAMPION, lever)})
                 for lever in LEVERS})
    arms['only tilt'] = replace(CHAMPION, tilt=coach.tilt)
    pool = Pool(12, SEED + 77, {'main': prior}, views, BUDGETS)
    table = {}
    for group in groups:
        results = pool.map([(c, world, 'earned', 'main') for c in arms.values()
                            for world in names[group]])
        table[group] = {name: np.array([[int(h.sum()) for h in w] for w in
                                        results[i * len(names[group]):(i + 1) * len(names[group])]])
                        for i, name in enumerate(arms)}
    pool.close()

    reproduced = {g: table[g]['coach'].mean(axis=0).tolist() ==
                  dev['groups'][g]['solved_mean_by_budget']['coach@40'][:3] for g in groups}
    draws = np.random.default_rng(SEED + 3).integers(0, EVAL_WORLDS, (BOOT, EVAL_WORLDS))
    result = {'scope': 'lever ablation of the fixed-hedge coach at tight budgets',
              'coach': coach.as_dict(), 'reproduced_dev': reproduced, 'budgets': list(BUDGETS),
              'groups': {}}
    for group, arms_ in table.items():
        block = {}
        for name, values in arms_.items():
            difference = values - arms_['champion']
            sums = difference[draws].sum(axis=1)
            block[name] = {'minus_champion': difference.sum(axis=0).tolist(),
                           'low': np.percentile(sums, 2.5, axis=0).tolist(),
                           'high': np.percentile(sums, 97.5, axis=0).tolist()}
        result['groups'][group] = block
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)
    print('dev run reproduced:', reproduced)
    for group, block in result['groups'].items():
        print(f'\n== {group}: minus champion at budgets {BUDGETS}')
        for name, entry in block.items():
            print('  {:16s}'.format(name) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(entry['minus_champion'], entry['low'], entry['high'])))


if __name__ == '__main__':
    sys.exit(main())
