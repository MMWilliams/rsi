"""Information-flow audit of the construction improver: out-of-fold routing and
two stronger pooled baselines, on the frozen confirmation caches.

Two review findings motivate this. First, `fit_router` in the frozen runs fitted
the router on specialist predictions made on the specialists' own training
rows, so those predictions were more confident and more often correct than they
will be at deployment. Both the runner and the independent auditor follow that
specification, so the audit could not catch it. Second, the pooled baseline has
less capacity than the built system and no access to the task-level statistics
the router sees, so an E1 gain could be capacity or features rather than
partition structure.

Arms per history window, all deployed on the untouched transfer panel:

  built_insample    the frozen procedure, reproduced as an anchor
  built_oof         same final specialists; router fitted on out-of-fold
                    specialist views from three bank folds of the history
  pooled            the frozen baseline, one model on the same history
  pooled_capacity   one model with four times the leaves of one specialist,
                    roughly matching the built system's total capacity
  pooled_featured   one model whose candidate rows are augmented with the same
                    five task-level public statistics the router sees, so it
                    can partition implicitly

E1, E2 and E3 are recomputed for built_oof against every pooled variant as
single unrounded estimands with paired bootstrap intervals.

Runs on the frozen, audited caches; generates nothing.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
import construction_improver_development as dev
import construction_improver_confirmation as conf


SIZES = conf.SIZES
MAX_WINDOWS = conf.MAX_WINDOWS
FOLDS = 3
BOOT = 20000
SEED = 921001


def stat_vector(task):
    s = task['stats']
    return np.asarray([s['log_pool'], s['margin'], s['spread'], s['distinct'],
                       s['head'] / 100.], np.float32)


def oof_views(history, order):
    """Per-task specialist views where no specialist has seen the task."""
    folds = [history[i::FOLDS] for i in range(FOLDS)]
    views = []
    proxied = 0
    for index, fold in enumerate(folds):
        rest = [bank for j, f in enumerate(folds) if j != index for bank in f]
        fold_specialists = dev.build_system(rest)
        for bank in fold:
            for task in bank:
                labels, confidence = dev.task_view(task, fold_specialists)
                for action in order:
                    if action not in confidence:
                        labels[action] = labels['pooled']
                        confidence[action] = confidence['pooled']
                        proxied += 1
                views.append((task, labels, confidence))
    return views, proxied


def router_from_views(views, actions, order):
    rows = []
    targets = defaultdict(list)
    for task, labels, confidence in views:
        rows.append(dev.features(task['stats'], confidence, order))
        for action in actions:
            targets[action].append(labels[action])
    x = np.asarray(rows, np.float32)
    router = {}
    for action in actions:
        y = np.asarray(targets[action], np.int8)
        router[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return router


def big_model():
    return HistGradientBoostingClassifier(
        max_leaf_nodes=60, min_samples_leaf=80, learning_rate=.05,
        max_iter=100, l2_regularization=1., random_state=0)


def fit_single(history, model, augment):
    xs, ys = [], []
    for bank in history:
        for task in bank:
            x = task['x']
            if augment:
                x = np.hstack([x, np.tile(stat_vector(task), (len(x), 1))])
            xs.append(x)
            ys.append(np.asarray(task['labels'], np.int8))
    return model.fit(np.concatenate(xs), np.concatenate(ys))


def deploy_single(transfer, model, augment):
    out = []
    for bank in transfer:
        total = 0
        for task in bank:
            x = task['x']
            if augment:
                x = np.hstack([x, np.tile(stat_vector(task), (len(x), 1))])
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(p)), key=lambda i: (float(p[i]), -i))
            total += task['labels'][pick]
        out.append(total)
    return out


def boot_interval(v, rng):
    v = np.asarray(v, float)
    k = len(v)
    sums = np.array([v[rng.integers(0, k, k)].sum() for _ in range(BOOT)])
    return [float(np.percentile(sums, 2.5)), float(np.percentile(sums, 97.5))]


def paired(left, right, rng):
    v = np.asarray(left, float) - np.asarray(right, float)
    return {'sum': float(v.sum()), 'positive_banks': int((v > 0).sum()),
            'losing_banks': int((v < 0).sum()),
            'bootstrap_interval': boot_interval(v, rng),
            'exact_interval_on_rounded': interval([int(round(x)) for x in v])}


def main():
    dest = conf.DEST
    out_path = dest / 'oof_audit.json'
    if out_path.exists():
        raise RuntimeError('already run')
    rng = np.random.default_rng(SEED)
    history_pool = conf.load_banks('history_a') + conf.load_banks('history_b')
    transfer = conf.load_banks('transfer')
    arms = ('built_insample', 'built_oof', 'pooled', 'pooled_capacity',
            'pooled_featured')
    curve = {}
    proxied_total = 0
    for size in SIZES:
        span = len(history_pool) - size + 1
        starts = list(range(0, span, max(1, span // MAX_WINDOWS)))[:MAX_WINDOWS]
        acc = {arm: np.zeros(len(transfer)) for arm in arms}
        for start in starts:
            history = history_pool[start:start + size]
            specialists = dev.build_system(history)
            order = sorted(specialists)
            actions = order + ['e0']
            router_in = dev.fit_router(history, specialists, actions, order)
            acc['built_insample'] += np.asarray(
                dev.deploy(transfer, specialists, router_in, actions, order), float)
            views, proxied = oof_views(history, order)
            proxied_total += proxied
            router_oof = router_from_views(views, actions, order)
            acc['built_oof'] += np.asarray(
                dev.deploy(transfer, specialists, router_oof, actions, order), float)
            acc['pooled'] += np.asarray(dev.pooled_only(transfer, specialists), float)
            acc['pooled_capacity'] += np.asarray(
                deploy_single(transfer, fit_single(history, big_model(), False),
                              False), float)
            acc['pooled_featured'] += np.asarray(
                deploy_single(transfer, fit_single(history, model_for(15), True),
                              True), float)
        curve[str(size)] = {arm: {'total': float(acc[arm].sum() / len(starts)),
                                  'per_bank': [float(v) for v in acc[arm] / len(starts)]}
                            for arm in arms}
        print('history={:2d} '.format(size) + ' '.join(
            '{}={:6.1f}'.format(arm, curve[str(size)][arm]['total']) for arm in arms),
            flush=True)

    big, small = curve[str(SIZES[-1])], curve[str(SIZES[0])]
    gates = {}
    for base in ('pooled', 'pooled_capacity', 'pooled_featured'):
        e1 = paired(big['built_oof']['per_bank'], big[base]['per_bank'], rng)
        e2 = paired(big['built_oof']['per_bank'], small['built_oof']['per_bank'], rng)
        growth_base = np.asarray(big[base]['per_bank']) - np.asarray(small[base]['per_bank'])
        e3v = (np.asarray(big['built_oof']['per_bank']) - np.asarray(small['built_oof']['per_bank'])) - growth_base
        e3 = {'sum': float(e3v.sum()), 'positive_banks': int((e3v > 0).sum()),
              'losing_banks': int((e3v < 0).sum()),
              'bootstrap_interval': boot_interval(e3v, rng),
              'exact_interval_on_rounded': interval([int(round(x)) for x in e3v]),
              'baseline_growth': float(growth_base.sum())}
        gates[base] = {'E1_oof_vs_baseline': e1, 'E2_oof_growth': e2,
                       'E3_oof_growth_minus_baseline_growth': e3,
                       'E1_passed': bool(e1['sum'] > 0 and e1['bootstrap_interval'][0] > 0),
                       'E3_passed': bool(e3['sum'] > 0 and e3['bootstrap_interval'][0] > 0)}
        print('vs {:16s} E1={:+.1f} {}  E3={:+.1f} {}'.format(
            base, e1['sum'], [round(x, 1) for x in e1['bootstrap_interval']],
            e3['sum'], [round(x, 1) for x in e3['bootstrap_interval']]), flush=True)
    insample_vs_oof = paired(big['built_insample']['per_bank'],
                             big['built_oof']['per_bank'], rng)
    print('in-sample router minus OOF router at 24 banks: {:+.1f} {}'.format(
        insample_vs_oof['sum'], [round(x, 1) for x in insample_vs_oof['bootstrap_interval']]))
    write_json(out_path, {
        'scope': 'information-flow audit: OOF router and stronger pooled baselines',
        'run': dest.name, 'folds': FOLDS, 'sizes': list(SIZES),
        'oof_proxied_action_views': proxied_total,
        'curve': curve, 'gates': gates,
        'insample_router_minus_oof_router_at_largest': insample_vs_oof,
        'limits': [
            'Fold specialists lacking a bin present in the final specialists '
            'are proxied by that fold\'s pooled model; the count is reported.',
            'pooled_capacity matches leaf count, not parameter count or '
            'training compute, and is one reasonable capacity match among several.',
            'Same strided windows as the frozen run; not independent samples.']})


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rep2':
        import construction_confirmation_rep2 as rep2
        rep2.install()
    main()
