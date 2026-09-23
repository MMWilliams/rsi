"""Does verifier growth survive a whole-mechanism holdout?

Every transfer result in this programme used fresh seeds of the same
generators, which establishes instance-level transfer only. The third review
asks for the split that matters for a learning-ability claim: new mechanisms.

The only growth claim left standing is verifier growth, a larger pooled model
on more verified labels beating the frozen base evaluator E0. This tests it
under leave-one-family-out: for each of the six mechanism families, a 60-leaf
pooled model is trained on the other five families' source labels and scored
on the held-out family's target tasks, against E0 on those same tasks and
against a model trained on all six families (the in-distribution reference).

  held_out - E0        does the evaluator improvement reach a family it never saw
  in_dist - held_out   the transfer gap, what seeing the family is worth

Paired over 36 target banks per family (three opened panels, twelve banks
each, eight tasks of the family per bank). Development evidence on opened
cached panels; nothing frozen.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from region_specialist_repayment_development import SOURCE, TARGET, REGIONS, load_cache


OUT = ROOT / 'analysis/mechanism-holdout-verifier-20260921.json'
BOOT = 20000
SEED = 925001
LEAVES = 60


def model():
    return HistGradientBoostingClassifier(
        max_leaf_nodes=LEAVES, min_samples_leaf=80, learning_rate=.05,
        max_iter=100, l2_regularization=1., random_state=0)


def source_rows(exclude=None):
    xs, ys = [], []
    for name in SOURCE:
        x, meta = load_cache(name)
        for task in meta:
            if exclude and task['region'] == exclude:
                continue
            xs.append(x[task['start']:task['start'] + task['count']])
            ys.append(np.asarray(task['labels'], np.int8))
    return np.concatenate(xs), np.concatenate(ys)


def score_family(fitted, family):
    """Per-bank correct choices on the family's target tasks, with E0 alongside."""
    banks = defaultdict(lambda: [0, 0])
    for name in TARGET:
        x, meta = load_cache(name)
        for task in meta:
            if task['region'] != family:
                continue
            p = fitted.predict_proba(x[task['start']:task['start'] + task['count']])[:, 1]
            pick = task['labels'][max(range(task['count']), key=lambda i: (float(p[i]), -i))]
            key = (name, task['seed'])
            banks[key][0] += pick
            banks[key][1] += task['e0_label']
    keys = sorted(banks)
    return [banks[k][0] for k in keys], [banks[k][1] for k in keys]


def paired(left, right, rng):
    v = np.asarray(left, float) - np.asarray(right, float)
    k = len(v)
    sums = np.array([v[rng.integers(0, k, k)].sum() for _ in range(BOOT)])
    return {'sum': float(v.sum()), 'banks': k, 'positive_banks': int((v > 0).sum()),
            'losing_banks': int((v < 0).sum()),
            'bootstrap_interval': [float(np.percentile(sums, 2.5)),
                                   float(np.percentile(sums, 97.5))]}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    rng = np.random.default_rng(SEED)
    ax, ay = source_rows()
    in_dist = model().fit(ax, ay)
    result = {'scope': 'leave-one-family-out transfer of the pooled-60 evaluator',
              'leaves': LEAVES, 'families': {}}
    for family in REGIONS:
        hx, hy = source_rows(exclude=family)
        held = model().fit(hx, hy)
        held_scores, e0 = score_family(held, family)
        in_scores, _ = score_family(in_dist, family)
        row = {'tasks': 8 * len(e0), 'e0': sum(e0),
               'held_out': sum(held_scores), 'in_distribution': sum(in_scores),
               'held_out_minus_e0': paired(held_scores, e0, rng),
               'in_dist_minus_e0': paired(in_scores, e0, rng),
               'transfer_gap_in_dist_minus_held_out': paired(in_scores, held_scores, rng)}
        result['families'][family] = row
        h, i, g = row['held_out_minus_e0'], row['in_dist_minus_e0'], row['transfer_gap_in_dist_minus_held_out']
        print('{:26s} E0={:3d} held={:3d} in={:3d} | held-E0 {:+6.1f} {} | in-E0 {:+6.1f} | gap {:+6.1f} {}'.format(
            family, row['e0'], row['held_out'], row['in_distribution'],
            h['sum'], [round(x, 1) for x in h['bootstrap_interval']], i['sum'],
            g['sum'], [round(x, 1) for x in g['bootstrap_interval']]), flush=True)
    totals = {k: sum(v[k] for v in result['families'].values())
              for k in ('e0', 'held_out', 'in_distribution')}
    result['totals'] = totals
    result['limits'] = ['Opened cached panels; development evidence.',
                        'Held-out models see five of six families; the family mix of the '
                        'remaining source data is unchanged, so this is mechanism holdout, '
                        'not a change in the base ranker or candidate generator.',
                        'E0 itself was trained with all six families present.']
    write_json(OUT, result)
    print('totals:', totals)


if __name__ == '__main__':
    main()
