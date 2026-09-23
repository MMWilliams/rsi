"""Opened-bank screen of combined specialist candidate evaluators."""
from __future__ import annotations

import json

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from wide_candidate_reranker_development import features
from dual_specialist_seed_evaluator import load_models
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval


SOURCE = (ROOT / 'runs/zero-query-mixed-integration-transfer-20260918',
          ROOT / 'runs/three-action-improver-transfer-20260918')
ADDED = ROOT / 'runs/dual-specialist-integration-transfer-20260918'
TARGET = ROOT / 'runs/selective-width-feedback-transfer-20260918'
OUT = ROOT / 'analysis/candidate-stacking-development-20260918.json'
MODELS = ROOT / 'analysis/candidate-stacking-models-20260918'


def panel(path, specialists):
    tasks = json.loads((path / 'sealed_bank.json').read_text())
    base = json.loads((path / 'base_pools.json').read_text())
    wide = json.loads((path / 'ast_wide_pools.json').read_text())
    records = json.loads((path / 'frozen_records.json').read_text())
    rows, xstruct, xstack, xmeta, y = [], [], [], [], []
    for task, rec in zip(tasks, records):
        pool = wide.get(task['id'], base[task['id']])
        old = rec['orders']['old']
        n = min(100, len(old))
        feat = features(task, pool, rec, n)
        pf = specialists['familiar'].predict_proba(feat)[:, 1]
        ps = specialists['shifted'].predict_proba(feat)[:, 1]
        scores = np.asarray(rec['old_scores'], float)
        std = max(float(scores.std()), .05)
        score_feature = (scores[old[:n]] - scores[old[0]]) / std
        candidate_extra = np.stack((pf, ps, np.maximum(pf, ps),
            np.abs(pf - ps), pf * ps, score_feature,
            np.arange(n) / 100.), axis=1).astype(np.float32)
        labels = np.asarray([int(bool(evaluate_program(pool[i]['program'],
                                                   task['hidden'][8:])))
                             for i in old[:n]], np.int8)
        start = len(y)
        y.extend(labels.tolist())
        xstruct.append(feat)
        xstack.append(np.c_[feat, candidate_extra])
        xmeta.append(candidate_extra)
        rows.append({'id': task['id'], 'seed': task['seed'],
                     'domain': 'shifted' if task['family'] == 'shifted_ast'
                     else 'familiar', 'start': start, 'count': n,
                     'old_top': old[0], 'e0_top': rec['orders']['e0'][0],
                     'pool_size': len(pool)})
    return {'rows': rows, 'struct': np.concatenate(xstruct),
            'stack': np.concatenate(xstack), 'meta': np.concatenate(xmeta),
            'y': np.asarray(y, np.int8)}


def merged(panels):
    return {name: np.concatenate([p[name] for p in panels])
            for name in ('struct', 'stack', 'meta', 'y')}


def fit(data):
    return {'pooled': model_for(15).fit(data['struct'], data['y']),
            'stacked': model_for(15).fit(data['stack'], data['y']),
            'meta_logistic': make_pipeline(
                StandardScaler(), LogisticRegression(C=.1, max_iter=1000,
                                                       random_state=0)).fit(
                data['meta'], data['y'])}


def evaluate(panel, models):
    arrays = panel
    p = {}
    for name, model in models.items():
        kind = 'struct' if 'pooled' in name else (
            'meta' if 'logistic' in name else 'stack')
        p[name] = model.predict_proba(arrays[kind])[:, 1]
    pf = arrays['meta'][:, 0]
    ps = arrays['meta'][:, 1]
    p.update({'candidate_max': np.maximum(pf, ps),
              'candidate_mean': (pf + ps) / 2,
              'candidate_product': pf * ps})
    rows = []
    for row in arrays['rows']:
        a, b = row['start'], row['start'] + row['count']
        labels = arrays['y'][a:b]
        choices = {name: a + int(np.argmax(prob[a:b])) for name, prob in p.items()}
        familiar = a + int(np.argmax(pf[a:b]))
        shifted = a + int(np.argmax(ps[a:b]))
        confidence = shifted if ps[shifted] > pf[familiar] else familiar
        choices.update({'dual_confidence': confidence,
                        'familiar': familiar, 'shifted': shifted,
                        'old': a})
        outcomes = {name: int(arrays['y'][idx]) for name, idx in choices.items()}
        rows.append({'seed': row['seed'], 'domain': row['domain'],
                     'outcomes': outcomes, 'top100_reachable': int(any(labels))})
    banks = []
    for seed in sorted({r['seed'] for r in rows}):
        group = [r for r in rows if r['seed'] == seed]
        names = rows[0]['outcomes']
        banks.append({'seed': seed, 'reachable': sum(r['top100_reachable'] for r in group),
                      **{name: sum(r['outcomes'][name] for r in group)
                         for name in names}})
    totals = {key: sum(b[key] for b in banks) for key in banks[0] if key != 'seed'}
    comparisons = {}
    for name in ('early_stacked', 'later_stacked', 'early_pooled',
                 'candidate_max', 'candidate_mean', 'candidate_product'):
        if name not in totals:
            continue
        d = [b[name] - b['dual_confidence'] for b in banks]
        comparisons[name + '_minus_dual'] = {
            'gain': sum(d), 'wins': sum(v > 0 for v in d),
            'losses': sum(v < 0 for v in d), 'interval': interval(d)}
    if 'later_stacked' in totals:
        d = [b['later_stacked'] - b['early_stacked'] for b in banks]
        comparisons['later_minus_early_stacked'] = {
            'gain': sum(d), 'wins': sum(v > 0 for v in d),
            'losses': sum(v < 0 for v in d), 'interval': interval(d)}
    return {'tasks': len(rows), 'candidate_labels': len(arrays['y']),
            'totals': totals, 'comparisons': comparisons, 'banks': banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development output exists')
    paths = SOURCE + (ADDED, TARGET)
    assert all(json.loads((path / 'audit.json').read_text())['passed']
               for path in paths)
    specialists = load_models()
    panels = [panel(path, specialists) for path in paths]
    first = merged(panels[:2])
    later = merged(panels[:3])
    early_models = fit(first)
    later_models = fit(later)
    models = {f'early_{name}': model for name, model in early_models.items()}
    models.update({f'later_{name}': model for name, model in later_models.items()})
    MODELS.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, MODELS / f'{name}.joblib', compress=3)
    targets = {path.name: evaluate(data, models)
               for path, data in zip(paths[2:], panels[2:])}
    result = {'scope': 'opened development only',
              'source': {'early_tasks': sum(len(p['rows']) for p in panels[:2]),
                         'later_tasks': sum(len(p['rows']) for p in panels[:3]),
                         'early_candidate_labels': len(first['y']),
                         'later_candidate_labels': len(later['y'])},
              'targets': targets}
    write_json(OUT, result)
    print(json.dumps({'scope': result['scope'], 'source': result['source'],
                      'targets': {key: {k: v for k, v in val.items() if k != 'banks'}
                                  for key, val in targets.items()}}, indent=2))


if __name__ == '__main__':
    main()
