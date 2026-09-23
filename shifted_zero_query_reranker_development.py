"""Opened screen of zero-query top-100 ranking learned from shifted feedback."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import features, MODELS as FAMILIAR_MODELS


A = ROOT / 'runs/shifted-ast-seed-transfer-20260918'
B = ROOT / 'runs/post-query-feedback-transfer-20260918'
TARGET = (ROOT / 'runs/shifted-feedback-value-transfer-20260918',
          ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918',
          ROOT / 'runs/combined-ranker-query-transfer-20260918')
OUT = ROOT / 'analysis/shifted-zero-query-reranker-development-20260918.json'
MODELS = ROOT / 'analysis/shifted-zero-query-reranker-models-20260918'
WIDTH = 100


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_arrays(path):
    tasks, base, wide, matrices, records = load_panel(path)
    x, y, groups = [], [], []
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide.get(key, base[key])
        n = min(WIDTH, len(pool))
        feat = features(task, pool, rec, n)
        group = []
        for rank, index in enumerate(rec['orders']['old'][:n]):
            x.append(feat[rank])
            y.append(int(bool(evaluate_program(pool[index]['program'],
                                               task['hidden'][8:]))))
            group.append(len(y) - 1)
        groups.append(group)
    return {'x': np.asarray(x, np.float32), 'y': np.asarray(y, np.int8),
            'groups': groups, 'tasks': len(tasks)}


def fit_models(a, b):
    x = np.r_[a['x'], b['x']]
    y = np.r_[a['y'], b['y']]
    scrambled = b['y'].copy()
    rng = np.random.default_rng(170241)
    for group in b['groups']:
        if len(group) > 1:
            scrambled[group] = rng.permutation(scrambled[group])
    return {'a_top100': model_for(15).fit(a['x'], a['y']),
            'ab_top100': model_for(15).fit(x, y),
            'ab_scrambled': model_for(15).fit(x, np.r_[a['y'], scrambled])}


def call_ids(path):
    if path.name == 'shifted-feedback-value-transfer-20260918':
        return {seed: set(item['cheap']) for seed, item in json.loads(
            (path / 'frozen_allocations.json').read_text()).items()}
    if path.name == 'shifted-survivor-evaluator-transfer-20260918':
        return {seed: set(item) for seed, item in json.loads(
            (path / 'frozen_allocations.json').read_text()).items()}
    frozen = json.loads((path / 'combined_children.json').read_text())
    return {seed: set(ids) for seed, ids in frozen['children']['e0_full']['calls'].items()}


def target_scores(path, models, familiar):
    tasks, base, wide, matrices, records = load_panel(path)
    calls = call_ids(path)
    rows = []
    checked = 0
    predictions = 0
    for task, rec in zip(tasks, records):
        if task['family'] not in ('ast_transition', 'shifted_ast'):
            continue
        key = task['id']
        pool = wide.get(key, base[key])
        old = rec['orders']['old']
        n = min(WIDTH, len(old))
        feat = features(task, pool, rec, n)
        orders = {'e0': rec['orders']['e0']}
        for name, model in {**models, 'familiar_top50': familiar}.items():
            width = min(50, n) if name == 'familiar_top50' else n
            p = model.predict_proba(feat[:width])[:, 1]
            predictions += width
            local = sorted(range(width), key=lambda i: (-float(p[i]), i))
            orders[name] = [old[i] for i in local] + old[width:]
        probe = rec['probe']
        truth = task['hidden'][probe][1]
        surviving = {i for i in range(len(pool))
                     if matrices[key][i][probe] == truth}
        if not surviving:
            surviving = set(range(len(pool)))
        zero = {}
        one = {}
        for name, order in orders.items():
            zero[name] = int(bool(evaluate_program(pool[order[0]]['program'],
                                                   task['hidden'][8:])))
            post = next(i for i in order if i in surviving)
            one[name] = int(bool(evaluate_program(pool[post]['program'],
                                                  task['hidden'][8:])))
            checked += 2
        rows.append({'id': key, 'seed': task['seed'],
                     'domain': 'shifted' if task['family']=='shifted_ast'
                     else 'familiar', 'queried': key in calls[str(task['seed'])],
                     'zero': zero, 'one': one})
    names = tuple(rows[0]['zero'])
    by_bank = defaultdict(list)
    for row in rows:
        by_bank[row['seed']].append(row)
    banks = []
    for seed, group in sorted(by_bank.items()):
        banks.append({'seed': seed, **{name: {
            'zero': sum(r['zero'][name] for r in group),
            'one_each': sum(r['one'][name] for r in group),
            'budgeted': sum(r['one'][name] if r['queried'] else r['zero'][name]
                            for r in group)} for name in names}})
    totals = {name: {field: sum(b[name][field] for b in banks)
                     for field in ('zero', 'one_each', 'budgeted')}
              for name in names}
    comparisons = {}
    for name in names:
        if name == 'e0':
            continue
        comparisons[name] = {}
        for field in ('zero', 'one_each', 'budgeted'):
            diffs = [b[name][field] - b['e0'][field] for b in banks]
            comparisons[name][field] = {
                'gain': sum(diffs), 'positive_banks': sum(x > 0 for x in diffs),
                'losing_banks': sum(x < 0 for x in diffs),
                'interval': interval(diffs)}
    return {'tasks': len(rows), 'candidate_choices_checked': checked,
            'model_predictions': predictions, 'totals': totals,
            'comparisons': comparisons, 'banks': banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development output exists')
    a = source_arrays(A)
    b = source_arrays(B)
    models = fit_models(a, b)
    familiar = joblib.load(FAMILIAR_MODELS / 'top50.joblib')
    MODELS.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, MODELS / f'{name}.joblib', compress=3)
    targets = {path.name: target_scores(path, models, familiar) for path in TARGET}
    result = {'scope': 'opened development only; no fresh claim',
              'source_tasks_a': a['tasks'], 'source_tasks_ab': a['tasks']+b['tasks'],
              'source_candidate_labels_a': len(a['y']),
              'source_candidate_labels_ab': len(a['y'])+len(b['y']),
              'source_positive_labels_ab': int(a['y'].sum()+b['y'].sum()),
              'model_sha256': {name: sha(MODELS / f'{name}.joblib')
                               for name in models},
              'targets': targets}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'targets'},
                      'targets': {name: {k: v for k, v in target.items()
                                         if k != 'banks'}
                                  for name, target in targets.items()}}, indent=2))


if __name__ == '__main__':
    main()
