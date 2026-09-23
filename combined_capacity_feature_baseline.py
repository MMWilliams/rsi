"""Stage 1 completion: a pooled baseline that is capacity- AND feature-matched.

The capacity audit matched leaves (60) and the feature audit matched the
router's task statistics, separately. The third review asks for the combined
baseline. It reuses the stored per-bank curves for `built60_oof`, `pooled60`
and `pooled120` from `capacity_audit.json` and computes only the two new arms:

  pooled60_featured    60 leaves, rows augmented with the five task statistics
  pooled120_featured   120 leaves, same augmentation

Same strided windows as the frozen run, so per-bank pairing is exact.
"""
from __future__ import annotations

import json
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import write_json
from cross_family_meta_improver_transfer import interval
import construction_improver_confirmation as conf


SIZES = conf.SIZES
MAX_WINDOWS = conf.MAX_WINDOWS
BOOT = 20000
SEED = 924001


def model(leaves):
    return HistGradientBoostingClassifier(
        max_leaf_nodes=leaves, min_samples_leaf=80, learning_rate=.05,
        max_iter=100, l2_regularization=1., random_state=0)


def stat_vector(task):
    s = task['stats']
    return np.asarray([s['log_pool'], s['margin'], s['spread'], s['distinct'],
                       s['head'] / 100.], np.float32)


def augmented(task):
    return np.hstack([task['x'], np.tile(stat_vector(task), (len(task['x']), 1))])


def fit(history, leaves):
    xs = [augmented(t) for bank in history for t in bank]
    ys = [np.asarray(t['labels'], np.int8) for bank in history for t in bank]
    return model(leaves).fit(np.concatenate(xs), np.concatenate(ys))


def deploy(transfer, fitted):
    out = []
    for bank in transfer:
        total = 0
        for task in bank:
            p = fitted.predict_proba(augmented(task))[:, 1]
            total += task['labels'][max(range(len(p)), key=lambda i: (float(p[i]), -i))]
        out.append(total)
    return out


def paired(left, right, rng):
    v = np.asarray(left, float) - np.asarray(right, float)
    k = len(v)
    sums = np.array([v[rng.integers(0, k, k)].sum() for _ in range(BOOT)])
    return {'sum': float(v.sum()), 'positive_banks': int((v > 0).sum()),
            'losing_banks': int((v < 0).sum()),
            'bootstrap_interval': [float(np.percentile(sums, 2.5)),
                                   float(np.percentile(sums, 97.5))],
            'exact_interval_on_rounded': interval([int(round(x)) for x in v])}


def main():
    dest = conf.DEST
    out_path = dest / 'combined_baseline.json'
    if out_path.exists():
        raise RuntimeError('already run')
    stored = json.loads((dest / 'capacity_audit.json').read_text())['curve']
    rng = np.random.default_rng(SEED)
    history_pool = conf.load_banks('history_a') + conf.load_banks('history_b')
    transfer = conf.load_banks('transfer')
    curve = {}
    for size in SIZES:
        span = len(history_pool) - size + 1
        starts = list(range(0, span, max(1, span // MAX_WINDOWS)))[:MAX_WINDOWS]
        acc = {'pooled60_featured': np.zeros(len(transfer)),
               'pooled120_featured': np.zeros(len(transfer))}
        for start in starts:
            history = history_pool[start:start + size]
            acc['pooled60_featured'] += np.asarray(deploy(transfer, fit(history, 60)), float)
            acc['pooled120_featured'] += np.asarray(deploy(transfer, fit(history, 120)), float)
        curve[str(size)] = {k: {'total': float(v.sum() / len(starts)),
                                'per_bank': [float(x) for x in v / len(starts)]}
                            for k, v in acc.items()}
        curve[str(size)].update({k: stored[str(size)][k]
                                 for k in ('built60_oof', 'pooled60', 'pooled120')})
        row = curve[str(size)]
        print('history={:2d} built60={:6.1f} p60={:6.1f} p60+f={:6.1f} p120={:6.1f} p120+f={:6.1f}'.format(
            size, row['built60_oof']['total'], row['pooled60']['total'],
            row['pooled60_featured']['total'], row['pooled120']['total'],
            row['pooled120_featured']['total']), flush=True)
    big = curve[str(SIZES[-1])]
    comparisons = {
        'built60_minus_pooled60_featured': paired(big['built60_oof']['per_bank'], big['pooled60_featured']['per_bank'], rng),
        'built60_minus_pooled120_featured': paired(big['built60_oof']['per_bank'], big['pooled120_featured']['per_bank'], rng),
        'pooled60_featured_minus_pooled60': paired(big['pooled60_featured']['per_bank'], big['pooled60']['per_bank'], rng),
        'pooled120_featured_minus_pooled120': paired(big['pooled120_featured']['per_bank'], big['pooled120']['per_bank'], rng)}
    for k, v in comparisons.items():
        print('{:36s} {:+.1f} {}w/{}l {}'.format(k, v['sum'], v['positive_banks'], v['losing_banks'],
                                                 [round(x, 1) for x in v['bootstrap_interval']]), flush=True)
    write_json(out_path, {'scope': 'capacity- and feature-matched pooled baselines',
                          'run': dest.name, 'curve': curve, 'comparisons_at_24': comparisons})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rep2':
        import construction_confirmation_rep2 as rep2
        rep2.install()
    main()
