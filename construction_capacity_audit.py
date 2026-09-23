"""Does partition structure add anything once capacity is matched?

`construction_oof_audit.py` showed that a single pooled model with 60 leaves
beats the 15-leaf built system by 50 and 36 at 24 banks. That withdraws the
construction claim as stated. It leaves one question open: the built system's
specialists had 15 leaves each, so the comparison was also mismatched in the
other direction. This gives the specialists and the pooled member 60 leaves,
fits the router out of fold, and compares against pooled models at 60 and 120
leaves on the same history.

If built-60 beats pooled-60 with a clean interval in both replications, partition
structure has value at matched capacity and needs its own frozen confirmation.
If it does not, partitioning adds nothing here beyond capacity. Either answer is
useful; neither un-withdraws the current claim. Runs on the frozen caches.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import write_json
from cross_family_meta_improver_transfer import interval
import construction_improver_development as dev
import construction_improver_confirmation as conf
import complexity_partition_environment as env


SIZES = conf.SIZES
MAX_WINDOWS = conf.MAX_WINDOWS
FOLDS = 3
BOOT = 20000
SEED = 922001


def model(leaves):
    return HistGradientBoostingClassifier(
        max_leaf_nodes=leaves, min_samples_leaf=80, learning_rate=.05,
        max_iter=100, l2_regularization=1., random_state=0)


def build(history, leaves):
    tasks = [t for bank in history for t in bank]
    groups = defaultdict(list)
    for task in tasks:
        groups[env.bin_of(task['labels'])].append(task)
    specialists = {}
    for name, group in groups.items():
        if name == 'unreachable' or len(group) < 8:
            continue
        x = np.concatenate([t['x'] for t in group])
        y = np.concatenate([np.asarray(t['labels'], np.int8) for t in group])
        if 0 < y.sum() < len(y):
            specialists[name] = model(leaves).fit(x, y)
    px = np.concatenate([t['x'] for t in tasks])
    py = np.concatenate([np.asarray(t['labels'], np.int8) for t in tasks])
    specialists['pooled'] = model(leaves).fit(px, py)
    return specialists


def oof_router(history, order, actions, leaves):
    folds = [history[i::FOLDS] for i in range(FOLDS)]
    rows = []
    targets = defaultdict(list)
    for index, fold in enumerate(folds):
        rest = [bank for j, f in enumerate(folds) if j != index for bank in f]
        fold_specialists = build(rest, leaves)
        for bank in fold:
            for task in bank:
                labels, confidence = dev.task_view(task, fold_specialists)
                for action in order:
                    if action not in confidence:
                        labels[action] = labels['pooled']
                        confidence[action] = confidence['pooled']
                rows.append(dev.features(task['stats'], confidence, order))
                for action in actions:
                    targets[action].append(labels[action])
    x = np.asarray(rows, np.float32)
    router = {}
    for action in actions:
        y = np.asarray(targets[action], np.int8)
        router[action] = (model(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return router


def deploy_pooled(transfer, fitted):
    out = []
    for bank in transfer:
        total = 0
        for task in bank:
            p = fitted.predict_proba(task['x'])[:, 1]
            total += task['labels'][max(range(len(p)), key=lambda i: (float(p[i]), -i))]
        out.append(total)
    return out


def fit_pooled(history, leaves):
    xs = [t['x'] for bank in history for t in bank]
    ys = [np.asarray(t['labels'], np.int8) for bank in history for t in bank]
    return model(leaves).fit(np.concatenate(xs), np.concatenate(ys))


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
    out_path = dest / 'capacity_audit.json'
    if out_path.exists():
        raise RuntimeError('already run')
    rng = np.random.default_rng(SEED)
    history_pool = conf.load_banks('history_a') + conf.load_banks('history_b')
    transfer = conf.load_banks('transfer')
    arms = ('built60_oof', 'pooled60', 'pooled120')
    curve = {}
    for size in SIZES:
        span = len(history_pool) - size + 1
        starts = list(range(0, span, max(1, span // MAX_WINDOWS)))[:MAX_WINDOWS]
        acc = {arm: np.zeros(len(transfer)) for arm in arms}
        for start in starts:
            history = history_pool[start:start + size]
            specialists = build(history, 60)
            order = sorted(specialists)
            actions = order + ['e0']
            router = oof_router(history, order, actions, 60)
            acc['built60_oof'] += np.asarray(
                dev.deploy(transfer, specialists, router, actions, order), float)
            acc['pooled60'] += np.asarray(
                deploy_pooled(transfer, fit_pooled(history, 60)), float)
            acc['pooled120'] += np.asarray(
                deploy_pooled(transfer, fit_pooled(history, 120)), float)
        curve[str(size)] = {arm: {'total': float(acc[arm].sum() / len(starts)),
                                  'per_bank': [float(v) for v in acc[arm] / len(starts)]}
                            for arm in arms}
        print('history={:2d} '.format(size) + ' '.join(
            '{}={:6.1f}'.format(arm, curve[str(size)][arm]['total']) for arm in arms),
            flush=True)
    big, small = curve[str(SIZES[-1])], curve[str(SIZES[0])]
    gates = {}
    for base in ('pooled60', 'pooled120'):
        e1 = paired(big['built60_oof']['per_bank'], big[base]['per_bank'], rng)
        gb = np.asarray(big[base]['per_bank']) - np.asarray(small[base]['per_bank'])
        e3v = (np.asarray(big['built60_oof']['per_bank'])
               - np.asarray(small['built60_oof']['per_bank'])) - gb
        e3 = {'sum': float(e3v.sum()), 'positive_banks': int((e3v > 0).sum()),
              'losing_banks': int((e3v < 0).sum()),
              'bootstrap_interval': paired(e3v, np.zeros_like(e3v), rng)['bootstrap_interval'],
              'baseline_growth': float(gb.sum())}
        gates[base] = {'E1_built60_vs_baseline': e1, 'E3_built60_growth_minus_baseline_growth': e3,
                       'E1_passed': bool(e1['sum'] > 0 and e1['bootstrap_interval'][0] > 0)}
        print('built60 vs {:9s} E1={:+.1f} {}  E3={:+.1f} {}'.format(
            base, e1['sum'], [round(x, 1) for x in e1['bootstrap_interval']],
            e3['sum'], [round(x, 1) for x in e3['bootstrap_interval']]), flush=True)
    write_json(out_path, {
        'scope': 'capacity-matched built (60-leaf specialists, OOF router) vs pooled 60 and 120',
        'run': dest.name, 'curve': curve, 'gates': gates,
        'limits': ['Leaf count is one capacity axis; iterations and learning rate are held fixed.',
                   'Same strided windows as the frozen run.']})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rep2':
        import construction_confirmation_rep2 as rep2
        rep2.install()
    main()
