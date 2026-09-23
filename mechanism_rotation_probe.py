"""Does rotating part of the window help at tight budgets?

Until its evidence changes, the earned loop scans the same head of its
ordering for every task. `Coach.rotate` spends a share of each task's scans on
a slice further down the ordering that moves on every task. Immediate hits per
task can only fall (the slice is ranked lower than the head it displaces); the
question is whether the diversity of what is found pays that back through the
loop.

Single-lever check on the two coach screens' worlds (same seed), beside the
champion and screen 2's in-sample optimum. Rotation earns a place in a third
screen only if one rotation arm beats the champion by at least 0.10 of the gap
to the ceiling at budget 256 or 512 on in-support worlds without losing to it
on out-of-support worlds. Development evidence.
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

OUT = ROOT / 'analysis/mechanism-rotation-probe-20260923.json'
SCREEN = ROOT / 'analysis/mechanism-coach-screen2-20260923.json'
SEED = 620101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WORKERS = 3


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    screen = json.loads(SCREEN.read_text())
    best = Coach(**screen['in_sample_best'])
    arms = {'champion': CHAMPION, 'rotate=0.25': Coach(rotate=.25),
            'rotate=0.5': Coach(rotate=.5), 'screen2_best': best,
            'screen2_best+rotate=0.25': Coach(**{**best.as_dict(), 'rotate': .25}),
            'screen2_best+rotate=0.5': Coach(**{**best.as_dict(), 'rotate': .5})}

    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    simulator = Simulator(harness)
    rng = random.Random(SEED)
    seen = [family for family in harness.by_family if family not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {'seen': draw_worlds(harness, seen_pool, 32, rng, KEYS_PER_WORLD,
                                  MINIMUM_MEMBERS, STREAM),
              'new_family': draw_worlds(harness, held_pool, 16, rng, KEYS_PER_WORLD,
                                        MINIMUM_MEMBERS, STREAM)}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, seen_pool, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, PRIOR_SOLVED, rng))
    views = {f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}

    pool = Pool(WORKERS, SEED + 77, {'main': prior}, views, BUDGETS)
    table = {}
    for group in groups:
        results = pool.map([(coach, world, 'earned', 'main') for coach in arms.values()
                            for world in names[group]])
        table[group] = {}
        for number, name in enumerate(arms):
            chunk = results[number * len(names[group]):(number + 1) * len(names[group])]
            table[group][name] = np.array([[int(h.sum()) for h in w] for w in chunk])
    pool.close()

    for group in groups:
        assert table[group]['champion'].sum(axis=0).tolist() == \
            screen['groups'][group]['champion']['total_by_budget'], group
    gap = {g: np.maximum(np.array(screen['groups'][g]['revealed']['total_by_budget'])
                         - table[g]['champion'].sum(axis=0), 1) for g in groups}
    gains = {g: {name: ((v.sum(axis=0) - table[g]['champion'].sum(axis=0)) / gap[g]).tolist()
                 for name, v in table[g].items()} for g in groups}
    passes = [name for name in arms if name != 'champion'
              and max(gains['seen'][name][1], gains['seen'][name][2]) >= .10
              and min(gains['new_family'][name]) >= 0]
    result = {'scope': 'window rotation at tight budgets', 'seed': SEED,
              'budgets': list(BUDGETS), 'arms': {n: c.as_dict() for n, c in arms.items()},
              'groups': {g: {n: {'total_by_budget': v.sum(axis=0).tolist(),
                                 'per_world': v.tolist()} for n, v in a.items()}
                         for g, a in table.items()},
              'gain_share_of_gap': gains, 'earns_a_screen': passes,
              'wall_seconds': time.perf_counter() - wall}
    write_json(OUT, result)
    for group in groups:
        print(f'\n== {group}: tasks solved, summed over worlds; gain as share of gap')
        for name, values in table[group].items():
            print(name.ljust(26) + ''.join('{:7d}'.format(int(v)) for v in values.sum(axis=0))
                  + '   ' + ' '.join('{:+.3f}'.format(x) for x in gains[group][name]))
    print('\nearns a third screen:', passes or 'none')
    print('{:.0f}s'.format(result['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
