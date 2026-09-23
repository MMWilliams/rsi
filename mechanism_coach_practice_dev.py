"""Practice at the unfamiliarity the coach will be scored on.

`mechanism-coach-fixed-hedge-dev-20260923.json`: with the hedge share fixed,
the trained coach improves every budget from 1024 up on every split and loses
96 [29, 169] at budget 128 on untrained family combinations, more with
training. `mechanism-coach-ablation-20260923.json` puts the loss on one lever:
resetting the weight on repeated evidence to zero removes it (0 [-54, 53]). In
support a row picked again and again is usually right; under a combination
shift the agent keeps picking the same wrong rows and the weight entrenches
them. The coach learned that from lifetimes in which the prior was never
wrong about combinations.

It already practised one kind of unfamiliarity, a withheld family, and that
practice bought +19 to +228 on worlds of an untrained family
(`mechanism-coach-dev-20260923.json`). This adds the other kind the claim is
scored on: a world of one training combination, lived with a prior fitted on
the training worlds without that combination. Per generation, 4 in-support, 2
family-practice and 2 combination-practice lifetimes, each kind weighted
equally in the shaped fitness. Trained beside it, on the same held-out worlds,
is the previous procedure (6 in-support, 2 family-practice), so the two are
compared paired. Hedge share fixed at one half in both. Fresh seeds.

Development evidence.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Pool, Prior, Simulator, Trainer,
                              draw_worlds, observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-practice-dev-20260923.json'
SEED = 626101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 32
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WORKERS = 12
SEARCHED = ('unknown', 'pair', 'count', 'depth1', 'affinity', 'soft', 'pick', 'tilt')
SIGMA = {'unknown': .2, 'pair': .2, 'count': .25, 'depth1': 1., 'affinity': .25,
         'soft': .2, 'pick': .25, 'tilt': .2}
PAIRS = 8
GENERATIONS = 40
CHECKPOINTS = (10, 20, 40)
# Lifetimes per generation, by kind.
BOTH = {'supported': 4, 'family': 2, 'combination': 2}
FAMILY_ONLY = {'supported': 6, 'family': 2}
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
    training = draw_worlds(harness, train_triples, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    observed = observed_sets(harness, training, reserved, PRIOR_SOLVED, rng)
    priors = {'main': Prior(harness, observed)}
    practice_families = sorted({family for triple in train_triples for family in triple})
    for family in practice_families:
        kept = [sets for world, sets in zip(training, observed) if family not in world['triple']]
        priors[f'without:{family}'] = Prior(harness, kept)
    for triple in train_triples:
        kept = [sets for world, sets in zip(training, observed)
                if world['triple'] != tuple(sorted(triple))]
        priors[f'without:{"+".join(sorted(triple))}'] = Prior(harness, kept)
    views = {f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}

    def fresh_views(triple_pool, stream_rng):
        world, = draw_worlds(harness, triple_pool, 1, stream_rng, KEYS_PER_WORLD,
                             MINIMUM_MEMBERS, STREAM + 40)
        stream = [index for index in world['stream'] if index not in reserved][:STREAM]
        return simulator.views(stream, stream_rng)

    def lifetimes(stream_rng, mix):
        out = []
        for _ in range(mix['supported']):
            out.append((fresh_views(train_triples, stream_rng), 'main', 'supported'))
        for _ in range(mix.get('family', 0)):
            family = practice_families[stream_rng.randrange(len(practice_families))]
            out.append((fresh_views([t for t in train_triples if family in t], stream_rng),
                        f'without:{family}', 'family'))
        for _ in range(mix.get('combination', 0)):
            triple = train_triples[stream_rng.randrange(len(train_triples))]
            out.append((fresh_views([triple], stream_rng),
                        f'without:{"+".join(sorted(triple))}', 'combination'))
        return out

    pool = Pool(WORKERS, SEED + 77, priors, views, BUDGETS)
    print('setup', round(time.perf_counter() - wall), 's; triples: train',
          len(train_triples), 'new', len(new_triples), 'held', len(held_pool), flush=True)

    trainers = {'both': (Trainer([BUDGETS], SEARCHED, SIGMA, SEED + 21, pairs=PAIRS), BOTH,
                         random.Random(SEED + 31)),
                'family_only': (Trainer([BUDGETS], SEARCHED, SIGMA, SEED + 21, pairs=PAIRS),
                                FAMILY_ONLY, random.Random(SEED + 32))}
    checkpoints = {name: {} for name in trainers}
    for generation in range(1, GENERATIONS + 1):
        for name, (trainer, mix, stream_rng) in trainers.items():
            trainer.generation(pool, lifetimes(stream_rng, mix))
            if generation in CHECKPOINTS:
                checkpoints[name][generation] = trainer.coach(0)
        print('generation {:2d} ({:.0f}s): both {} | family only {}'.format(
            generation, time.perf_counter() - wall,
            {k: round(v, 2) for k, v in trainers['both'][0].coach(0).as_dict().items()
             if k in SEARCHED},
            {k: round(v, 2) for k, v in trainers['family_only'][0].coach(0).as_dict().items()
             if k in SEARCHED}), flush=True)

    arms = {'static': (BLIND, 'static'), 'blind': (BLIND, 'earned'),
            'warm': (UNHEDGED, 'earned'), 'champion': (CHAMPION, 'earned'),
            'revealed': (BLIND, 'revealed')}
    for name in trainers:
        arms.update({f'{name}@{g}': (coach, 'earned') for g, coach in checkpoints[name].items()})
    table = {}
    for group in groups:
        results = pool.map([(coach, world, arm, 'main')
                            for coach, arm in arms.values() for world in names[group]])
        table[group] = {}
        for number, name in enumerate(arms):
            chunk = results[number * len(names[group]):(number + 1) * len(names[group])]
            table[group][name] = np.array([[hits for hits in per_world] for per_world in chunk])
    pool.close()

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, EVAL_WORLDS, (BOOT, EVAL_WORLDS))
    final = GENERATIONS
    result = {'scope': 'practice at combination and family unfamiliarity, held-out worlds',
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'seed': SEED, 'budgets': list(BUDGETS), 'stream': STREAM,
              'searched': list(SEARCHED), 'generations': GENERATIONS,
              'mixes': {'both': BOTH, 'family_only': FAMILY_ONLY},
              'held_out_families': list(HELD_OUT_FAMILIES),
              'new_triples': [list(t) for t in new_triples],
              'checkpoints': {name: {str(g): c.as_dict() for g, c in points.items()}
                              for name, points in checkpoints.items()},
              'groups': {}}
    for group, arms_ in table.items():
        totals = {name: values.sum(axis=2) for name, values in arms_.items()}
        block = {'solved_mean_by_budget': {name: values.mean(axis=0).tolist()
                                           for name, values in totals.items()},
                 'per_world': {name: values.tolist() for name, values in totals.items()},
                 'contrasts': {}}
        pairs = [(f'{name}@{g}', 'champion') for name in trainers for g in CHECKPOINTS]
        pairs.append((f'both@{final}', f'family_only@{final}'))
        for left, right in pairs:
            difference = totals[left] - totals[right]
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
        print('arm'.ljust(18) + ''.join(str(b).rjust(8) for b in BUDGETS))
        for name, values in block['solved_mean_by_budget'].items():
            print(name.ljust(18) + ''.join('{:8.1f}'.format(v) for v in values))
        for name, entry in block['contrasts'].items():
            print('  {:30s}'.format(name) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(entry['sum'], entry['low'], entry['high'])))
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
