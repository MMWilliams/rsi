"""Does heterogeneous training size make confidence a deceptive signal?

Every action space so far died on P2c: a zero-knowledge rule, usually "trust
whichever specialist is more confident", captured 90 to 98 percent of the
achievable value, leaving an improver nothing to learn.

There is a principled reason that rule might fail. A model's confidence scales
with how much data it saw, not only with whether it is right. The region
specialists exist at depth 25 (about 4.8k labels each) and depth 100 (about 22k
each). If the deep models are systematically more confident wherever both are
available, then "most confident" is biased toward depth regardless of
correctness, and the per-region correction has to be learned from verified
effects rather than guessed.

This screens that action set against all four preconditions before any improver
is built for it. Development evidence on opened panels.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import (
    TARGET, REGIONS, load_cache, MODELS as DEEP)


SHALLOW = ROOT / 'analysis/region-depth-models-20260920'
OUT = ROOT / 'analysis/deceptive-confidence-screen-20260920.json'
DEPTHS = (25, 100)
THRESHOLD = 20


def action_name(region, depth):
    return f'{region}@{depth}'


def load_actions():
    models = {}
    for region in REGIONS:
        models[action_name(region, 100)] = joblib.load(DEEP / f'{region}.joblib')
        models[action_name(region, 25)] = joblib.load(
            SHALLOW / f'{region}@25.joblib')
    return models


def panel_rows(name, models):
    """Per task: each action's verified outcome and its stated confidence."""
    x, meta = load_cache(name)
    scored = {key: model.predict_proba(x)[:, 1] for key, model in models.items()}
    rows = []
    for task in meta:
        start, count = task['start'], task['count']
        labels = task['labels']
        entry = {'seed': task['seed'], 'region': task['region'],
                 'e0': task['e0_label'], 'labels': {}, 'confidence': {},
                 'stats': task['stats']}
        for key, probabilities in scored.items():
            window = probabilities[start:start + count]
            pick = max(range(count), key=lambda i: (float(window[i]), -i))
            entry['labels'][key] = labels[pick]
            entry['confidence'][key] = float(window[pick])
        rows.append(entry)
    return rows


def totals(rows, choose):
    banks = defaultdict(int)
    for row in rows:
        banks[row['seed']] += row['labels'][choose(row)]
    return [banks[s] for s in sorted(banks)]


def compare(left, right):
    diffs = [a - b for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def features_of(row, actions):
    return np.asarray(
        [row['stats']['log_pool'], row['stats']['margin'],
         row['stats']['spread'], row['stats']['distinct']]
        + [float(row['region'] == r) for r in REGIONS]
        + [row['confidence'][a] for a in actions], np.float32)


def main():
    if OUT.exists():
        raise RuntimeError('screen exists')
    models = load_actions()
    actions = sorted(models)
    panels = {name: panel_rows(name, models) for name in TARGET}

    result = {'scope': 'opened development; four-precondition screen of the '
                       'depth-heterogeneous action set',
              'actions': actions, 'threshold': THRESHOLD, 'panels': {}}

    for name, rows in panels.items():
        most_confident = totals(
            rows, lambda r: max(actions, key=lambda a: (r['confidence'][a], a)))
        own_deep = totals(rows, lambda r: action_name(r['region'], 100))
        oracle = totals(rows, lambda r: max(actions, key=lambda a: r['labels'][a]))
        best_single = max(actions,
                          key=lambda a: sum(r['labels'][a] for r in rows))
        constant = totals(rows, lambda r, a=best_single: a)

        # Is confidence biased toward depth regardless of correctness?
        deep_more_confident = np.mean([
            r['confidence'][action_name(r['region'], 100)]
            >= r['confidence'][action_name(r['region'], 25)] for r in rows])
        deep_more_correct = np.mean([
            r['labels'][action_name(r['region'], 100)]
            >= r['labels'][action_name(r['region'], 25)] for r in rows])

        best_default = max((most_confident, own_deep, constant), key=sum)
        result['panels'][name] = {
            'tasks': len(rows),
            'most_confident': sum(most_confident),
            'own_region_deep': sum(own_deep),
            'best_constant': sum(constant), 'best_constant_action': best_single,
            'oracle': sum(oracle),
            'default_regret_vs_most_confident': sum(oracle) - sum(most_confident),
            'default_regret_vs_best_default': sum(oracle) - sum(best_default),
            'p2c_passed': bool(sum(oracle) - sum(best_default) > THRESHOLD),
            'deep_more_confident_rate': float(deep_more_confident),
            'deep_more_correct_rate': float(deep_more_correct),
            'confidence_depth_bias':
                float(deep_more_confident - deep_more_correct)}
        value = result['panels'][name]
        print(f'{name}: most_conf={value["most_confident"]} '
              f'own_deep={value["own_region_deep"]} '
              f'const={value["best_constant"]} oracle={value["oracle"]}  '
              f'P2c regret={value["default_regret_vs_best_default"]} '
              f'passed={value["p2c_passed"]}  '
              f'depth bias={value["confidence_depth_bias"]:+.3f}', flush=True)

    # P2d: can a selector fitted on two panels beat the best default on a third?
    names = list(TARGET)
    train_rows = [r for n in names[:2] for r in panels[n]]
    test_rows = panels[names[2]]
    x = np.asarray([features_of(r, actions) for r in train_rows], np.float32)
    selectors = {}
    for action in actions:
        y = np.asarray([r['labels'][action] for r in train_rows], np.int8)
        selectors[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                             else float(y.mean()))
    xt = np.asarray([features_of(r, actions) for r in test_rows], np.float32)
    predicted = {a: (np.full(len(test_rows), m) if isinstance(m, float)
                     else m.predict_proba(xt)[:, 1])
                 for a, m in selectors.items()}
    banks = defaultdict(int)
    for index, row in enumerate(test_rows):
        pick = max(actions, key=lambda a: (float(predicted[a][index]), a))
        banks[row['seed']] += row['labels'][pick]
    learned = [banks[s] for s in sorted(banks)]

    default_choice = max(
        (('most_confident',
          totals(test_rows, lambda r: max(actions,
                                          key=lambda a: (r['confidence'][a], a)))),
         ('own_region_deep',
          totals(test_rows, lambda r: action_name(r['region'], 100)))),
        key=lambda pair: sum(pair[1]))
    against = compare(learned, default_choice[1])
    result['learnability'] = {
        'train_panels': names[:2], 'test_panel': names[2],
        'learned': sum(learned), 'default_used': default_choice[0],
        'default': sum(default_choice[1]),
        'learned_minus_default': against,
        'p2d_passed': bool(against['gain'] > 0 and against['interval'][0] > 0)}
    print(f'P2d: learned={sum(learned)} vs {default_choice[0]}='
          f'{sum(default_choice[1])} -> {against["gain"]:+d} '
          f'{against["positive_banks"]}w/{against["losing_banks"]}l '
          f'{against["interval"]}  passed={result["learnability"]["p2d_passed"]}')

    result['verdict'] = {
        'p2c_all_panels': all(v['p2c_passed']
                              for v in result['panels'].values()),
        'p2d': result['learnability']['p2d_passed']}
    result['limits'] = [
        'Opened panels; development evidence only.',
        'Depth 25 and depth 100 models differ in training size and in nothing '
        'else, so the confidence comparison is like for like.',
        'The selector sees each action stated confidence as a feature, so it '
        'can learn to distrust depth where that helps.',
        'Oracle uses final labels and is not deployable.']
    write_json(OUT, result)
    print('verdict:', result['verdict'])


if __name__ == '__main__':
    main()
