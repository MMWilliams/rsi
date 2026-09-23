"""Does experience of a world make its unfamiliar mechanisms solvable?

The power screen found the residual: at a fixed budget almost nothing is
solved, at unlimited budget a free rule solves seven tenths, so the binding
constraint is reaching a good hypothesis, not choosing among the ones already
in hand. This measures whether experience relieves that constraint.

A world admits about two hundred and fifty of the catalog's one hundred and
sixty-six thousand predicates, and never says which. An arm sees `n` solved
mechanisms of the world, all different from the ones it is tested on, and may
reorder the catalog however it likes. Every arm then scans the first `B`
entries of its own order, keeps the candidates consistent with the eight
visible examples, and picks among them by the same free rule, so ordering is
the only thing that differs.

  complexity   catalog order, the Occam default, and identical to experience 0
  density      density closest to one half, the best free order in the screen
  random       a fixed permutation, the no-information control
  experience   rows scored by how often their atoms appear in the solved set
  wrong world  the same rule fed another world's solved set, which is the
               control that separates acquiring this structure from having
               any structure at all

Reported per budget and per experience level, paired over tasks, with the
budget the free default needs to match experience at each level. Development
evidence on opened draws; nothing is frozen here.
"""
from __future__ import annotations

import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import (build_catalog, densities, make_task, make_worlds,
                                 pack, vector_test)

OUT = ROOT / 'analysis/mechanism-world-growth-20260921.json'
WORLDS = 12
KEYS_PER_WORLD = 14
TEST_MECHANISMS = 60
EXPERIENCE = (0, 1, 2, 4, 8, 16, 32, 64)
BUDGETS = (64, 256, 1024, 4096, 16384, 65536, None)
SEED = 601601
BOOT = 20000


def atom_columns(catalog):
    left = np.array([code[1] for code in catalog.codes], dtype=np.int32)
    right = np.array([code[2] if code[0] >= 0 else -1 for code in catalog.codes],
                     dtype=np.int32)
    return left, right


def ranks_of(order):
    position = np.empty(len(order), dtype=np.int32)
    position[order] = np.arange(len(order), dtype=np.int32)
    return position


def experience_order(catalog, left, right, base, mechanisms):
    """Score rows by how often their atoms appear in solved mechanisms.

    Counting is the whole rule: no model is fitted, so a gain here cannot be
    credited to capacity. Ties fall back to catalog order, which makes the
    zero-experience order identical to the Occam default by construction.
    """
    counts = np.zeros(len(catalog.atoms) + 1, dtype=np.float64)
    for index in mechanisms:
        code = catalog.codes[index]
        counts[code[1]] += 1
        if code[0] >= 0:
            counts[code[2]] += 1
    weight = np.log1p(counts)
    score = weight[left] + np.where(right >= 0, weight[right], 0.)
    return np.lexsort((base, -score))


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
    left, right = atom_columns(catalog)
    base = np.arange(catalog.size, dtype=np.int64)

    worlds = make_worlds(catalog, density, WORLDS, KEYS_PER_WORLD, SEED,
                         minimum=TEST_MECHANISMS + max(EXPERIENCE) + 40)
    free_ranks = {
        'complexity': ranks_of(base.copy()),
        'density': ranks_of(np.lexsort((base, np.abs(density - .5)))),
        'random': ranks_of(np.random.default_rng(SEED).permutation(catalog.size)),
    }

    rng = random.Random(SEED + 1)
    plan = []
    for world in worlds:
        members = list(world.members)
        random.Random(SEED + hash(world.name) % 1000).shuffle(members)
        plan.append({'world': world, 'test': members[:TEST_MECHANISMS],
                     'pool': members[TEST_MECHANISMS:]})

    experience_ranks, wrong_ranks = {}, {}
    for index, entry in enumerate(plan):
        other = plan[(index + 1) % len(plan)]['pool']
        for size in EXPERIENCE:
            experience_ranks[(index, size)] = ranks_of(
                experience_order(catalog, left, right, base, entry['pool'][:size]))
            wrong_ranks[(index, size)] = ranks_of(
                experience_order(catalog, left, right, base, other[:size]))

    arms = ['complexity', 'density', 'random'] + \
        [f'experience:{size}' for size in EXPERIENCE] + \
        [f'wrong_world:{size}' for size in EXPERIENCE]
    outcomes = {arm: {budget: [] for budget in BUDGETS} for arm in arms}
    unsolvable = 0

    for index, entry in enumerate(plan):
        for mechanism in entry['test']:
            task = make_task(catalog, mechanism, rng)
            consistent = np.flatnonzero(vector_test(packed, task['visible_pos'],
                                                    task['visible_neg']))
            if len(consistent) == 0:
                unsolvable += 1
                continue
            good = vector_test(packed, task['hidden_pos'], task['hidden_neg'])[consistent]
            order_key = np.lexsort((complexity[consistent], sizes[consistent]))

            def resolve(position):
                ranked = position[consistent]
                for budget in BUDGETS:
                    limit = catalog.size if budget is None else budget
                    hit = 0
                    for candidate in order_key:
                        if ranked[candidate] < limit:
                            hit = int(good[candidate])
                            break
                    yield budget, hit

            for name, position in free_ranks.items():
                for budget, hit in resolve(position):
                    outcomes[name][budget].append(hit)
            for size in EXPERIENCE:
                for budget, hit in resolve(experience_ranks[(index, size)]):
                    outcomes[f'experience:{size}'][budget].append(hit)
                for budget, hit in resolve(wrong_ranks[(index, size)]):
                    outcomes[f'wrong_world:{size}'][budget].append(hit)

    tasks = len(outcomes['complexity'][BUDGETS[0]])
    boot_rng = np.random.default_rng(SEED + 2)
    draws = boot_rng.integers(0, tasks, (BOOT, tasks))

    def paired(left_arm, right_arm, budget):
        difference = np.asarray(outcomes[left_arm][budget], float) - \
            np.asarray(outcomes[right_arm][budget], float)
        sums = difference[draws].sum(axis=1)
        return {'sum': float(difference.sum()),
                'interval': [float(np.percentile(sums, 2.5)),
                             float(np.percentile(sums, 97.5))]}

    rate = {arm: {str(budget): float(np.mean(outcomes[arm][budget])) for budget in BUDGETS}
            for arm in arms}
    best_free = {budget: max(('complexity', 'density', 'random'),
                             key=lambda name: rate[name][str(budget)]) for budget in BUDGETS}

    equivalence = {}
    for size in EXPERIENCE:
        row = {}
        for budget in BUDGETS:
            target = rate[f'experience:{size}'][str(budget)]
            matched = None
            for candidate in BUDGETS:
                limit = catalog.size if candidate is None else candidate
                reference = max(rate[name][str(candidate)]
                                for name in ('complexity', 'density', 'random'))
                if reference >= target:
                    matched = limit
                    break
            row[str(budget)] = matched
        equivalence[str(size)] = row

    result = {
        'scope': 'within-world mechanism holdout under a scan budget',
        'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
        'worlds': [{'name': entry['world'].name, 'members': len(entry['world']),
                    'keys': list(entry['world'].keys)} for entry in plan],
        'tasks': tasks, 'unsolvable': unsolvable, 'seed': SEED,
        'rate': rate,
        'best_free_order': {str(budget): best_free[budget] for budget in BUDGETS},
        'experience_minus_best_free': {
            str(size): {str(budget): paired(f'experience:{size}', best_free[budget], budget)
                        for budget in BUDGETS} for size in EXPERIENCE},
        'experience_minus_wrong_world': {
            str(size): {str(budget): paired(f'experience:{size}', f'wrong_world:{size}', budget)
                        for budget in BUDGETS} for size in EXPERIENCE},
        'budget_equivalence': equivalence,
        'cost': {'wall_seconds': time.perf_counter() - wall,
                 'cpu_seconds': time.process_time() - cpu,
                 'peak_rss_mb': process.memory_info().rss / 1e6,
                 'unsolvable_tasks': unsolvable},
    }
    write_json(OUT, result)

    print(f'{tasks} tasks over {len(plan)} worlds, catalog {catalog.size}')
    header = 'arm'.ljust(16) + ''.join(str(budget).rjust(9) for budget in BUDGETS)
    print(header)
    for arm in arms:
        print(arm.ljust(16) + ''.join('{:9.3f}'.format(rate[arm][str(budget)])
                                      for budget in BUDGETS))
    print('\nexperience minus best free order (tasks out of {}):'.format(tasks))
    for size in EXPERIENCE:
        row = result['experience_minus_best_free'][str(size)]
        print('n={:<4d}'.format(size) + ''.join('{:+9.0f}'.format(row[str(budget)]['sum'])
                                                for budget in BUDGETS))
    print('\nexperience minus wrong world:')
    for size in EXPERIENCE:
        row = result['experience_minus_wrong_world'][str(size)]
        print('n={:<4d}'.format(size) + ''.join('{:+9.0f}'.format(row[str(budget)]['sum'])
                                                for budget in BUDGETS))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
