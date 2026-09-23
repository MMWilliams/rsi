"""Improver growth in the complexity-partition environment.

This is the first environment to clear all four preconditions
(`analysis/complexity-partition-environment-20260920.json`): default regret
+123, +101 and +89 against the most-confident rule, and a held-out selector
beating that rule by +19 with interval +5 to +33.

The question this asks is the one that has failed roughly forty times: does a
parent holding **more** verified history build a **better** router than one
holding less, on untouched banks?

Two methodology lessons from today are built in rather than rediscovered:

  - the small-history arm is scored as its **expected** value over every
    contiguous window of that size, never one predeclared draw, because the
    first replication's +80 turned out to be a property of which bank `initial`
    happened to hold;
  - the reference is the **zero-knowledge default**, most-confident, not a weak
    draw, because every previous apparent pass was measured against a baseline
    weaker than a free hand-written rule.

Development evidence on opened panels. A frozen fresh-bank confirmation is a
separate run.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import TARGET
import complexity_partition_environment as env


OUT = ROOT / 'analysis/improver-growth-complexity-20260920.json'
SIZES = (2, 4, 8, 12, 16, 24)
THRESHOLD = 6


def banks_of(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['seed']].append(row)
    return [grouped[s] for s in sorted(grouped)]


def fit_router(tasks, actions, scored_actions):
    """A parent's router, fitted only on the history it holds."""
    x = np.asarray([env.feats(r, scored_actions) for r in tasks], np.float32)
    models = {}
    for action in actions:
        y = np.asarray([r['labels'][action] for r in tasks], np.int8)
        models[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return models


def deploy(models, target, actions, scored_actions):
    x = np.asarray([env.feats(r, scored_actions) for r in target], np.float32)
    predicted = {a: (np.full(len(target), m) if isinstance(m, float)
                     else m.predict_proba(x)[:, 1])
                 for a, m in models.items()}
    picks = [max(actions, key=lambda a: (float(predicted[a][i]), a))
             for i in range(len(target))]
    return picks


def per_bank(target_banks, picks):
    out = []
    index = 0
    for bank in target_banks:
        total = 0
        for row in bank:
            total += row['labels'][picks[index]]
            index += 1
        out.append(total)
    return out


def compare(left, right):
    diffs = [int(round(a - b)) for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    names = [b[0] for b in env.BINS]
    models = {}
    for name in names:
        bx, by = env.rows_for(env.SOURCE, keep=name)
        models[name] = model_for(15).fit(bx, by)
    px, py = env.rows_for(env.SOURCE)
    models['pooled'] = model_for(15).fit(px, py)
    actions = names + ['pooled', 'e0']
    scored_actions = sorted(models)

    panels = {n: env.evaluate(n, models) for n in TARGET}
    target_names = list(TARGET)
    history_banks = (banks_of(panels[target_names[0]])
                     + banks_of(panels[target_names[1]]))
    target_banks = banks_of(panels[target_names[2]])
    target_rows = [r for bank in target_banks for r in bank]

    default_picks = [max(models, key=lambda a: (r['confidence'][a], a))
                     for r in target_rows]
    default = per_bank(target_banks, default_picks)
    oracle = per_bank(target_banks,
                      [max(actions, key=lambda a: r['labels'][a])
                       for r in target_rows])

    curve = {}
    for size in SIZES:
        windows = [history_banks[start:start + size]
                   for start in range(len(history_banks) - size + 1)]
        accumulated = np.zeros(len(target_banks))
        totals = []
        for window in windows:
            tasks = [r for bank in window for r in bank]
            router = fit_router(tasks, actions, scored_actions)
            picks = deploy(router, target_rows, actions, scored_actions)
            scores = per_bank(target_banks, picks)
            accumulated += np.asarray(scores, float)
            totals.append(sum(scores))
        expected = accumulated / len(windows)
        curve[str(size)] = {
            'windows': len(windows),
            'expected_total': float(expected.sum()),
            'min_total': int(min(totals)), 'max_total': int(max(totals)),
            'expected_per_bank': [float(v) for v in expected],
            'vs_default': compare(list(expected), default)}
        value = curve[str(size)]
        print('history={:2d} windows={:2d} expected={:7.1f} [{:d},{:d}] '
              'vs_default={:+d} {}'.format(
                  size, value['windows'], value['expected_total'],
                  value['min_total'], value['max_total'],
                  value['vs_default']['gain'], value['vs_default']['interval']),
              flush=True)

    largest = curve[str(SIZES[-1])]['expected_per_bank']
    smallest = curve[str(SIZES[0])]['expected_per_bank']
    growth = compare(largest, smallest)
    contextual = curve[str(SIZES[-1])]['vs_default']

    result = {
        'scope': 'opened development; improver growth in the '
                 'complexity-partition environment',
        'history_pool_banks': len(history_banks),
        'target_panel': target_names[2], 'target_banks': len(target_banks),
        'default_rule': 'most confident specialist per task, zero knowledge',
        'default_total': sum(default), 'oracle_total': sum(oracle),
        'curve': curve,
        'growth_largest_minus_smallest': growth,
        'contextual_largest_minus_default': contextual,
        'gates': {
            'C1_contextual_value': {
                **contextual,
                'passed': bool(contextual['gain'] > 0
                               and contextual['interval'][0] > 0)},
            'C2_improver_growth': {
                **growth,
                'passed': bool(growth['gain'] >= THRESHOLD
                               and growth['losing_banks'] <= 4
                               and growth['interval'][0] > 0)}},
        'limits': [
            'Opened panels; development evidence. A frozen fresh-bank '
            'confirmation is a separate run.',
            'Contiguous windows over the same history pool are not independent '
            'samples.',
            'The complexity bin defining the specialists is latent but derived '
            'from the old ranker order, so it is not independent of it.',
            'Oracle uses final labels and is not deployable.']}
    write_json(OUT, result)
    print('default={} oracle={}'.format(sum(default), sum(oracle)))
    print('C1 contextual value: {:+d} {}w/{}l {} passed={}'.format(
        contextual['gain'], contextual['positive_banks'],
        contextual['losing_banks'], contextual['interval'],
        result['gates']['C1_contextual_value']['passed']))
    print('C2 improver growth : {:+d} {}w/{}l {} passed={}'.format(
        growth['gain'], growth['positive_banks'], growth['losing_banks'],
        growth['interval'], result['gates']['C2_improver_growth']['passed']))


if __name__ == '__main__':
    main()
