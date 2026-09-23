"""Does cross-world experience keep moving the tight-budget wall?

Two coach screens and a near-miss probe (`mechanism-coach-screen-20260922.json`,
`mechanism-coach-screen2-20260923.json`, `mechanism-near-miss-probe-20260923.json`)
put the earned loop's tight-budget gap down to information: before its first
solve the agent's window is set by the cross-world prior alone, near-misses in
that window carry no signal about the world, and no policy over the evidence
the loop has closes more than about 2% of the gap to the informed ceiling at
budget 256.

The one source of information that acts before the first solve is the prior,
and its value has only been measured up to 400 training worlds and at budgets
1024 and 4096 (`mechanism-compounding-20260921.json`, rising and unsaturated).
This measures the champion earned loop (cold-start pair prior, half hedged)
with the prior fitted on 25, 100, 400, 1600 and 6400 training worlds, at every
budget from 128 to 4096, on held-out worlds of trained family combinations,
of untrained combinations, and of an untrained family.

Controls at 6400 worlds: the same estimator fitted on worlds drawn without
family structure, and the structured prior with atom labels permuted. The
unhedged prior at 6400 is reported beside the hedged one.

If tight-budget solves keep rising with worlds, the wall is data-limited and
cross-world experience is the lever to build on; if they flatten, the prior's
form is the limit. Development evidence.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Pool, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.mechanism_space import world_members
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-prior-scaling-20260923.json'
SEED = 623101
SIZES = (25, 100, 400, 1600, 6400)
PRIOR_SOLVED = 64
EVAL_WORLDS = 32
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WORKERS = 12
BOOT = 20000


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

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

    training = draw_worlds(harness, train_triples, max(SIZES), rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    seen_keys = [key for key in harness.key_names if key.split(':')[0] in seen]
    uniform = []
    while len(uniform) < max(SIZES):
        chosen = rng.sample(seen_keys, KEYS_PER_WORLD)
        members = world_members(harness.catalog, harness.by_key, chosen)
        if len(members) >= MINIMUM_MEMBERS:
            uniform.append({'members': members})
    structured_sets = observed_sets(harness, training, reserved, PRIOR_SOLVED, rng)
    uniform_sets = observed_sets(harness, uniform, reserved, PRIOR_SOLVED, rng)
    priors = {f'structured:{size}': Prior(harness, structured_sets[:size]) for size in SIZES}
    priors['uniform'] = Prior(harness, uniform_sets)
    priors['permuted'] = priors[f'structured:{max(SIZES)}'].permuted(
        harness, np.random.default_rng(SEED + 5).permutation(len(harness.key_names)))
    views = {f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}
    print('setup', round(time.perf_counter() - wall), 's', flush=True)

    arms = {'blind': (BLIND, 'earned', f'structured:{max(SIZES)}')}
    arms.update({f'prior@{size}': (CHAMPION, 'earned', f'structured:{size}') for size in SIZES})
    arms.update({f'unhedged@{max(SIZES)}': (UNHEDGED, 'earned', f'structured:{max(SIZES)}'),
                 'uniform@6400': (CHAMPION, 'earned', 'uniform'),
                 'permuted@6400': (CHAMPION, 'earned', 'permuted'),
                 'revealed': (BLIND, 'revealed', f'structured:{max(SIZES)}')})

    pool = Pool(WORKERS, SEED + 77, priors, views, BUDGETS)
    table = {}
    for group in groups:
        results = pool.map([(coach, world, arm, prior) for coach, arm, prior in arms.values()
                            for world in names[group]])
        table[group] = {}
        for number, name in enumerate(arms):
            chunk = results[number * len(names[group]):(number + 1) * len(names[group])]
            table[group][name] = np.array([[int(hits.sum()) for hits in per_world]
                                           for per_world in chunk])
    pool.close()

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, EVAL_WORLDS, (BOOT, EVAL_WORLDS))
    largest = f'prior@{max(SIZES)}'
    result = {'scope': 'earned-loop value of the cross-world prior against worlds seen',
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'seed': SEED, 'sizes': list(SIZES), 'budgets': list(BUDGETS), 'stream': STREAM,
              'held_out_families': list(HELD_OUT_FAMILIES),
              'new_triples': [list(t) for t in new_triples], 'groups': {}}
    for group, arms_ in table.items():
        block = {'solved_mean_by_budget': {name: values.mean(axis=0).tolist()
                                           for name, values in arms_.items()},
                 'per_world': {name: values.tolist() for name, values in arms_.items()},
                 'contrasts': {}}
        pairs = [(f'prior@{size}', 'blind') for size in SIZES]
        pairs += [(f'prior@{b}', f'prior@{a}') for a, b in zip(SIZES, SIZES[1:])]
        pairs += [(largest, 'uniform@6400'), (largest, 'permuted@6400'),
                  (largest, f'unhedged@{max(SIZES)}')]
        for left, right in pairs:
            difference = arms_[left] - arms_[right]
            sums = difference[draws].sum(axis=1)
            block['contrasts'][f'{left} - {right}'] = {
                'sum': difference.sum(axis=0).tolist(),
                'low': np.percentile(sums, 2.5, axis=0).tolist(),
                'high': np.percentile(sums, 97.5, axis=0).tolist()}
        result['groups'][group] = block
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for group, block in result['groups'].items():
        print(f'\n== {group}: mean tasks solved of {STREAM}, by budget')
        print('arm'.ljust(16) + ''.join(str(b).rjust(8) for b in BUDGETS))
        for name, values in block['solved_mean_by_budget'].items():
            print(name.ljust(16) + ''.join('{:8.1f}'.format(v) for v in values))
        for name, entry in block['contrasts'].items():
            print('  {:28s}'.format(name) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(entry['sum'], entry['low'], entry['high'])))
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
