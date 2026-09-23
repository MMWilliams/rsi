"""Second headroom screen: the levers the first one held fixed.

`mechanism-coach-screen-20260922.json` found no headroom worth training for in
the seven-lever class: the in-sample optimum's share of the gap from the
champion to the informed ceiling was 0.072, -0.001, 0.093, 0.175, 0.245 and
0.489 at budgets 128 to 4096, so any trained coach in that class could only
make a claim restricted to generous budgets.

Its fixed arms located the tight-budget lever it excluded. The hedge costs a
great deal at tight budgets where the prior is in support (the unhedged prior
solves 479 against the champion's 293 at budget 128) and buys nothing there
where it is not (61 against 38), while at generous budgets out of support it is
what keeps the prior from doing harm. One fixed share cannot be right at both
ends. The other lever no class has tried is when to spend: the earned loop is
limited by how early correct atoms arrive, so moving scans from late tasks to
early ones at a fixed total may start it sooner.

This screen adds three fields to the searched class: the hedge share, its
slope in log budget, and the allocation tilt. Because the hedge is now
searchable, the in-sample optimum is taken over worlds whose families training
held *and* worlds containing one it did not, with each group normalised by its
own gap to the ceiling, so a coach cannot buy in-support gains with
out-of-support losses unseen.

Same seed and worlds as the first screen; its champion totals are asserted.

Decision rule, fixed before this runs. Proceed to a trained coach only if the
in-sample optimum's normalised gain on the in-support worlds is at least 0.10
at four or more of the six budgets and positive at all six, and on the
out-of-support worlds is at least zero at all six. Development evidence.
"""
from __future__ import annotations

import json
import random
import sys
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Coach, Pool, Prior, Simulator,
                              draw_worlds, observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-screen2-20260923.json'
FIRST = ROOT / 'analysis/mechanism-coach-screen-20260922.json'
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
SEARCHED = ('unknown', 'pair', 'count', 'depth1', 'affinity', 'soft', 'pick', 'hedge',
            'hedge_slope', 'tilt')
SIGMA = {'unknown': .2, 'pair': .2, 'count': .25, 'depth1': 1., 'affinity': .25,
         'soft': .2, 'pick': .25, 'hedge': .2, 'hedge_slope': .1, 'tilt': .3}
POPULATION = 24
ELITE = 6
ITERATIONS = 10
LEVERS = {'tilt=+0.5': Coach(tilt=.5), 'tilt=-0.5': Coach(tilt=-.5),
          'hedge_slope=+0.15': Coach(hedge_slope=.15),
          'slope+tilt': Coach(hedge_slope=.15, tilt=.5)}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()
    first = json.loads(FIRST.read_text())

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
    every = [world for group in groups for world in names[group]]

    pool = Pool(WORKERS, SEED + 77, {'main': prior}, views, BUDGETS)

    def run(coaches, arm='earned'):
        """Per coach and group, per-world per-budget tasks solved."""
        results = pool.map([(coach, world, arm, 'main') for coach in coaches for world in every])
        out = []
        for number in range(len(coaches)):
            chunk = results[number * len(every):(number + 1) * len(every)]
            per_world = np.array([[int(hits.sum()) for hits in world] for world in chunk])
            out.append({group: per_world[[every.index(w) for w in names[group]]]
                        for group in groups})
        return out

    fixed = {'champion': (CHAMPION, 'earned'), 'warm': (UNHEDGED, 'earned'),
             'revealed': (BLIND, 'revealed')}
    fixed.update({name: (coach, 'earned') for name, coach in LEVERS.items()})
    table = {group: {} for group in groups}
    for name, (coach, arm) in fixed.items():
        for group, values in run([coach], arm)[0].items():
            table[group][name] = values
    for group in groups:
        for name in ('champion', 'warm', 'revealed'):
            assert table[group][name].sum(axis=0).tolist() == \
                first['groups'][group][name]['total_by_budget'], (group, name)
    print('fixed arms done, first screen reproduced', round(time.perf_counter() - wall), 's',
          flush=True)

    champion = {g: table[g]['champion'].sum(axis=0) for g in groups}
    gap = {g: np.maximum(table[g]['revealed'].sum(axis=0) - champion[g], 1) for g in groups}

    def gains(scored):
        return {g: (scored[g].sum(axis=0) - champion[g]) / gap[g] for g in groups}

    start = Coach(**{**first['in_sample_best'], 'hedge_slope': 0., 'tilt': 0.})
    mean = start.vector()
    index = [list(Coach.__dataclass_fields__).index(name) for name in SEARCHED]
    sigma = np.array([SIGMA[name] for name in SEARCHED])
    search = np.random.default_rng(SEED + 12)
    history, best = [], (-np.inf, start, None)
    for iteration in range(ITERATIONS):
        coaches = []
        for _ in range(POPULATION):
            vector = mean.copy()
            vector[index] = mean[index] + sigma * search.standard_normal(len(index))
            coaches.append(Coach.from_vector(vector).clipped())
        scored = []
        for coach, per_group in zip(coaches, run(coaches)):
            by_group = gains(per_group)
            scored.append((float(np.mean([by_group[g].mean() for g in groups])), coach,
                           per_group, by_group))
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
    pool.close()

    _fitness, best_coach, best_scores, best_gains = best
    for group in groups:
        table[group]['in_sample_best'] = best_scores[group]
    decision = bool((best_gains['seen'] >= .10).sum() >= 4 and (best_gains['seen'] > 0).all()
                    and (best_gains['new_family'] >= 0).all())
    result = {'scope': 'in-sample headroom with the hedge and allocation searchable',
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'seed': SEED, 'budgets': list(BUDGETS), 'stream': STREAM,
              'searched': list(SEARCHED), 'population': POPULATION, 'elite': ELITE,
              'iterations': ITERATIONS, 'start': start.as_dict(), 'history': history,
              'in_sample_best': best_coach.as_dict(),
              'in_sample_gain_by_budget': {g: v.tolist() for g, v in best_gains.items()},
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
        print('arm'.ljust(18) + ''.join(str(b).rjust(8) for b in BUDGETS))
        for name, values in arms.items():
            print(name.ljust(18) + ''.join('{:8d}'.format(int(v)) for v in values.sum(axis=0)))
        print('in-sample gain:', [round(x, 3) for x in best_gains[group]])
    print('best:', {k: round(v, 3) for k, v in best_coach.as_dict().items()})
    print('decision: proceed' if decision else 'decision: no headroom worth training for')
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
