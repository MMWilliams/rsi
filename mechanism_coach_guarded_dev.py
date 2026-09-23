"""The RL-trained coach inside a safety contract.

`mechanism-coach-dev-20260923.json`: a coach trained by evolution strategies
on lifetimes lifts the earned loop on unfamiliar worlds at budgets of 1024 and
up (+311, +488, +323 of 3200 on untrained family combinations), and on worlds
containing an untrained family it loses at mid budgets (-66 at 256, -124 at
512). Its checkpoints are fragile there: generation 10 lost 748 at 4096
although its hedge share matched the champion's, because the coach also
rewrote the order its hedged half follows.

Here the coach may train every field except the safety contract, which is
fixed: half of every task's scans follow the rule the agent would use with no
prior and no coach (`arm='guarded'`). The coach can then only spend its own
half badly. Same training as before (continual ES from the champion, practice
at unfamiliarity on a quarter of lifetimes), on fresh seeds, with random
search at matched lifetimes and the same trained fields without the guard.

What a confirmable claim would need, read here as development: gains at every
budget where the loop receives evidence (the screens found room only from 1024
up) on untrained combinations, and no significant loss at any budget on any
split, including worlds with an untrained family. Development evidence.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Pool, Prior, Simulator, Trainer,
                              draw_worlds, observed_sets, shaped, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-guarded-dev-20260923.json'
SEED = 624101
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
SUPPORTED_PER_GENERATION = 6
PRACTICE_PER_GENERATION = 2
GENERATIONS = 40
CHECKPOINTS = (0, 10, 20, 40)
RANDOM_CANDIDATES = 160
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
    views = {f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}

    def fresh_views(triple_pool, count, stream_rng):
        out = []
        for world in draw_worlds(harness, triple_pool, count, stream_rng, KEYS_PER_WORLD,
                                 MINIMUM_MEMBERS, STREAM + 40):
            stream = [index for index in world['stream'] if index not in reserved][:STREAM]
            out.append(simulator.views(stream, stream_rng))
        return out

    def lifetimes(stream_rng):
        out = [(v, 'main', 'supported')
               for v in fresh_views(train_triples, SUPPORTED_PER_GENERATION, stream_rng)]
        for _ in range(PRACTICE_PER_GENERATION):
            family = practice_families[stream_rng.randrange(len(practice_families))]
            with_family = [t for t in train_triples if family in t]
            out.append((fresh_views(with_family, 1, stream_rng)[0], f'without:{family}',
                        'practice'))
        return out

    pool = Pool(WORKERS, SEED + 77, priors, views, BUDGETS)
    print('setup', round(time.perf_counter() - wall), 's; triples: train',
          len(train_triples), 'new', len(new_triples), 'held', len(held_pool), flush=True)

    trainer = Trainer([BUDGETS], SEARCHED, SIGMA, SEED + 21, pairs=PAIRS, arm='guarded')
    stream_rng = random.Random(SEED + 31)
    checkpoints = {0: CHAMPION}
    consumed = 0
    for generation in range(1, GENERATIONS + 1):
        batch = lifetimes(stream_rng)
        trainer.generation(pool, batch)
        consumed += 2 * PAIRS * len(batch) * len(BUDGETS)
        if generation in CHECKPOINTS:
            checkpoints[generation] = trainer.coach(0)
        print('generation {:2d} ({:.0f}s): {}'.format(
            generation, time.perf_counter() - wall,
            {k: round(v, 2) for k, v in trainer.coach(0).as_dict().items()}), flush=True)

    search_rng = random.Random(SEED + 41)
    per_candidate = consumed // (RANDOM_CANDIDATES * len(BUDGETS))
    batch = []
    while len(batch) < per_candidate:
        batch.extend(lifetimes(search_rng))
    batch = batch[:per_candidate]
    noise = np.random.default_rng(SEED + 42).standard_normal(
        (RANDOM_CANDIDATES - 1, len(SEARCHED)))
    base = Trainer([BUDGETS], SEARCHED, SIGMA, SEED + 43)
    candidates = [CHAMPION] + [base.coach(0, 2. * row) for row in noise]
    results = iter(pool.map([(coach, views_, 'guarded', prior)
                             for coach in candidates for views_, prior, _kind in batch]))
    kinds = sorted({kind for _v, _p, kind in batch})
    totals = {kind: np.zeros((len(candidates), len(BUDGETS))) for kind in kinds}
    for number in range(len(candidates)):
        for _views, _prior, kind in batch:
            totals[kind][number] += [hits.sum() for hits in next(results)]
    random_best = candidates[int(np.argmax(shaped(totals, kinds)))]
    print('random search:', per_candidate, 'lifetimes per candidate, chose',
          {k: round(v, 2) for k, v in random_best.as_dict().items()}, flush=True)

    final = f'coach@{GENERATIONS}'
    arms = {'static': (BLIND, 'static'), 'blind': (BLIND, 'earned'),
            'warm': (UNHEDGED, 'earned'), 'champion': (CHAMPION, 'earned'),
            'revealed': (BLIND, 'revealed'), 'random_search': (random_best, 'guarded'),
            'unguarded': (checkpoints[GENERATIONS], 'earned')}
    arms.update({f'coach@{g}': (coach, 'guarded') for g, coach in checkpoints.items() if g})
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
    result = {'scope': 'an RL-trained coach inside a fixed safety contract, held-out worlds',
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'seed': SEED, 'budgets': list(BUDGETS), 'stream': STREAM,
              'searched': list(SEARCHED), 'generations': GENERATIONS,
              'coach_training_lifetimes': consumed,
              'held_out_families': list(HELD_OUT_FAMILIES),
              'new_triples': [list(t) for t in new_triples],
              'checkpoints': {str(g): coach.as_dict() for g, coach in checkpoints.items()},
              'random_search': random_best.as_dict(), 'groups': {}}
    for group, arms_ in table.items():
        totals = {name: values.sum(axis=2) for name, values in arms_.items()}
        block = {'solved_mean_by_budget': {name: values.mean(axis=0).tolist()
                                           for name, values in totals.items()},
                 'per_world': {name: values.tolist() for name, values in totals.items()},
                 'first_vs_last_twenty': {name: [values[:, :, :20].mean(axis=(0, 2)).tolist(),
                                                 values[:, :, -20:].mean(axis=(0, 2)).tolist()]
                                          for name, values in arms_.items()},
                 'contrasts': {}}
        for left, right in ([(f'coach@{g}', 'champion') for g in CHECKPOINTS if g]
                            + [(final, 'random_search'), (final, 'unguarded'),
                               ('random_search', 'champion'), ('unguarded', 'champion')]):
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
