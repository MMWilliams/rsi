"""Purest improver growth: the improver BUILDS its components, not just routes them.

The confirmed result (`COMPLEXITY-IMPROVER-RESULTS-2026-09-21.md`) tested an
improver that routes among four specialists trained once, outside the experiment,
on opened panels. That leaves two purity gaps: the components are not part of the
evidence, and "improvement" means selection rather than construction.

Here the improver receives only verified history banks and must do everything
itself:

  1. compute the latent complexity partition from its own history labels,
  2. train one specialist per bin on its own history,
  3. fit a router over those specialists from its own history,
  4. deploy on an untouched transfer panel.

Nothing is inherited. More history must therefore buy a better *construction*,
not merely a better choice among fixed options.

The zero-knowledge baseline is the strongest free alternative: **train a single
pooled model on exactly the same history and deploy it everywhere.** That is what
a researcher would do without knowing the partition matters, it uses identical
data and identical compute budget, and beating it is the whole claim.

Development evidence on opened cached panels. A frozen confirmation is separate.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import SOURCE, TARGET, load_cache
import complexity_partition_environment as env


OUT = ROOT / 'analysis/construction-improver-development-20260921.json'
SIZES = (4, 8, 16, 32, 48)
MAX_WINDOWS = 6
TRANSFER_PANEL = TARGET[2]
THRESHOLD = 6
SEED = 914001


def load_banks():
    """Every cached panel as a list of banks, each bank a list of task dicts."""
    panels = {}
    for name in list(SOURCE) + list(TARGET):
        x, meta = load_cache(name)
        grouped = defaultdict(list)
        for task in meta:
            grouped[task['seed']].append({
                'seed': task['seed'], 'panel': name,
                'x': x[task['start']:task['start'] + task['count']],
                'labels': task['labels'], 'e0_label': task['e0_label'],
                'stats': task['stats']})
        panels[name] = [grouped[s] for s in sorted(grouped)]
    return panels


def build_system(history):
    """The improver's entire output, from its history alone."""
    tasks = [t for bank in history for t in bank]
    bins = {}
    for task in tasks:
        bins.setdefault(env.bin_of(task['labels']), []).append(task)

    specialists = {}
    for name, group in bins.items():
        if name == 'unreachable' or len(group) < 8:
            continue
        x = np.concatenate([t['x'] for t in group])
        y = np.concatenate([np.asarray(t['labels'], np.int8) for t in group])
        if 0 < y.sum() < len(y):
            specialists[name] = model_for(15).fit(x, y)
    px = np.concatenate([t['x'] for t in tasks])
    py = np.concatenate([np.asarray(t['labels'], np.int8) for t in tasks])
    specialists['pooled'] = model_for(15).fit(px, py)
    return specialists


def task_view(task, specialists):
    """Each specialist's verified pick and stated confidence on one task."""
    labels = {'e0': task['e0_label']}
    confidence = {}
    for name, model in specialists.items():
        p = model.predict_proba(task['x'])[:, 1]
        pick = max(range(len(p)), key=lambda i: (float(p[i]), -i))
        labels[name] = task['labels'][pick]
        confidence[name] = float(p[pick])
    return labels, confidence


def features(stats, confidence, order):
    return np.asarray([stats['log_pool'], stats['margin'], stats['spread'],
                       stats['distinct'], stats['head'] / 100.]
                      + [confidence[a] for a in order], np.float32)


def fit_router(history, specialists, actions, order):
    rows = []
    targets = defaultdict(list)
    for bank in history:
        for task in bank:
            labels, confidence = task_view(task, specialists)
            rows.append(features(task['stats'], confidence, order))
            for action in actions:
                targets[action].append(labels[action])
    x = np.asarray(rows, np.float32)
    router = {}
    for action in actions:
        y = np.asarray(targets[action], np.int8)
        router[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return router


def deploy(transfer, specialists, router, actions, order):
    """Per-bank correct choices under the improver's own built system."""
    per_bank = []
    for bank in transfer:
        total = 0
        for task in bank:
            labels, confidence = task_view(task, specialists)
            x = features(task['stats'], confidence, order).reshape(1, -1)
            best, best_p = None, -1.
            for action in actions:
                model = router[action]
                p = (model if isinstance(model, float)
                     else float(model.predict_proba(x)[0, 1]))
                if p > best_p or (p == best_p and action < best):
                    best, best_p = action, p
            total += labels[best]
        per_bank.append(total)
    return per_bank


def pooled_only(transfer, specialists):
    """Zero-knowledge baseline: one pooled model on the same history."""
    per_bank = []
    for bank in transfer:
        total = 0
        for task in bank:
            p = specialists['pooled'].predict_proba(task['x'])[:, 1]
            pick = max(range(len(p)), key=lambda i: (float(p[i]), -i))
            total += task['labels'][pick]
        per_bank.append(total)
    return per_bank


def compare(left, right):
    diffs = [int(round(a - b)) for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def main():
    if OUT.exists():
        raise RuntimeError('development exists')
    panels = load_banks()
    transfer = panels[TRANSFER_PANEL]
    history_pool = [bank for name, banks in panels.items()
                    if name != TRANSFER_PANEL for bank in banks]
    print('history banks', len(history_pool), 'transfer banks', len(transfer),
          flush=True)

    curve = {}
    for size in SIZES:
        starts = list(range(0, len(history_pool) - size + 1,
                            max(1, (len(history_pool) - size + 1) // MAX_WINDOWS)))
        starts = starts[:MAX_WINDOWS]
        built = np.zeros(len(transfer))
        pooled = np.zeros(len(transfer))
        totals = []
        for start in starts:
            history = history_pool[start:start + size]
            specialists = build_system(history)
            order = sorted(specialists)
            actions = order + ['e0']
            router = fit_router(history, specialists, actions, order)
            scores = deploy(transfer, specialists, router, actions, order)
            built += np.asarray(scores, float)
            pooled += np.asarray(pooled_only(transfer, specialists), float)
            totals.append(sum(scores))
        built /= len(starts)
        pooled /= len(starts)
        curve[str(size)] = {
            'windows': len(starts),
            'built_total': float(built.sum()),
            'pooled_total': float(pooled.sum()),
            'min_total': int(min(totals)), 'max_total': int(max(totals)),
            'built_per_bank': [float(v) for v in built],
            'pooled_per_bank': [float(v) for v in pooled],
            'built_minus_pooled': compare(list(built), list(pooled))}
        value = curve[str(size)]
        print('history={:2d} windows={} built={:6.1f} pooled={:6.1f} '
              'built-pooled={:+d} {}'.format(
                  size, value['windows'], value['built_total'],
                  value['pooled_total'], value['built_minus_pooled']['gain'],
                  value['built_minus_pooled']['interval']), flush=True)

    largest = curve[str(SIZES[-1])]
    smallest = curve[str(SIZES[0])]
    growth = compare(largest['built_per_bank'], smallest['built_per_bank'])
    pooled_growth = compare(largest['pooled_per_bank'],
                            smallest['pooled_per_bank'])
    against_pooled = largest['built_minus_pooled']
    monotone = all(curve[str(a)]['built_total'] <= curve[str(b)]['built_total']
                   for a, b in zip(SIZES, SIZES[1:]))

    result = {
        'scope': 'opened development; construction improver, nothing inherited',
        'transfer_panel': TRANSFER_PANEL,
        'history_pool_banks': len(history_pool),
        'sizes': list(SIZES), 'curve': curve, 'monotone_built': bool(monotone),
        'gates': {
            'D1_construction_beats_pooling': {
                **against_pooled,
                'passed': bool(against_pooled['gain'] > 0
                               and against_pooled['interval'][0] > 0)},
            'D2_construction_growth': {
                **growth,
                'passed': bool(growth['gain'] >= THRESHOLD
                               and growth['losing_banks'] <= 4
                               and growth['interval'][0] > 0)}},
        'pooled_growth_for_reference': pooled_growth,
        'limits': [
            'Opened cached panels; development evidence only.',
            'The partition rule (bin edges on first-correct rank) is researcher '
            'written; the improver computes the partition and trains every '
            'model, but did not invent the rule itself.',
            'Windows are strided over one history pool and are not independent.',
            'The transfer panel is held out of every history window.']}
    write_json(OUT, result)
    print('monotone_built={} '.format(monotone))
    print('D1 construction beats pooling: {:+d} {}w/{}l {} passed={}'.format(
        against_pooled['gain'], against_pooled['positive_banks'],
        against_pooled['losing_banks'], against_pooled['interval'],
        result['gates']['D1_construction_beats_pooling']['passed']))
    print('D2 construction growth      : {:+d} {}w/{}l {} passed={}'.format(
        growth['gain'], growth['positive_banks'], growth['losing_banks'],
        growth['interval'], result['gates']['D2_construction_growth']['passed']))
    print('pooled-only growth (ref)    : {:+d} {}'.format(
        pooled_growth['gain'], pooled_growth['interval']))


if __name__ == '__main__':
    main()
