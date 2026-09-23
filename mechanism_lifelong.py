"""Growth when the experience is earned rather than handed over.

Every number in `MECHANISM-GROWTH-RESULTS-2026-09-21.md` gives an arm its
solved mechanisms for free. Solving them cost budget, and none of it was
charged, so those results measure the value of accumulated experience and not
improvement productivity. This charges it.

An agent meets a stream of 120 tasks from one world, each a mechanism it has
never seen, and spends the same scan budget on every one. It starts knowing
nothing about the world. Whatever it learns, it learns from tasks it has
already paid for, so the total resource is the number of tasks times the
budget and is identical for every arm. The question is whether the loop closes:
does solving a few tasks make the next ones cheap enough to solve, and does
that compound.

  static     never updates; the experience-free rule, and the floor
  blind      adds the atoms of whatever it submitted, right or wrong. Needs no
             feedback of any kind, so nothing outside the task is consulted
  feedback   adds those atoms only when told the answer was right: one bit per
             task, charged nothing
  revealed   is told the true mechanism after every task, right or wrong. Not
             an arm anyone could deploy; it is the ceiling for this loop
  meta       feedback, plus the cross-world prior of the confirmation run,
             which is where a prior should pay most: when the agent has almost
             no experience of its own

The task stream is shared by all arms, so every comparison is paired on the
same mechanisms in the same order. Development evidence; nothing frozen.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test
from rsi.mechanism_worlds import Harness, affinity, ranks_of

OUT = ROOT / 'analysis/mechanism-lifelong-20260921.json'
SEED = 606101
WORLDS = 24
STREAM = 120
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
MINIMUM_MEMBERS = 150
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
BUDGETS = (256, 1024)
FLOOR = 1e-4
BOOT = 20000
ARMS = ('static', 'blind', 'feedback', 'revealed', 'meta')
CHECKPOINTS = (10, 30, 60, 120)


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

    def draw(count):
        out = []
        while len(out) < count:
            world = harness.sample_world(viable[rng.randrange(len(viable))], rng,
                                         KEYS_PER_WORLD, MINIMUM_MEMBERS)
            if world is not None:
                out.append(world)
        return out

    evaluation = draw(WORLDS)
    reserved = {index for world in evaluation for index in world['members'][:STREAM]}
    training = draw(TRAINING_WORLDS)
    observed = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
        observed.append(sorted({harness.key_index[key]
                                for key in harness.observed_keys(solved)}))
    prior = affinity(observed, keys)

    static_order = ranks_of(harness.order_from_key_scores(np.zeros(keys)))
    curves = {budget: {arm: np.zeros((WORLDS, STREAM)) for arm in ARMS}
              for budget in BUDGETS}

    for world_number, world in enumerate(evaluation):
        stream = list(world['members'])
        rng.shuffle(stream)
        stream = stream[:STREAM]
        views = []
        for mechanism in stream:
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
                counts = np.zeros(keys)
                position = static_order
                stale = False
                for step, view in enumerate(views):
                    if stale:
                        direct = (counts > 0).astype(float)
                        present = list(np.flatnonzero(counts))
                        score = np.maximum(direct, prior[present].max(axis=0)) \
                            if arm == 'meta' and present else direct
                        position = ranks_of(
                            harness.order_from_key_scores(np.log(score + FLOOR)))
                        stale = False
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
                    elif arm == 'feedback' and hit:
                        learned = int(view['consistent'][pick])
                    elif arm == 'revealed':
                        learned = view['mechanism']
                    elif arm == 'meta' and hit:
                        learned = int(view['consistent'][pick])
                    if learned is not None:
                        for key in catalog.keys(learned):
                            counts[harness.key_index[key]] += 1
                        stale = True

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, WORLDS, (BOOT, WORLDS))
    result = {'scope': 'earned experience under a charged budget',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'worlds': WORLDS, 'stream': STREAM, 'training_worlds': TRAINING_WORLDS,
              'seed': SEED, 'budgets': {}}

    for budget in BUDGETS:
        totals = {arm: curves[budget][arm].sum(axis=1) for arm in ARMS}
        block = {'solved_per_world_mean': {arm: float(totals[arm].mean()) for arm in ARMS},
                 'cumulative': {arm: {str(point): float(
                     curves[budget][arm][:, :point].sum(axis=1).mean())
                     for point in CHECKPOINTS} for arm in ARMS},
                 'first_ten_vs_last_ten': {arm: [
                     float(curves[budget][arm][:, :10].mean()),
                     float(curves[budget][arm][:, -10:].mean())] for arm in ARMS}}
        for arm in ARMS:
            if arm == 'static':
                continue
            difference = totals[arm] - totals['static']
            sums = difference[draws].sum(axis=1)
            block.setdefault('minus_static', {})[arm] = {
                'sum': float(difference.sum()),
                'interval': [float(np.percentile(sums, 2.5)),
                             float(np.percentile(sums, 97.5))]}
        difference = totals['meta'] - totals['feedback']
        sums = difference[draws].sum(axis=1)
        block['meta_minus_feedback'] = {
            'sum': float(difference.sum()),
            'interval': [float(np.percentile(sums, 2.5)),
                         float(np.percentile(sums, 97.5))]}
        result['budgets'][str(budget)] = block

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for budget in BUDGETS:
        block = result['budgets'][str(budget)]
        print('\n== budget {} : {} worlds of {} tasks'.format(budget, WORLDS, STREAM))
        print('arm'.ljust(10) + ''.join('cum@{}'.format(point).rjust(10)
                                        for point in CHECKPOINTS)
              + 'first10'.rjust(10) + 'last10'.rjust(10) + 'minus static'.rjust(20))
        for arm in ARMS:
            row = ''.join('{:10.1f}'.format(block['cumulative'][arm][str(point)])
                          for point in CHECKPOINTS)
            first, last = block['first_ten_vs_last_ten'][arm]
            tail = ''
            if arm in block.get('minus_static', {}):
                entry = block['minus_static'][arm]
                tail = '{:+8.0f} {}'.format(entry['sum'],
                                            [round(x) for x in entry['interval']])
            print(arm.ljust(10) + row + '{:10.3f}{:10.3f}'.format(first, last) +
                  tail.rjust(20))
        entry = block['meta_minus_feedback']
        print('meta minus feedback: {:+.0f} {}'.format(
            entry['sum'], [round(x) for x in entry['interval']]))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
