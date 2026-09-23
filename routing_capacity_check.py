"""Is the routed four-specialist system the best use of its 24 history banks?

The routing confirmation established C1 and C2: a router fitted on 24 banks of
verified history beats the most-confident rule and beats a router fitted on two
banks. Those are claims about learning to route, and this check does not touch
them. It asks a different question the reviewers' residual-over-default framing
requires: does the routed system beat a single capacity-matched pooled model
that sees the same history?

Two pooled comparators, because the routed system's specialists were trained on
two separate opened source panels and only its router on the 24 history banks:

  pooled60_history   one 60-leaf model on the 24 history banks only
  pooled60_all       one 60-leaf model on the source panels plus the 24 banks

The first matches the router's data; the second matches the routed system's
total label exposure. Both are deployed on the untouched transfer panel. Also
reported: the frozen specialists' most-confident rule and the 24-bank router,
recomputed here from the caches so all arms share one code path.

Requires `routing_cache_build.py` to have run for the target replication.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from region_specialist_repayment_development import SOURCE, load_cache
import construction_improver_confirmation as conf
import complexity_improver_confirmation as routing
import complexity_partition_environment as env
import routing_cache_build as rcb


BOOT = 20000
SEED = 923001
NAMES = routing.NAMES
ACTIONS = routing.ACTIONS


def model(leaves):
    return HistGradientBoostingClassifier(
        max_leaf_nodes=leaves, min_samples_leaf=80, learning_rate=.05,
        max_iter=100, l2_regularization=1., random_state=0)


def views(banks, specialists):
    """Per-task label and confidence of every frozen specialist."""
    rows = []
    for bank in banks:
        for task in bank:
            labels = {'e0': task['e0_label']}
            confidence = {}
            for name, spec in specialists.items():
                p = spec.predict_proba(task['x'])[:, 1]
                pick = max(range(len(p)), key=lambda i: (float(p[i]), -i))
                labels[name] = task['labels'][pick]
                confidence[name] = float(p[pick])
            rows.append({'seed': task['seed'], 'stats': task['stats'],
                         'labels': labels, 'confidence': confidence})
    return rows


def per_bank(rows, picks):
    banks = defaultdict(int)
    for row, action in zip(rows, picks):
        banks[row['seed']] += row['labels'][action]
    return [banks[s] for s in sorted(banks)]


def source_rows():
    xs, ys = [], []
    for name in SOURCE:
        x, meta = load_cache(name)
        for task in meta:
            xs.append(x[task['start']:task['start'] + task['count']])
            ys.append(np.asarray(task['labels'], np.int8))
    return xs, ys


def pooled_arm(train_xs, train_ys, transfer, leaves):
    fitted = model(leaves).fit(np.concatenate(train_xs), np.concatenate(train_ys))
    out = []
    for bank in transfer:
        total = 0
        for task in bank:
            p = fitted.predict_proba(task['x'])[:, 1]
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


def main(which):
    rcb.install(which)
    dest = conf.DEST
    out_path = dest / 'capacity_check.json'
    if out_path.exists():
        raise RuntimeError('already run')
    rng = np.random.default_rng(SEED)
    history = conf.load_banks('history_a') + conf.load_banks('history_b')
    transfer = conf.load_banks('transfer')
    specialists = {n: joblib.load(routing.SPECIALISTS / f'{n}.joblib') for n in NAMES}
    scored = sorted(NAMES)

    hist_rows = views(history, specialists)
    tr_rows = views(transfer, specialists)
    router = routing.fit_router(hist_rows, scored)
    routed = per_bank(tr_rows, routing.deploy(router, tr_rows, scored))
    confident = per_bank(tr_rows, [max(NAMES, key=lambda a: (r['confidence'][a], a))
                                   for r in tr_rows])

    hx = [t['x'] for bank in history for t in bank]
    hy = [np.asarray(t['labels'], np.int8) for bank in history for t in bank]
    sx, sy = source_rows()
    arms = {'routed_24': routed, 'most_confident': confident,
            'pooled60_history': pooled_arm(hx, hy, transfer, 60),
            'pooled60_all': pooled_arm(sx + hx, sy + hy, transfer, 60),
            'pooled15_all': pooled_arm(sx + hx, sy + hy, transfer, 15)}
    for name, arm in arms.items():
        print('{:18s} {:6.1f}'.format(name, float(sum(arm))), flush=True)
    comparisons = {f'routed_minus_{k}': paired(routed, v, rng)
                   for k, v in arms.items() if k != 'routed_24'}
    for k, v in comparisons.items():
        print('{:32s} {:+.1f} {}w/{}l {}'.format(
            k, v['sum'], v['positive_banks'], v['losing_banks'],
            [round(x, 1) for x in v['bootstrap_interval']]), flush=True)
    write_json(out_path, {
        'scope': 'routing confirmation against capacity-matched pooled models',
        'run': dest.name, 'totals': {k: float(sum(v)) for k, v in arms.items()},
        'per_bank': arms, 'comparisons': comparisons,
        'limits': ['The routed system spends source-panel labels on specialists '
                   'and history labels on the router; pooled60_all matches total '
                   'label exposure, pooled60_history matches router data only.',
                   'Leaf count is one capacity axis.']})


if __name__ == '__main__':
    main(sys.argv[1])
