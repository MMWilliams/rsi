"""Development probe: is the residual in mechanism selection learnable?

The power screen showed that at full budget the generator's own weight ordering
beats Occam ordering by 0.3 points, while some consistent candidate is correct
on every task. So the prior over *which mechanism was drawn* carries almost no
usable information, and the 35 points Occam leaves on the table are a question
about which consistent hypothesis generalizes, not about which is most likely.

This probe measures the free rules first, because an improver only earns its
name against the best rule that needs no experience:

  occam       lowest complexity among the consistent candidates
  density     density closest to one half
  slack       smallest positive set (the most committal consistent hypothesis)
  consensus   largest agreement with the other consistent candidates, a free
              model average that no fitting step is required to compute

and then asks whether a model fitted on solved tasks beats them on mechanisms
it has never seen, and on whole families it has never seen. Development
evidence on drawn tasks; nothing frozen.

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
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from rsi.mechanism_space import (ALPHABET_SIZE, build_catalog, catalog_digest,
                                 drawable, make_task, pack, vector_test)

OUT = ROOT / 'analysis/mechanism-selection-probe-20260921.json'
TASKS = 4000
SEED = 512101
LEAVES = 60
HOLDOUT_FAMILIES = ('mod', 'popcount')


def popcounts(packed):
    view = packed.view(np.uint8)
    table = np.unpackbits(view.reshape(-1, 1), axis=1).sum(axis=1)
    return table.reshape(packed.shape[0], -1).sum(axis=1).astype(np.int32)


def features(catalog, packed, sizes, task, where):
    """Per-candidate rows for one task's consistent set.

    Every feature is family-agnostic: nothing here names a mechanism family or
    a catalog index, so a model fitted with families withheld cannot recover
    them through the feature vector.
    """
    size = sizes[where].astype(np.float64)
    complexity = np.array([catalog[index]['complexity'] for index in where], float)
    depth = np.array([catalog[index]['depth'] for index in where], float)
    required = bin(task['visible_pos']).count('1')
    forbidden = bin(task['visible_neg']).count('1')
    slack = size - required
    # Agreement with the rest of the consistent set, the free model average.
    block = packed[where]
    bits = np.unpackbits(block.view(np.uint8).reshape(len(where), -1), axis=1)
    votes = bits.sum(axis=0)
    agreement = (bits * votes).sum(axis=1) / max(len(where), 1) / np.maximum(size, 1)
    consensus = (bits * (votes / max(len(where), 1))).sum(axis=1) - \
        ((1 - bits) * (votes / max(len(where), 1))).sum(axis=1)
    return np.column_stack([
        complexity, depth, size / ALPHABET_SIZE, slack / ALPHABET_SIZE,
        np.full(len(where), required / ALPHABET_SIZE),
        np.full(len(where), forbidden / ALPHABET_SIZE),
        np.full(len(where), float(len(where))),
        np.log1p(np.full(len(where), float(len(where)))),
        agreement, consensus / ALPHABET_SIZE,
        np.abs(size / ALPHABET_SIZE - .5),
        complexity - complexity.min(), size - size.min(),
    ])


FREE_RULES = ('occam', 'density', 'slack', 'consensus', 'random')


def free_choices(rows, rng):
    """Index into the consistent set chosen by each experience-free rule."""
    complexity, size, agreement = rows[:, 0], rows[:, 2], rows[:, 8]
    return {'occam': int(np.lexsort((size, complexity))[0]),
            'density': int(np.argmin(np.abs(size - .5))),
            'slack': int(np.lexsort((complexity, size))[0]),
            'consensus': int(np.argmax(agreement)),
            'random': rng.randrange(len(rows))}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    catalog = build_catalog()
    packed = pack(catalog)
    sizes = popcounts(packed)
    rows, weights = drawable(catalog)
    rng = random.Random(SEED)
    choice_rng = random.Random(SEED + 1)

    tasks = []
    drawn = rng.choices(range(len(rows)), weights=weights, k=TASKS)
    for pick in drawn:
        row = rows[pick]
        task = make_task(row, rng)
        consistent = vector_test(packed, task['visible_pos'], task['visible_neg'])
        where = np.flatnonzero(consistent)
        if len(where) == 0:
            continue
        good = vector_test(packed, task['hidden_pos'], task['hidden_neg'])[where]
        tasks.append({'mechanism': row['index'], 'families': row['families'],
                      'where': where, 'good': good,
                      'x': features(catalog, packed, sizes, task, where)})

    total = len(tasks)
    free = {name: 0 for name in FREE_RULES}
    for task in tasks:
        picks = free_choices(task['x'], choice_rng)
        for name, index in picks.items():
            free[name] += int(task['good'][index])

    # Mechanism holdout: fit on tasks whose mechanism differs from the target's.
    # Splitting by mechanism index is the instance/mechanism boundary; splitting
    # by family is the harder one that ended the verifier claim.
    order = list(range(total))
    random.Random(SEED + 2).shuffle(order)
    half = total // 2
    fit_ids = set(order[:half])
    test_ids = [index for index in order[half:]]
    fit_mechanisms = {tasks[index]['mechanism'] for index in fit_ids}
    test_ids = [index for index in test_ids
                if tasks[index]['mechanism'] not in fit_mechanisms]

    def fit(indices):
        x = np.concatenate([tasks[index]['x'] for index in indices])
        y = np.concatenate([tasks[index]['good'] for index in indices])
        model = HistGradientBoostingClassifier(
            max_leaf_nodes=LEAVES, min_samples_leaf=40, learning_rate=.06,
            max_iter=180, l2_regularization=1., random_state=0)
        return model.fit(x, y.astype(np.int8))

    def score(model, indices):
        hits = 0
        for index in indices:
            task = tasks[index]
            probability = model.predict_proba(task['x'])[:, 1]
            hits += int(task['good'][int(np.argmax(probability))])
        return hits

    learned = fit(sorted(fit_ids))
    mechanism_holdout = score(learned, test_ids)

    family_fit = [index for index in range(total)
                  if not set(tasks[index]['families']) & set(HOLDOUT_FAMILIES)]
    family_test = [index for index in range(total)
                   if set(tasks[index]['families']) & set(HOLDOUT_FAMILIES)]
    family_model = fit(family_fit) if family_fit else None
    family_holdout = score(family_model, family_test) if family_test else 0

    def rates(indices):
        out = {}
        for name in FREE_RULES:
            hits = 0
            local = random.Random(SEED + 3)
            for index in indices:
                picks = free_choices(tasks[index]['x'], local)
                hits += int(tasks[index]['good'][picks[name]])
            out[name] = hits / len(indices)
        return out

    result = {
        'scope': 'full-budget selection among consistent hypotheses',
        'catalog': {'rows': len(catalog), 'digest': catalog_digest(catalog)},
        'tasks': total, 'seed': SEED,
        'free_rules_all_tasks': {name: free[name] / total for name in FREE_RULES},
        'mechanism_holdout': {
            'test_tasks': len(test_ids),
            'learned': mechanism_holdout / len(test_ids),
            'free': rates(test_ids)},
        'family_holdout': {
            'withheld': list(HOLDOUT_FAMILIES),
            'fit_tasks': len(family_fit), 'test_tasks': len(family_test),
            'learned': family_holdout / max(len(family_test), 1),
            'free': rates(family_test) if family_test else {}},
        'cost': {'wall_seconds': time.perf_counter() - wall,
                 'cpu_seconds': time.process_time() - cpu,
                 'peak_rss_mb': process.memory_info().rss / 1e6},
    }
    write_json(OUT, result)
    print('tasks', total)
    print('free rules:', {k: round(v, 3) for k, v in result['free_rules_all_tasks'].items()})
    print('mechanism holdout: learned {:.3f} vs {}'.format(
        result['mechanism_holdout']['learned'],
        {k: round(v, 3) for k, v in result['mechanism_holdout']['free'].items()}))
    print('family holdout ({} tasks): learned {:.3f} vs {}'.format(
        result['family_holdout']['test_tasks'], result['family_holdout']['learned'],
        {k: round(v, 3) for k, v in result['family_holdout']['free'].items()}))
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
