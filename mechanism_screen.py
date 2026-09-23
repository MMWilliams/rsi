"""P2 power screen for the drawn-mechanism environment.

Before an improver is built for an action space, the space has to have
headroom: a best available action worth enough more than the default to be
worth learning (`TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md`, P2). Here the
action is an ordering over the hypothesis catalog, the default is Occam
ordering (lowest complexity first), and the ceiling is the generator's own
weight function, which is exactly computable and known to no arm.

Reported per budget, over tasks whose mechanisms are drawn from the generator:

  occam        first consistent candidate in complexity order, scored on hidden
  density      first consistent candidate ordered by |density - 0.5|
  random       a fixed permutation, the no-information control
  prior        first consistent candidate in generator-weight order, the ceiling
  reachable    is the true mechanism inside the budget window at all

The screen answers two questions. Is the environment ambiguous, so that being
consistent with eight examples does not determine the answer? And is the gap
between Occam and the ceiling large enough that a learned prior has something
to earn? Development evidence; nothing is frozen here.

Superseded. This ran against an earlier build of the catalog (157,878 rows,
before every cross-family pair was enumerated and before worlds existed) and
does not import against the current `rsi/mechanism_space.py`. It is kept as
the record of what it measured; `mechanism_selection_recheck.py` re-asks the
same question on the catalog the confirmation used.
"""
from __future__ import annotations

import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import (build_catalog, catalog_digest, correct, drawable,
                                 make_task, pack, vector_test, weight_of)

OUT = ROOT / 'analysis/mechanism-screen-20260921.json'
TASKS = 600
SEED = 511777
BUDGETS = (16, 64, 256, 1024, 4096, 16384, 65536, None)


def orderings(catalog, seed):
    """Index permutations of the catalog, one per arm."""
    size = len(catalog)
    complexity = np.array([row['complexity'] for row in catalog])
    density = np.array([row['density'] for row in catalog])
    weight = np.array([weight_of(row) for row in catalog])
    rng = np.random.default_rng(seed)
    return {
        'occam': np.argsort(complexity, kind='stable'),
        'density': np.argsort(np.abs(density - .5), kind='stable'),
        'random': rng.permutation(size),
        'prior': np.argsort(-weight, kind='stable'),
    }


def first_consistent(order, consistent, budget):
    """Index of the arm's pick, or None if nothing in the window is consistent."""
    window = order if budget is None else order[:budget]
    hits = consistent[window]
    if not hits.any():
        return None
    return int(window[int(np.argmax(hits))])


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall = time.perf_counter()
    cpu = time.process_time()

    catalog = build_catalog()
    packed = pack(catalog)
    rows, weights = drawable(catalog)
    order = orderings(catalog, SEED)
    position = {name: np.empty(len(catalog), dtype=np.int64) for name in order}
    for name, perm in order.items():
        position[name][perm] = np.arange(len(catalog))

    rng = random.Random(SEED)
    drawn = rng.choices(range(len(rows)), weights=weights, k=TASKS)
    solved = {name: {budget: 0 for budget in BUDGETS} for name in order}
    reachable = {budget: 0 for budget in BUDGETS}
    consistent_counts, true_positions = [], {name: [] for name in order}
    failures = 0

    for pick in drawn:
        row = rows[pick]
        task = make_task(row, rng)
        consistent = vector_test(packed, task['visible_pos'], task['visible_neg'])
        if not consistent[row['index']]:
            failures += 1
            continue
        consistent_counts.append(int(consistent.sum()))
        for name in order:
            true_positions[name].append(int(position[name][row['index']]))
        good = vector_test(packed, task['hidden_pos'], task['hidden_neg'])
        for budget in BUDGETS:
            limit = len(catalog) if budget is None else budget
            reachable[budget] += int(position['prior'][row['index']] < limit)
            for name in order:
                chosen = first_consistent(order[name], consistent, budget)
                if chosen is not None and good[chosen]:
                    solved[name][budget] += 1

    tasks = len(consistent_counts)
    result = {
        'scope': 'P2 power screen on drawn mechanisms',
        'catalog': {'rows': len(catalog), 'digest': catalog_digest(catalog),
                    'drawable': len(rows)},
        'tasks': tasks, 'failures': failures, 'seed': SEED,
        'ambiguity': {'mean_consistent': float(np.mean(consistent_counts)),
                      'median_consistent': float(np.median(consistent_counts)),
                      'max_consistent': int(np.max(consistent_counts)),
                      'unique_answer_fraction': float(np.mean(np.array(consistent_counts) == 1))},
        'true_mechanism_rank': {name: {'median': float(np.median(values)),
                                       'mean': float(np.mean(values))}
                                for name, values in true_positions.items()},
        'solved': {name: {str(budget): solved[name][budget] for budget in BUDGETS}
                   for name in order},
        'rate': {name: {str(budget): solved[name][budget] / tasks for budget in BUDGETS}
                 for name in order},
        'prior_reachable': {str(budget): reachable[budget] / tasks for budget in BUDGETS},
        'headroom_prior_minus_occam': {
            str(budget): (solved['prior'][budget] - solved['occam'][budget]) / tasks
            for budget in BUDGETS},
        'cost': {'wall_seconds': time.perf_counter() - wall,
                 'cpu_seconds': time.process_time() - cpu,
                 'peak_rss_mb': process.memory_info().rss / 1e6,
                 'failed_draws': failures},
    }
    write_json(OUT, result)
    print('catalog {rows} rows, {drawable} drawable'.format(**result['catalog']))
    print('ambiguity: mean {mean_consistent:.1f} consistent, unique in {unique_answer_fraction:.3f}'
          .format(**result['ambiguity']))
    header = 'budget'.ljust(8) + ''.join(name.rjust(10) for name in order)
    print(header)
    for budget in BUDGETS:
        line = str(budget).ljust(8)
        for name in order:
            line += '{:10.3f}'.format(result['rate'][name][str(budget)])
        print(line)
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
