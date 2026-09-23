"""Where the earned loop stops being able to bootstrap.

`mechanism-lifelong-20260921.json` found that an agent which keeps the atoms of
whatever it submitted raises its own solve rate eightfold over 120 tasks at a
scan budget of 1024, and gets nowhere at 256: 3.5 tasks solved against 19.7.
Self-improvement there is a property of the rule and the budget together, so
the budget at which the loop starts to close is worth locating rather than
bracketing.

Six budgets, the same three arms, the same charged accounting: every atom the
agent knows came from a task it has already paid for. `revealed` is the
ceiling, told the true mechanism each time, and is not an arm anyone could
deploy.

The ordering is recomputed only when the *set* of known atoms changes, which it
stops doing once the agent has seen its world's atoms; the run is otherwise
identical to the one it extends. Development evidence; nothing frozen.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test
from rsi.mechanism_worlds import Harness, ranks_of

OUT = ROOT / 'analysis/mechanism-takeoff-20260921.json'
SEED = 609101
WORLDS = 16
STREAM = 100
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
MINIMUM_MEMBERS = 130
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
FLOOR = 1e-4
BOOT = 20000
ARMS = ('static', 'blind', 'revealed')
CHECKPOINTS = (20, 50, 100)


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    catalog = harness.catalog
    keys = len(harness.key_names)
    rng = random.Random(SEED)
    harness.set_tiebreak(SEED + 77)

    families = sorted(harness.by_family)
    viable = [triple for triple in itertools.combinations(families, FAMILIES_PER_WORLD)
              if harness.sample_world(triple, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)]
    evaluation = []
    while len(evaluation) < WORLDS:
        world = harness.sample_world(viable[rng.randrange(len(viable))], rng,
                                     KEYS_PER_WORLD, MINIMUM_MEMBERS)
        if world is not None:
            evaluation.append(world)

    static_order = ranks_of(harness.order_from_key_scores(np.zeros(keys)))
    curves = {budget: {arm: np.zeros((WORLDS, STREAM)) for arm in ARMS}
              for budget in BUDGETS}

    for world_number, world in enumerate(evaluation):
        stream = list(world['members'])
        rng.shuffle(stream)
        views = []
        for mechanism in stream[:STREAM]:
            task = make_task(catalog, mechanism, rng)
            consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                    task['visible_neg']))
            good = vector_test(harness.packed, task['hidden_pos'],
                               task['hidden_neg'])[consistent]
            views.append({'mechanism': mechanism, 'consistent': consistent, 'good': good,
                          'select': np.lexsort((harness.complexity[consistent],
                                                harness.sizes[consistent]))})
        for budget in BUDGETS:
            for arm in ARMS:
                known = set()
                position = static_order
                for step, view in enumerate(views):
                    ranked = position[view['consistent']]
                    pick = -1
                    for candidate in view['select']:
                        if ranked[candidate] < budget:
                            pick = candidate
                            break
                    hit = 0 if pick < 0 else int(view['good'][pick])
                    curves[budget][arm][world_number, step] = hit
                    learned = None
                    if arm == 'blind' and pick >= 0:
                        learned = int(view['consistent'][pick])
                    elif arm == 'revealed':
                        learned = view['mechanism']
                    if learned is None:
                        continue
                    fresh = {harness.key_index[key] for key in catalog.keys(learned)} - known
                    if not fresh:
                        continue
                    known |= fresh
                    score = np.zeros(keys)
                    score[sorted(known)] = 1.
                    position = ranks_of(
                        harness.order_from_key_scores(np.log(score + FLOOR)))

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, WORLDS, (BOOT, WORLDS))
    result = {'scope': 'the budget at which an earned loop starts to close',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'worlds': WORLDS, 'stream': STREAM, 'seed': SEED, 'budgets': {}}

    for budget in BUDGETS:
        totals = {arm: curves[budget][arm].sum(axis=1) for arm in ARMS}
        difference = totals['blind'] - totals['static']
        sums = difference[draws].sum(axis=1)
        result['budgets'][str(budget)] = {
            'solved': {arm: float(totals[arm].mean()) for arm in ARMS},
            'cumulative': {arm: {str(point): float(
                curves[budget][arm][:, :point].sum(axis=1).mean())
                for point in CHECKPOINTS} for arm in ARMS},
            'first_twenty_vs_last_twenty': {arm: [
                float(curves[budget][arm][:, :20].mean()),
                float(curves[budget][arm][:, -20:].mean())] for arm in ARMS},
            'blind_minus_static': {
                'sum': float(difference.sum()),
                'interval': [float(np.percentile(sums, 2.5)),
                             float(np.percentile(sums, 97.5))]}}

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    print('budget'.ljust(8) + 'static'.rjust(9) + 'blind'.rjust(9) + 'revealed'.rjust(10)
          + 'blind first20'.rjust(15) + 'last20'.rjust(9) + 'blind - static'.rjust(24))
    for budget in BUDGETS:
        block = result['budgets'][str(budget)]
        first, last = block['first_twenty_vs_last_twenty']['blind']
        entry = block['blind_minus_static']
        print(str(budget).ljust(8)
              + '{:9.1f}{:9.1f}{:10.1f}'.format(block['solved']['static'],
                                                block['solved']['blind'],
                                                block['solved']['revealed'])
              + '{:15.3f}{:9.3f}'.format(first, last)
              + '{:+9.0f} {}'.format(entry['sum'],
                                     [round(x) for x in entry['interval']]).rjust(24))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
