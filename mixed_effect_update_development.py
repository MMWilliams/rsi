"""Opened cross-fit of mixed-effect feedback for specialist routing."""
from __future__ import annotations

import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from specialist_applicability_transfer import (DEST, SOURCE, B, E0, SPECIALIST,
                                                new_regressor)
from specialist_applicability_development import panel_rows


OUT = ROOT / 'analysis/mixed-effect-update-development-20260918.json'
THRESHOLDS = (0., .05, .1, .15, .2)


def source_rows():
    e0 = joblib.load(E0)
    specialist = joblib.load(SPECIALIST)
    result = []
    for path in SOURCE + (B,):
        result.extend(panel_rows(path, e0, specialist))
    assert len(result) == 384
    return result


def mixed_rows():
    assert json.loads((DEST / 'audit.json').read_text())['passed']
    records = json.loads((DEST / 'frozen_records.json').read_text())
    results = json.loads((DEST / 'results.json').read_text())['tasks']
    allocations = json.loads((DEST / 'frozen_allocations.json').read_text())
    rows = []
    for rec, outcome in zip(records, results):
        assert rec['id'] == outcome['id']
        rows.append({'id': rec['id'], 'seed': rec['seed'],
                     'domain': outcome['domain'],
                     'effect_features': rec['router_features'],
                     'zero': outcome['zero'],
                     'e0': outcome['one']['e0'],
                     'specialist': outcome['one']['specialist'],
                     'effect': outcome['one']['specialist'] - outcome['one']['e0'],
                     'queried': rec['id'] in allocations[str(rec['seed'])]})
    assert len(rows) == 192
    return rows


def fit(rows, effects=None):
    x = np.asarray([r['effect_features'] for r in rows], np.float32)
    y = np.asarray([r['effect'] for r in rows] if effects is None
                   else effects, float)
    return new_regressor().fit(x, y)


def predictions(model, rows):
    return model.predict(np.asarray([r['effect_features'] for r in rows],
                                    np.float32))


def utility(rows, forecast, threshold):
    return sum((r['specialist'] if p > threshold else r['e0'])
               if r['queried'] else r['zero']
               for r, p in zip(rows, forecast))


def select_threshold(rows, forecast):
    # Source feedback is used only for selecting among the frozen small menu.
    return max(THRESHOLDS, key=lambda t: (utility(rows, forecast, t), t))


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    original = source_rows()
    mixed = mixed_rows()
    initial = joblib.load(DEST / 'effect.joblib')
    seeds = sorted({r['seed'] for r in mixed})
    assert len(seeds) == 24
    predictions_out = []
    folds = []
    for fold in range(2):
        training_seeds = set(seeds[fold * 12:(fold + 1) * 12])
        train = [r for r in mixed if r['seed'] in training_seeds]
        test = [r for r in mixed if r['seed'] not in training_seeds]
        assert len(train) == len(test) == 96
        rng = np.random.default_rng(9471 + fold)
        scrambled = np.asarray([r['effect'] for r in train], float)
        for domain in ('familiar', 'shifted'):
            indices = [i for i, r in enumerate(train) if r['domain'] == domain]
            scrambled[indices] = rng.permutation(scrambled[indices])
        duplicate = original[:48] + original[-48:]
        models = {'i0': initial,
                  'i1': fit(original + train),
                  'scrambled': fit(original + train,
                      [r['effect'] for r in original] + scrambled.tolist()),
                  'duplicate': fit(original + duplicate)}
        source_forecast = {name: predictions(model, train)
                           for name, model in models.items()}
        chosen = {name: select_threshold(train, source_forecast[name])
                  for name in models}
        target_forecast = {name: predictions(model, test)
                           for name, model in models.items()}
        fold_summary = {'fold': fold, 'training_seeds': sorted(training_seeds),
                        'selected_thresholds': chosen,
                        'test_correct': {name: {str(t): utility(
                            test, forecast, t) for t in THRESHOLDS}
                            for name, forecast in target_forecast.items()},
                        'selected_correct': {name: utility(test,
                            target_forecast[name], chosen[name]) for name in models}}
        folds.append(fold_summary)
        for i, row in enumerate(test):
            predictions_out.append({'id': row['id'], 'seed': row['seed'],
                'domain': row['domain'], 'queried': row['queried'],
                'zero': row['zero'], 'e0': row['e0'],
                'specialist': row['specialist'], 'effect': row['effect'],
                'forecast': {name: float(values[i])
                             for name, values in target_forecast.items()},
                'thresholds': chosen})
    predictions_out.sort(key=lambda r: r['id'])
    banks = []
    for seed in seeds:
        group = [r for r in predictions_out if r['seed'] == seed]
        bank = {'seed': seed}
        for name in ('i0', 'i1', 'scrambled', 'duplicate'):
            bank[name + '_zero'] = sum(
                (r['specialist'] if r['forecast'][name] > 0 else r['e0'])
                if r['queried'] else r['zero'] for r in group)
            bank[name + '_selected'] = sum(
                (r['specialist'] if r['forecast'][name] > r['thresholds'][name]
                 else r['e0']) if r['queried'] else r['zero'] for r in group)
        banks.append(bank)
    totals = {name: sum(b[name] for b in banks) for name in banks[0]
              if name != 'seed'}
    comparisons = {}
    for mode in ('zero', 'selected'):
        for name in ('i1', 'scrambled', 'duplicate'):
            diff = [b[name + '_' + mode] - b['i0_' + mode] for b in banks]
            comparisons[name + '_minus_i0_' + mode] = {
                'gain': sum(diff), 'positive_banks': sum(x > 0 for x in diff),
                'losing_banks': sum(x < 0 for x in diff),
                'interval': interval(diff)}
    result = {'scope': 'opened cross-fit development; no fresh transfer claim',
              'original_effect_tasks': len(original),
              'new_feedback_tasks_per_fold': 96,
              'held_out_tasks_per_fold': 96,
              'totals': totals, 'comparisons': comparisons,
              'folds': folds, 'banks': banks,
              'predictions': predictions_out}
    write_json(OUT, result)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('banks', 'predictions')}, indent=2))


if __name__ == '__main__':
    main()
