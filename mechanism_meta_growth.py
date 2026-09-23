"""Does experience of many worlds make an unfamiliar world quicker to learn?

Within one world, counting the atoms of solved mechanisms is enough: experience
of sixty-four of a world's mechanisms takes the solve rate at a scan budget of
256 from 0.008 to 0.803, and the same rule fed another world's mechanisms gains
nothing (`mechanism-world-growth-20260921.json`). That is acquiring a structure,
and it is the floor, not the claim. The claim worth testing is the second half
of the adopted definition: not solving unfamiliar problems, but acquiring
unfamiliar skills faster because of what earlier skills taught.

Setting. Four hundred training worlds are observed through their solved
mechanisms, which is all an agent would ever see. A fresh world then gives `k`
solved mechanisms, and an arm must order the catalog for that world's other
mechanisms. The free adaptation rule is the within-world rule at small `k`:
credit the atoms you have seen. A meta arm may also use what the training
worlds say about which atoms travel together.

  free           atoms of the k solved mechanisms, the within-world rule
  meta           key affinity estimated from the training worlds' solved sets
  meta_uniform   the same estimator fitted on worlds drawn with no structure,
                 which is the control that says the gain came from structure
                 that exists rather than from having a second stage at all
  meta_scrambled the affinity matrix with its key labels permuted

Three evaluation splits separate three different claims, in the order that
ended the verifier claim when it was finally asked of it:

  seen_triple    the world's three atom families were combined in training
  new_triple     the families were each seen, never in this combination
  new_family     the world uses a family no training world contained

Development evidence on opened draws; nothing is frozen here.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import (build_catalog, densities, drawable_index, make_task,
                                 pack, vector_test, world_members)

OUT = ROOT / 'analysis/mechanism-meta-growth-20260921.json'
SEED = 602101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 12
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
ADAPT = (1, 2, 4, 8, 16)
BUDGETS = (256, 1024, 4096, 16384, 65536, None)
HELD_OUT_FAMILIES = ('popcount', 'xormod')
HELD_OUT_TRIPLES = 6
MINIMUM_MEMBERS = 120
ALPHA = 2.0
BOOT = 20000


def ranks_of(order):
    position = np.empty(len(order), dtype=np.int32)
    position[order] = np.arange(len(order), dtype=np.int32)
    return position


def sample_world(catalog, by_key, by_family, triple, rng, attempts=40):
    pool = [key for family in triple for key in by_family[family]]
    if len(pool) < KEYS_PER_WORLD:
        return None
    for _ in range(attempts):
        keys = rng.sample(pool, KEYS_PER_WORLD)
        if {key.split(':')[0] for key in keys} != set(triple):
            continue
        members = world_members(catalog, by_key, keys)
        if len(members) >= MINIMUM_MEMBERS:
            return {'keys': tuple(sorted(keys)), 'triple': tuple(sorted(triple)),
                    'members': members}
    return None


def affinity(observed_sets, key_index, alpha=ALPHA):
    """P(atom b is in a world | atom a is in it), estimated by counting worlds.

    Nothing here knows what a family is. If atoms of the same family travel
    together, the counts say so; if worlds have no structure, they say that
    instead, and the arm that reads them inherits whichever is true.
    """
    size = len(key_index)
    appear = np.zeros(size)
    cooccur = np.zeros((size, size))
    for keys in observed_sets:
        indices = [key_index[key] for key in keys if key in key_index]
        appear[indices] += 1
        block = np.zeros(size)
        block[indices] = 1.
        cooccur[np.ix_(indices, range(size))] += block
    base = appear / max(len(observed_sets), 1)
    return (cooccur + alpha * base[None, :]) / (appear[:, None] + alpha)


def key_columns(catalog, key_index):
    left = np.empty(catalog.size, dtype=np.int32)
    right = np.empty(catalog.size, dtype=np.int32)
    for index in range(catalog.size):
        keys = catalog.keys(index)
        left[index] = key_index[keys[0]]
        right[index] = key_index[keys[1]] if len(keys) > 1 else -1
    return left, right


def order_from_scores(key_score, left, right, base):
    score = key_score[left] + np.where(right >= 0, key_score[right], 0.)
    return np.lexsort((base, -score))


def observed_keys(catalog, mechanisms):
    keys = []
    for index in mechanisms:
        keys.extend(catalog.keys(index))
    return keys


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    catalog = build_catalog()
    packed = pack(catalog)
    density = densities(packed)
    sizes = (density * 256).astype(np.int32)
    complexity = np.array([catalog.complexity(index) for index in range(catalog.size)],
                          dtype=np.int32)
    base = np.arange(catalog.size, dtype=np.int64)
    by_key = drawable_index(catalog, density)
    by_family = {}
    for key in sorted(by_key):
        by_family.setdefault(key.split(':')[0], []).append(key)
    key_names = sorted(by_key)
    key_index = {key: index for index, key in enumerate(key_names)}
    left, right = key_columns(catalog, key_index)

    rng = random.Random(SEED)
    seen_families = [family for family in sorted(by_family)
                     if family not in HELD_OUT_FAMILIES]
    viable = []
    for triple in itertools.combinations(seen_families, FAMILIES_PER_WORLD):
        if sample_world(catalog, by_key, by_family, triple, rng) is not None:
            viable.append(triple)
    held_triples = set(rng.sample(viable, HELD_OUT_TRIPLES))
    training_triples = [triple for triple in viable if triple not in held_triples]

    training = []
    while len(training) < TRAINING_WORLDS:
        triple = training_triples[rng.randrange(len(training_triples))]
        world = sample_world(catalog, by_key, by_family, triple, rng)
        if world is not None:
            training.append(world)

    uniform_training = []
    while len(uniform_training) < TRAINING_WORLDS:
        keys = rng.sample(key_names, KEYS_PER_WORLD)
        members = world_members(catalog, by_key, keys)
        if len(members) >= MINIMUM_MEMBERS:
            uniform_training.append({'keys': tuple(sorted(keys)), 'triple': None,
                                     'members': members})

    def observed(worlds):
        out = []
        for world in worlds:
            solved = rng.sample(world['members'], min(PRIOR_SOLVED, len(world['members'])))
            out.append(sorted(set(observed_keys(catalog, solved))))
        return out

    structured_sets = observed(training)
    uniform_sets = observed(uniform_training)
    affinities = {'meta': affinity(structured_sets, key_index),
                  'meta_uniform': affinity(uniform_sets, key_index)}
    permutation = np.random.default_rng(SEED + 5).permutation(len(key_names))
    affinities['meta_scrambled'] = affinities['meta'][np.ix_(permutation, permutation)]

    evaluation = {'seen_triple': [], 'new_triple': [], 'new_family': []}
    held_family_triples = [triple for triple in
                           itertools.combinations(sorted(by_family), FAMILIES_PER_WORLD)
                           if set(triple) & set(HELD_OUT_FAMILIES)]
    while len(evaluation['seen_triple']) < EVAL_WORLDS:
        world = sample_world(catalog, by_key, by_family,
                             training_triples[rng.randrange(len(training_triples))], rng)
        if world is not None:
            evaluation['seen_triple'].append(world)
    while len(evaluation['new_triple']) < EVAL_WORLDS:
        world = sample_world(catalog, by_key, by_family,
                             sorted(held_triples)[rng.randrange(len(held_triples))], rng)
        if world is not None:
            evaluation['new_triple'].append(world)
    while len(evaluation['new_family']) < EVAL_WORLDS:
        world = sample_world(catalog, by_key, by_family,
                             held_family_triples[rng.randrange(len(held_family_triples))], rng)
        if world is not None:
            evaluation['new_family'].append(world)

    free_orders = {
        'complexity': ranks_of(base.copy()),
        'density': ranks_of(np.lexsort((base, np.abs(density - .5)))),
    }
    arms = ['complexity', 'density'] + \
        [f'{name}:{k}' for k in ADAPT
         for name in ('free', 'meta', 'meta_uniform', 'meta_scrambled')]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}
    world_sizes = {split: [] for split in evaluation}

    for split, worlds in evaluation.items():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            test = members[:TEST_MECHANISMS]
            pool = members[TEST_MECHANISMS:]
            world_sizes[split].append(len(members))
            ranks = dict(free_orders)
            for k in ADAPT:
                keys = observed_keys(catalog, pool[:k])
                indices = [key_index[key] for key in keys]
                counts = np.zeros(len(key_names))
                for index in indices:
                    counts[index] += 1
                ranks[f'free:{k}'] = ranks_of(
                    order_from_scores(np.log1p(counts), left, right, base))
                for name, matrix in affinities.items():
                    posterior = matrix[indices].mean(axis=0) if indices else \
                        np.zeros(len(key_names))
                    ranks[f'{name}:{k}'] = ranks_of(
                        order_from_scores(np.log(posterior + 1e-9), left, right, base))
            for mechanism in test:
                task = make_task(catalog, mechanism, rng)
                consistent = np.flatnonzero(vector_test(packed, task['visible_pos'],
                                                        task['visible_neg']))
                if len(consistent) == 0:
                    continue
                good = vector_test(packed, task['hidden_pos'],
                                   task['hidden_neg'])[consistent]
                order_key = np.lexsort((complexity[consistent], sizes[consistent]))
                for arm in arms:
                    ranked = ranks[arm][consistent]
                    for budget in BUDGETS:
                        limit = catalog.size if budget is None else budget
                        hit = 0
                        for candidate in order_key:
                            if ranked[candidate] < limit:
                                hit = int(good[candidate])
                                break
                        outcomes[split][arm][budget].append(hit)

    boot = np.random.default_rng(SEED + 7)
    result = {'scope': 'adaptation to an unfamiliar world after experience of many',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'held_out_families': list(HELD_OUT_FAMILIES),
              'held_out_triples': [list(triple) for triple in sorted(held_triples)],
              'prior_solved_per_world': PRIOR_SOLVED, 'seed': SEED, 'splits': {}}

    for split in evaluation:
        tasks = len(outcomes[split]['complexity'][BUDGETS[0]])
        draws = boot.integers(0, tasks, (BOOT, tasks))

        def paired(a, b, budget):
            difference = np.asarray(outcomes[split][a][budget], float) - \
                np.asarray(outcomes[split][b][budget], float)
            sums = difference[draws].sum(axis=1)
            return {'sum': float(difference.sum()),
                    'interval': [float(np.percentile(sums, 2.5)),
                                 float(np.percentile(sums, 97.5))]}

        rate = {arm: {str(budget): float(np.mean(outcomes[split][arm][budget]))
                      for budget in BUDGETS} for arm in arms}
        result['splits'][split] = {
            'tasks': tasks, 'worlds': len(evaluation[split]),
            'world_members_mean': float(np.mean(world_sizes[split])),
            'rate': rate,
            'meta_minus_free': {str(k): {str(budget): paired(f'meta:{k}', f'free:{k}', budget)
                                         for budget in BUDGETS} for k in ADAPT},
            'meta_minus_uniform': {
                str(k): {str(budget): paired(f'meta:{k}', f'meta_uniform:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT},
            'meta_minus_scrambled': {
                str(k): {str(budget): paired(f'meta:{k}', f'meta_scrambled:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT},
        }

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for split in ('seen_triple', 'new_triple', 'new_family'):
        block = result['splits'][split]
        print('\n== {} : {} tasks, {} worlds, {:.0f} members each'.format(
            split, block['tasks'], block['worlds'], block['world_members_mean']))
        print('arm'.ljust(18) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(18) + ''.join('{:9.3f}'.format(block['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        print('meta minus free (tasks out of {}):'.format(block['tasks']))
        for k in ADAPT:
            row = block['meta_minus_free'][str(k)]
            print('k={:<3d}'.format(k) + ''.join('{:+9.0f}'.format(row[str(b)]['sum'])
                                                 for b in BUDGETS))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
