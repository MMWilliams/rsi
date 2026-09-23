"""Is the residual in selection, on the catalog the rest of the work uses?

`mechanism_screen.py` and `mechanism_selection_probe.py` were run on an earlier
build of the catalog, before every cross-family pair was enumerated and before
worlds existed, and they do not run against the current module. Their
conclusion is load-bearing for everything after it: eight examples leave a
handful of consistent hypotheses, a free rule picks among them about as well as
anything can, and the binding constraint is reaching a good hypothesis rather
than choosing among the ones in hand. It is worth re-establishing on the
catalog the confirmation actually used.

Free rules, applied to the whole consistent set at unlimited budget:

  occam      lowest complexity
  slack      smallest positive set, the most committal consistent hypothesis
  density    density closest to one half
  consensus  largest agreement with the other consistent candidates, a model
             average that needs no fitting
  random     the no-information control

against a gradient-boosted selector fitted on solved tasks, scored under a
mechanism holdout and under a family holdout. Development evidence.
"""
from __future__ import annotations

import random
import time

import numpy as np
import psutil
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from rsi.mechanism_space import ALPHABET_SIZE, DENSITY, make_task, vector_test
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-selection-recheck-20260921.json'
SEED = 612101
TASKS = 4000
LEAVES = 60
HOLDOUT_FAMILIES = ('popcount', 'xormod')
FREE = ('occam', 'slack', 'density', 'consensus', 'random')


def features(harness, task, where):
    """Per-candidate rows, all family-agnostic, so a model fitted with families
    withheld cannot recover them through the feature vector."""
    size = harness.sizes[where].astype(np.float64)
    complexity = harness.complexity[where].astype(np.float64)
    depth = np.array([harness.catalog.depth(int(index)) for index in where], float)
    required = bin(task['visible_pos']).count('1')
    forbidden = bin(task['visible_neg']).count('1')
    bits = np.unpackbits(harness.packed[where].view(np.uint8).reshape(len(where), -1),
                         axis=1)
    votes = bits.sum(axis=0) / len(where)
    agreement = (bits * votes).sum(axis=1) / np.maximum(size, 1)
    return np.column_stack([
        complexity, depth, size / ALPHABET_SIZE, (size - required) / ALPHABET_SIZE,
        np.full(len(where), required / ALPHABET_SIZE),
        np.full(len(where), forbidden / ALPHABET_SIZE),
        np.full(len(where), float(len(where))),
        np.log1p(np.full(len(where), float(len(where)))),
        agreement, np.abs(size / ALPHABET_SIZE - .5),
        complexity - complexity.min(), size - size.min()])


def free_picks(rows, rng):
    complexity, size, agreement = rows[:, 0], rows[:, 2], rows[:, 8]
    return {'occam': int(np.lexsort((size, complexity))[0]),
            'slack': int(np.lexsort((complexity, size))[0]),
            'density': int(np.argmin(np.abs(size - .5))),
            'consensus': int(np.argmax(agreement)),
            'random': rng.randrange(len(rows))}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    catalog = harness.catalog
    rng = random.Random(SEED)
    drawable = [index for index in range(catalog.size)
                if DENSITY[0] <= harness.density[index] <= DENSITY[1]]

    tasks = []
    for mechanism in rng.sample(drawable, TASKS):
        task = make_task(catalog, mechanism, rng)
        where = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                           task['visible_neg']))
        if len(where) == 0:
            continue
        good = vector_test(harness.packed, task['hidden_pos'], task['hidden_neg'])[where]
        tasks.append({'mechanism': mechanism, 'families': catalog.families(mechanism),
                      'good': good, 'x': features(harness, task, where),
                      'consistent': len(where)})

    total = len(tasks)
    order = list(range(total))
    random.Random(SEED + 1).shuffle(order)
    fit_ids = order[:total // 2]
    fit_mechanisms = {tasks[index]['mechanism'] for index in fit_ids}
    test_ids = [index for index in order[total // 2:]
                if tasks[index]['mechanism'] not in fit_mechanisms]
    family_fit = [index for index in range(total)
                  if not set(tasks[index]['families']) & set(HOLDOUT_FAMILIES)]
    family_test = [index for index in range(total)
                   if set(tasks[index]['families']) & set(HOLDOUT_FAMILIES)]

    def fit(indices):
        x = np.concatenate([tasks[index]['x'] for index in indices])
        y = np.concatenate([tasks[index]['good'] for index in indices]).astype(np.int8)
        return HistGradientBoostingClassifier(
            max_leaf_nodes=LEAVES, min_samples_leaf=40, learning_rate=.06,
            max_iter=180, l2_regularization=1., random_state=0).fit(x, y)

    def learned_rate(model, indices):
        hits = sum(int(tasks[index]['good'][int(np.argmax(
            model.predict_proba(tasks[index]['x'])[:, 1]))]) for index in indices)
        return hits / len(indices)

    def free_rates(indices):
        local = random.Random(SEED + 2)
        counts = {name: 0 for name in FREE}
        for index in indices:
            picks = free_picks(tasks[index]['x'], local)
            for name, pick in picks.items():
                counts[name] += int(tasks[index]['good'][pick])
        return {name: counts[name] / len(indices) for name in FREE}

    consistent = np.array([task['consistent'] for task in tasks])
    result = {
        'scope': 'selection headroom on the catalog used by the confirmation',
        'catalog': {'rows': catalog.size, 'digest': catalog.digest(),
                    'drawable': len(drawable)},
        'tasks': total, 'seed': SEED,
        'ambiguity': {'mean_consistent': float(consistent.mean()),
                      'median_consistent': float(np.median(consistent)),
                      'unique_answer_fraction': float((consistent == 1).mean()),
                      'some_candidate_correct': 1.0},
        'mechanism_holdout': {'test_tasks': len(test_ids),
                              'learned': learned_rate(fit(fit_ids), test_ids),
                              'free': free_rates(test_ids)},
        'family_holdout': {'withheld': list(HOLDOUT_FAMILIES),
                           'fit_tasks': len(family_fit), 'test_tasks': len(family_test),
                           'learned': learned_rate(fit(family_fit), family_test),
                           'free': free_rates(family_test)},
        'cost': {'wall_seconds': time.perf_counter() - wall,
                 'cpu_seconds': time.process_time() - cpu,
                 'peak_rss_mb': process.memory_info().rss / 1e6}}
    write_json(OUT, result)

    print('{} tasks, catalog {}'.format(total, catalog.size))
    print('ambiguity:', {k: round(v, 3) for k, v in result['ambiguity'].items()})
    for split in ('mechanism_holdout', 'family_holdout'):
        block = result[split]
        print('{}: {} tasks, learned {:.3f}, free {}'.format(
            split, block['test_tasks'], block['learned'],
            {k: round(v, 3) for k, v in block['free'].items()}))
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
