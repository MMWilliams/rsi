"""Opened screen of direct, weighted and two-head edit-effect predictors."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from mixed_effect_update_development import source_rows, mixed_rows
from specialist_applicability_transfer import DEST, new_regressor


OUT = ROOT / 'analysis/effect-predictor-alternatives-development-20260918.json'


def fit_models(rows):
    x = np.asarray([r['effect_features'] for r in rows], np.float32)
    effect = np.asarray([r['effect'] for r in rows], float)
    e0 = np.asarray([r['e0'] for r in rows], int)
    specialist = np.asarray([r['specialist'] for r in rows], int)
    result = {'base': joblib.load(DEST / 'effect.joblib')}
    for name, pos, neg in (('weighted2', 2., 2.), ('weighted4', 4., 4.),
                           ('harm6', 3., 6.)):
        weight = np.where(effect > 0, pos, np.where(effect < 0, neg, 1.))
        result[name] = new_regressor().fit(x, effect, sample_weight=weight)
    result['head_e0'] = HistGradientBoostingClassifier(
        max_depth=3, max_iter=70, learning_rate=.05,
        min_samples_leaf=16, l2_regularization=5, random_state=27).fit(x, e0)
    result['head_specialist'] = HistGradientBoostingClassifier(
        max_depth=3, max_iter=70, learning_rate=.05,
        min_samples_leaf=16, l2_regularization=5, random_state=27).fit(x, specialist)
    scaler = StandardScaler().fit(x)
    z = scaler.transform(x)
    result['scaler'] = scaler
    for lam in (10., 100.):
        result[f'ridge{int(lam)}'] = Ridge(alpha=lam).fit(z, effect)
    result['logit'] = LogisticRegression(
        C=.1, max_iter=1000, class_weight='balanced', random_state=27).fit(
            z, effect.astype(int))
    return result


def predict(models, rows):
    x = np.asarray([r['effect_features'] for r in rows], np.float32)
    z = models['scaler'].transform(x)
    result = {name: model.predict(x) for name, model in models.items()
              if name in ('base', 'weighted2', 'weighted4', 'harm6')}
    result['twohead'] = (models['head_specialist'].predict_proba(x)[:, 1] -
                         models['head_e0'].predict_proba(x)[:, 1])
    result['ridge10'] = models['ridge10'].predict(z)
    result['ridge100'] = models['ridge100'].predict(z)
    p = models['logit'].predict_proba(z)
    labels = list(models['logit'].classes_)
    result['logit'] = p[:, labels.index(1)] - p[:, labels.index(-1)]
    return result


def score(rows, predictions):
    banks = []
    for seed in sorted({r['seed'] for r in rows}):
        ids = [i for i, r in enumerate(rows) if r['seed'] == seed]
        bank = {'seed': seed}
        for name, values in predictions.items():
            bank[name] = sum(
                (rows[i]['specialist'] if values[i] > 0 else rows[i]['e0'])
                if rows[i]['queried'] else rows[i]['zero'] for i in ids)
            for domain in ('familiar', 'shifted'):
                bank[f'{name}_{domain}'] = sum(
                    (rows[i]['specialist'] if values[i] > 0 else rows[i]['e0'])
                    if rows[i]['queried'] else rows[i]['zero'] for i in ids
                    if rows[i]['domain'] == domain)
        banks.append(bank)
    totals = {name: sum(b[name] for b in banks) for name in banks[0]
              if name != 'seed'}
    comparison = {}
    for name in predictions:
        diff = [b[name] - b['base'] for b in banks]
        comparison[name] = {'gain_vs_base': sum(diff),
                            'positive_banks': sum(x > 0 for x in diff),
                            'losing_banks': sum(x < 0 for x in diff),
                            'interval': interval(diff),
                            'effect_mse': float(np.mean((predictions[name] -
                                np.asarray([r['effect'] for r in rows])) ** 2))}
    return {'totals': totals, 'comparisons': comparison, 'banks': banks}


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    source = source_rows()
    target = mixed_rows()
    assert len(source) == 384 and len(target) == 192
    models = fit_models(source)
    predictions = predict(models, target)
    result = {'scope': 'opened development only; common 384 task effect source',
              'source_tasks': len(source), 'target_tasks': len(target),
              'target': score(target, predictions)}
    write_json(OUT, result)
    print(json.dumps({'scope': result['scope'],
                      'target': {k: v for k, v in result['target'].items()
                                 if k != 'banks'}}, indent=2))


if __name__ == '__main__':
    main()
