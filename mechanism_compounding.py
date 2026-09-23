"""Does the ability to acquire a world improve with the number of worlds seen?

G2 showed that experience of 400 worlds makes an unfamiliar world quicker to
learn. That is a level: a fixed amount of prior experience buying a fixed
advantage. Compounding is a different statement, about the derivative. If
seeing twice as many worlds keeps buying more, the quantity that improves is
the capacity to learn rather than any particular thing learned, which is what
the adopted definition asks for and what nothing in this repository has ever
measured.

The sweep fits the same estimator on the first 25, 50, 100, 200 and 400
training worlds and reads the G2 margin at each size, on worlds whose family
combination no training world used. Worlds drawn without family structure are
fitted at every size too: if the curve rises there as well, the sweep is
measuring the estimator warming up rather than structure accumulating.

Development evidence; nothing frozen.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test, world_members
from rsi.mechanism_worlds import Harness, affinity, ranks_of

OUT = ROOT / 'analysis/mechanism-compounding-20260921.json'
SEED = 607101
SIZES = (25, 50, 100, 200, 400)
PRIOR_SOLVED = 64
EVAL_WORLDS = 20
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
HELD_OUT_TRIPLES = 6
MINIMUM_MEMBERS = 120
ADAPT = (1, 2, 4)
BUDGETS = (1024, 4096)
FLOOR = 1e-4
BOOT = 20000


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
    held_triples = sorted(rng.sample(viable, HELD_OUT_TRIPLES))
    training_triples = [triple for triple in viable if triple not in held_triples]

    def draw(triples, count):
        out = []
        while len(out) < count:
            world = harness.sample_world(triples[rng.randrange(len(triples))], rng,
                                         KEYS_PER_WORLD, MINIMUM_MEMBERS)
            if world is not None:
                out.append(world)
        return out

    evaluation = draw(held_triples, EVAL_WORLDS)
    for world in evaluation:
        members = list(world['members'])
        rng.shuffle(members)
        world['test'] = members[:TEST_MECHANISMS]
        world['pool'] = members[TEST_MECHANISMS:]
    reserved = {index for world in evaluation for index in world['test']}

    training = draw(training_triples, max(SIZES))
    uniform = []
    while len(uniform) < max(SIZES):
        chosen = rng.sample(harness.key_names, KEYS_PER_WORLD)
        members = world_members(catalog, harness.by_key, chosen)
        if len(members) >= MINIMUM_MEMBERS:
            uniform.append({'members': members})

    def observe(worlds):
        out = []
        for world in worlds:
            allowed = [index for index in world['members'] if index not in reserved]
            solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
            out.append(sorted({harness.key_index[key]
                               for key in harness.observed_keys(solved)}))
        return out

    structured_sets = observe(training)
    uniform_sets = observe(uniform)
    priors = {}
    for size in SIZES:
        priors[('structured', size)] = affinity(structured_sets[:size], keys)
        priors[('uniform', size)] = affinity(uniform_sets[:size], keys)

    arms = ['free_set'] + [f'{kind}:{size}' for kind in ('structured', 'uniform')
                           for size in SIZES]
    outcomes = {k: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for k in ADAPT}

    for world in evaluation:
        ranks = {}
        for k in ADAPT:
            counts = harness.key_counts(world['pool'][:k])
            present = list(np.flatnonzero(counts))
            direct = (counts > 0).astype(float)
            ranks[('free_set', k)] = ranks_of(
                harness.order_from_key_scores(np.log(direct + FLOOR)))
            for (kind, size), matrix in priors.items():
                score = np.maximum(direct, matrix[present].max(axis=0)) if present else direct
                ranks[(f'{kind}:{size}', k)] = ranks_of(
                    harness.order_from_key_scores(np.log(score + FLOOR)))
        for mechanism in world['test']:
            task = make_task(catalog, mechanism, rng)
            consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                    task['visible_neg']))
            if len(consistent) == 0:
                continue
            good = vector_test(harness.packed, task['hidden_pos'],
                               task['hidden_neg'])[consistent]
            select = np.lexsort((harness.complexity[consistent], harness.sizes[consistent]))
            for k in ADAPT:
                for arm in arms:
                    ranked = ranks[(arm, k)][consistent]
                    for budget in BUDGETS:
                        hit = 0
                        for candidate in select:
                            if ranked[candidate] < budget:
                                hit = int(good[candidate])
                                break
                        outcomes[k][arm][budget].append(hit)

    tasks = len(outcomes[ADAPT[0]]['free_set'][BUDGETS[0]])
    boot = np.random.default_rng(SEED + 5)
    draws = boot.integers(0, tasks, (BOOT, tasks))

    def paired(k, arm, budget):
        difference = np.asarray(outcomes[k][arm][budget], float) - \
            np.asarray(outcomes[k]['free_set'][budget], float)
        sums = difference[draws].sum(axis=1)
        return {'sum': float(difference.sum()),
                'interval': [float(np.percentile(sums, 2.5)),
                             float(np.percentile(sums, 97.5))]}

    result = {'scope': 'margin over the free rule as a function of worlds seen',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'tasks': tasks, 'eval_worlds': EVAL_WORLDS, 'sizes': list(SIZES),
              'seed': SEED,
              'rate': {str(k): {arm: {str(budget): float(np.mean(outcomes[k][arm][budget]))
                                      for budget in BUDGETS} for arm in arms}
                       for k in ADAPT},
              'margin_over_free': {str(k): {arm: {str(budget): paired(k, arm, budget)
                                                  for budget in BUDGETS}
                                            for arm in arms if arm != 'free_set'}
                                   for k in ADAPT}}
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for budget in BUDGETS:
        print('\n== budget {} : {} tasks'.format(budget, tasks))
        print('k'.ljust(4) + ''.join('{:>12s}'.format(f'{kind[:4]}:{size}')
                                     for kind in ('structured', 'uniform')
                                     for size in SIZES))
        for k in ADAPT:
            row = ''.join('{:+12.0f}'.format(
                result['margin_over_free'][str(k)][f'{kind}:{size}'][str(budget)]['sum'])
                for kind in ('structured', 'uniform') for size in SIZES)
            print(str(k).ljust(4) + row)
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
