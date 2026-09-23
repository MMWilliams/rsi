"""A benchmark whose useful partition cross-cuts its visible one.

Nine action spaces failed because the structure that decides which specialist
works is the same structure that is visible: the mechanism family, readable from
the Unicode block, or recoverable from the specialists' own confidence. A free
heuristic therefore always existed.

This partitions training by **solution complexity** instead: how deep the first
correct candidate sits in the old ranker's order. That property

  - is latent, since knowing it requires knowing the answer,
  - cross-cuts mechanism family, so family matching cannot express it,
  - is plausibly predictable from public pool statistics, which is what P2d needs.

Specialists are trained per complexity bin on two source panels and screened on
three target panels against all four preconditions. Development evidence on
opened panels; nothing is frozen here.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import SOURCE, TARGET, load_cache


OUT = ROOT / 'analysis/complexity-partition-environment-20260920.json'
MODELS = ROOT / 'analysis/complexity-partition-models-20260920'
THRESHOLD = 20
BINS = (('shallow', 0, 3), ('mid', 3, 15), ('deep', 15, 100))


def bin_of(labels):
    """Latent complexity bin: where the first correct candidate sits."""
    for rank, y in enumerate(labels):
        if y:
            for name, low, high in BINS:
                if low <= rank < high:
                    return name
            return BINS[-1][0]
    return 'unreachable'


def panel_tasks(name):
    x, meta = load_cache(name)
    for task in meta:
        task['bin'] = bin_of(task['labels'])
    return x, meta


def rows_for(panels, keep=None):
    xs = []
    ys = []
    for name in panels:
        x, meta = panel_tasks(name)
        for task in meta:
            if keep and task['bin'] != keep:
                continue
            xs.append(x[task['start']:task['start'] + task['count']])
            ys.append(np.asarray(task['labels'], np.int8))
    return np.concatenate(xs), np.concatenate(ys)


def evaluate(name, models):
    x, meta = panel_tasks(name)
    scored = {k: m.predict_proba(x)[:, 1] for k, m in models.items()}
    rows = []
    for task in meta:
        start, count = task['start'], task['count']
        entry = {'seed': task['seed'], 'region': task['region'],
                 'bin': task['bin'], 'stats': task['stats'],
                 'labels': {'e0': task['e0_label']}, 'confidence': {}}
        for key, probabilities in scored.items():
            window = probabilities[start:start + count]
            pick = max(range(count), key=lambda i: (float(window[i]), -i))
            entry['labels'][key] = task['labels'][pick]
            entry['confidence'][key] = float(window[pick])
        rows.append(entry)
    return rows


def totals(rows, picks):
    banks = defaultdict(int)
    for row, action in zip(rows, picks):
        banks[row['seed']] += row['labels'][action]
    return [banks[s] for s in sorted(banks)]


def compare(left, right):
    diffs = [a - b for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def feats(row, scored_actions):
    """Public features only. `scored_actions` are the models that state a
    confidence; e0 is an action but is not a scored model, so it has none."""
    stats = row['stats']
    return np.asarray([stats['log_pool'], stats['margin'], stats['spread'],
                       stats['distinct'], stats['head'] / 100.]
                      + [row['confidence'][a] for a in scored_actions],
                      np.float32)


def main():
    if OUT.exists():
        raise RuntimeError('screen exists')
    names = [b[0] for b in BINS]
    models = {}
    for name in names:
        bx, by = rows_for(SOURCE, keep=name)
        models[name] = model_for(15).fit(bx, by)
    px, py = rows_for(SOURCE)
    models['pooled'] = model_for(15).fit(px, py)
    MODELS.mkdir(parents=True, exist_ok=True)
    for key, model in models.items():
        joblib.dump(model, MODELS / f'{key}.joblib', compress=3)

    actions = names + ['pooled', 'e0']
    panels = {n: evaluate(n, models) for n in TARGET}
    result = {'scope': 'opened development; four-precondition screen of the '
                       'complexity-partition environment',
              'bins': [list(b) for b in BINS], 'threshold': THRESHOLD,
              'source_panels': list(SOURCE), 'panels': {}}

    for name, rows in panels.items():
        counts = defaultdict(int)
        for row in rows:
            counts[row['bin']] += 1
        own = totals(rows, [r['bin'] if r['bin'] in names else 'pooled'
                            for r in rows])
        pooled = totals(rows, ['pooled'] * len(rows))
        confident = totals(rows, [max(models, key=lambda a: (r['confidence'][a], a))
                                  for r in rows])
        oracle = totals(rows, [max(actions, key=lambda a: r['labels'][a])
                               for r in rows])
        best_single = max(actions, key=lambda a: sum(r['labels'][a] for r in rows))
        constant = totals(rows, [best_single] * len(rows))
        defaults = {'pooled': pooled, 'most_confident': confident,
                    'best_constant': constant}
        best_default = max(defaults, key=lambda k: sum(defaults[k]))
        regret = sum(oracle) - sum(defaults[best_default])
        result['panels'][name] = {
            'tasks': len(rows), 'bin_counts': dict(counts),
            'own_bin_oracle_routing': sum(own), 'pooled': sum(pooled),
            'most_confident': sum(confident), 'best_constant': sum(constant),
            'best_constant_action': best_single, 'oracle': sum(oracle),
            'best_default': best_default,
            'best_default_total': sum(defaults[best_default]),
            'default_regret': regret,
            'p2c_passed': bool(regret > THRESHOLD),
            'own_bin_minus_default': compare(own, defaults[best_default])}
        value = result['panels'][name]
        print('{:32s} pooled={:3d} conf={:3d} const={:3d} own_bin={:3d} '
              'oracle={:3d} default={}({}) P2c={:+d} {}'.format(
                  name[:32], value['pooled'], value['most_confident'],
                  value['best_constant'], value['own_bin_oracle_routing'],
                  value['oracle'], best_default, value['best_default_total'],
                  regret, value['p2c_passed']), flush=True)

    target_names = list(TARGET)
    train = [r for n in target_names[:2] for r in panels[n]]
    test = panels[target_names[2]]
    scored_actions = sorted(models)
    xtr = np.asarray([feats(r, scored_actions) for r in train], np.float32)
    selectors = {}
    for action in actions:
        y = np.asarray([r['labels'][action] for r in train], np.int8)
        selectors[action] = (model_for(15).fit(xtr, y) if 0 < y.sum() < len(y)
                             else float(y.mean()))
    xte = np.asarray([feats(r, scored_actions) for r in test], np.float32)
    predicted = {a: (np.full(len(test), m) if isinstance(m, float)
                     else m.predict_proba(xte)[:, 1])
                 for a, m in selectors.items()}
    learned = totals(test, [max(actions, key=lambda a: (float(predicted[a][i]), a))
                            for i in range(len(test))])

    chosen = result['panels'][target_names[2]]
    dname = chosen['best_default']
    dpicks = {'pooled': ['pooled'] * len(test),
              'most_confident': [max(models, key=lambda a: (r['confidence'][a], a))
                                 for r in test],
              'best_constant': [chosen['best_constant_action']] * len(test)}[dname]
    default = totals(test, dpicks)
    against = compare(learned, default)
    result['learnability'] = {
        'train_panels': target_names[:2], 'test_panel': target_names[2],
        'learned': sum(learned), 'default_used': dname,
        'default': sum(default), 'learned_minus_default': against,
        'p2d_passed': bool(against['gain'] > 0 and against['interval'][0] > 0)}
    print('P2d: learned={} vs {}={} -> {:+d} {}w/{}l {} passed={}'.format(
        sum(learned), dname, sum(default), against['gain'],
        against['positive_banks'], against['losing_banks'],
        against['interval'], result['learnability']['p2d_passed']))

    result['verdict'] = {
        'p2c_all_panels': all(v['p2c_passed'] for v in result['panels'].values()),
        'p2d': result['learnability']['p2d_passed']}
    result['limits'] = [
        'Opened panels; development evidence only.',
        'The complexity bin is defined by the old ranker order, so it is latent '
        'but not independent of that ranker.',
        'Own-bin routing uses hidden labels and is an upper reference, not a '
        'deployable policy.',
        'Oracle uses final labels and is not deployable.']
    write_json(OUT, result)
    print('verdict:', result['verdict'])


if __name__ == '__main__':
    main()
