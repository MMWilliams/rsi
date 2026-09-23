"""Is there anything for a trained coach to find? Screen before building one.

The proposal is an external component, trained by reinforcement learning on
whole lifetimes, that sets the free choices of the earned loop
(`rsi/growth_coach.py`). The first rule of this programme is to screen an
action space before an improver is built for it. The screen here is the
in-sample optimum: the best coach in the class found by policy search on the
very worlds it is scored on. That is an upper bound on what any training could
deliver on these worlds, so if it is not clearly above the champion, nothing
trained on other worlds will be.

Champion: the cold-start pair prior with half the budget hedged, the best
procedure in `mechanism-hedged-start-20260921.json` that is safe outside its
support. The hedge is held at one half for every searched coach: that contract
is not up for tuning, because every acquired prior here has failed outside its
support and the hedge is what bounds it.

Decision rule, fixed before this runs. Normalised gain at a budget is
(in-sample best minus champion) / (revealed ceiling minus champion), tasks
summed over the 32 screen worlds. Proceed to a trained coach only if the gain
is at least 0.10 at four or more of the six budgets and positive at all six.
Otherwise the class has no headroom worth training for.

Single-lever variants are reported beside it so that any headroom can be
attributed. Worlds whose families include one no training world held are
scored for every fixed arm and for the in-sample best, as a warning about what
the search is buying, not as part of the decision. Development evidence.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Coach, Pool, Prior, Simulator,
                              draw_worlds, observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-screen-20260922.json'
SEED = 620101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
SCREEN_WORLDS = 32
NEW_FAMILY_WORLDS = 16
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WORKERS = 12
SEARCHED = ('unknown', 'pair', 'count', 'depth1', 'affinity', 'soft', 'pick')
SIGMA = {'unknown': .4, 'pair': .4, 'count': .5, 'depth1': 2., 'affinity': .5,
         'soft': .4, 'pick': .5}
POPULATION = 24
ELITE = 6
ITERATIONS = 10
LEVERS = {'unknown=0.5': Coach(unknown=.5), 'unknown=2': Coach(unknown=2.),
          'pair=0.5': Coach(pair=.5), 'pair=2': Coach(pair=2.),
          'count=0.5': Coach(count=.5), 'count=2': Coach(count=2.),
          'depth1=-3': Coach(depth1=-3.), 'depth1=+3': Coach(depth1=3.),
          'affinity=0.5': Coach(affinity=.5), 'affinity=1': Coach(affinity=1.),
          'soft=0.5': Coach(soft=.5), 'soft=1': Coach(soft=1.),
          'pick=0.5': Coach(pick=.5),
          'hedge=0.25': Coach(hedge=.25), 'hedge=0.75': Coach(hedge=.75)}


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
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {'seen': draw_worlds(harness, seen_pool, SCREEN_WORLDS, rng, KEYS_PER_WORLD,
                                  MINIMUM_MEMBERS, STREAM),
              'new_family': draw_worlds(harness, held_pool, NEW_FAMILY_WORLDS, rng,
                                        KEYS_PER_WORLD, MINIMUM_MEMBERS, STREAM)}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, seen_pool, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, PRIOR_SOLVED, rng))
    views = {f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}

    pool = Pool(WORKERS, SEED + 77, {'main': prior}, views, BUDGETS)

    def totals(coach, group, arm='earned'):
        """Per-world, per-budget tasks solved, shape (worlds, budgets)."""
        results = pool.map([(coach, world, arm, 'main') for world in names[group]])
        return np.array([[int(hits.sum()) for hits in per_world] for per_world in results])

    fixed = {'static': (BLIND, 'static'), 'blind': (BLIND, 'earned'),
             'warm': (UNHEDGED, 'earned'), 'champion': (CHAMPION, 'earned'),
             'revealed': (BLIND, 'revealed')}
    fixed.update({name: (coach, 'earned') for name, coach in LEVERS.items()})
    table = {group: {name: totals(coach, group, arm) for name, (coach, arm) in fixed.items()}
             for group in groups}
    print('fixed arms done', round(time.perf_counter() - wall), 's', flush=True)

    champion = table['seen']['champion'].sum(axis=0)
    ceiling = table['seen']['revealed'].sum(axis=0)
    gap = np.maximum(ceiling - champion, 1)

    def gain(per_world):
        return (per_world.sum(axis=0) - champion) / gap

    mean = CHAMPION.vector()
    index = [list(Coach.__dataclass_fields__).index(name) for name in SEARCHED]
    sigma = np.array([SIGMA[name] for name in SEARCHED])
    search = np.random.default_rng(SEED + 11)
    history, best = [], (-np.inf, CHAMPION, None)
    for iteration in range(ITERATIONS):
        coaches = []
        for _ in range(POPULATION):
            vector = mean.copy()
            vector[index] = mean[index] + sigma * search.standard_normal(len(index))
            coaches.append(Coach.from_vector(vector).clipped())
        results = pool.map([(coach, world, 'earned', 'main')
                            for coach in coaches for world in names['seen']])
        scored = []
        for number, coach in enumerate(coaches):
            per_world = np.array([[int(hits.sum()) for hits in results[number * len(names['seen'])
                                                                      + w]]
                                  for w in range(len(names['seen']))])
            per_budget = gain(per_world)
            scored.append((float(per_budget.mean()), coach, per_world))
        scored.sort(key=lambda item: -item[0])
        if scored[0][0] > best[0]:
            best = scored[0]
        elite = np.array([item[1].vector() for item in scored[:ELITE]])
        mean = elite.mean(axis=0)
        sigma = .5 * sigma + .5 * np.maximum(elite[:, index].std(axis=0), .05 * sigma)
        history.append({'iteration': iteration, 'best_fitness': scored[0][0],
                        'median_fitness': float(np.median([item[0] for item in scored])),
                        'mean': Coach.from_vector(mean).as_dict()})
        print('iteration {} best {:+.3f} median {:+.3f} ever {:+.3f} | {}'.format(
            iteration, scored[0][0], history[-1]['median_fitness'], best[0],
            {k: round(v, 2) for k, v in scored[0][1].as_dict().items()}), flush=True)

    best_coach = best[1]
    table['seen']['in_sample_best'] = best[2]
    table['new_family']['in_sample_best'] = totals(best_coach, 'new_family')
    pool.close()

    in_sample_gain = gain(best[2])
    decision = bool((in_sample_gain >= .10).sum() >= 4 and (in_sample_gain > 0).all())
    result = {'scope': 'in-sample headroom of a trained coach over the hedged champion',
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'seed': SEED, 'budgets': list(BUDGETS), 'stream': STREAM,
              'training_worlds': TRAINING_WORLDS, 'held_out_families': list(HELD_OUT_FAMILIES),
              'searched': list(SEARCHED), 'population': POPULATION, 'elite': ELITE,
              'iterations': ITERATIONS, 'history': history,
              'in_sample_best': best_coach.as_dict(),
              'in_sample_gain_by_budget': in_sample_gain.tolist(),
              'decision_proceed': decision,
              'groups': {group: {name: {'total_by_budget': values.sum(axis=0).tolist(),
                                        'per_world': values.tolist()}
                                 for name, values in arms.items()}
                         for group, arms in table.items()}}
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for group, arms in table.items():
        print(f'\n== {group}: tasks solved, summed over worlds, by budget')
        print('arm'.ljust(16) + ''.join(str(b).rjust(8) for b in BUDGETS))
        for name, values in arms.items():
            print(name.ljust(16) + ''.join('{:8d}'.format(int(v)) for v in values.sum(axis=0)))
    print('\nin-sample gain over champion, share of the gap to the ceiling:',
          [round(x, 3) for x in in_sample_gain])
    print('decision: proceed' if decision else 'decision: no headroom worth training for')
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
