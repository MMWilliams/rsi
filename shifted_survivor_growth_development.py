"""Opened incremental feedback screen for a top-100 post-query candidate evaluator."""
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
from post_query_candidate_development import E0, load_panel
from wide_candidate_reranker_development import features
from wide_post_query_development import MODELS as FAMILIAR_MODELS


A = ROOT / 'runs/shifted-ast-seed-transfer-20260918'
B = ROOT / 'runs/post-query-feedback-transfer-20260918'
C = ROOT / 'runs/shifted-feedback-value-transfer-20260918'
OUT = ROOT / 'analysis/shifted-survivor-growth-development-20260918.json'
MODELS = ROOT / 'analysis/shifted-survivor-growth-models-20260918'
WIDTH = 100


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_for(task, pool, rec, matrix, e0):
    old = rec['orders']['old']
    n = min(WIDTH, len(old))
    feat = features(task, pool, rec, n)
    prob = e0.predict_proba(feat)[:, 1]
    probe = rec['probe']
    truth = task['hidden'][probe][1]
    surviving = {i for i in range(len(pool)) if matrix[i][probe] == truth}
    if not surviving:
        surviving = set(range(len(pool)))
    head = [(rank, index) for rank, index in enumerate(old[:n])
            if index in surviving]
    scores = np.asarray(rec['old_scores'], float)
    std = max(float(scores.std()), .05)
    best = max(scores[i] for i in surviving)
    e0_rank = {index: rank for rank, index in enumerate(rec['orders']['e0'])}
    anchor = rec['orders']['e0'][0]
    rows = []
    for rank, index in head:
        agree = sum(matrix[index][j] == matrix[anchor][j]
                    for j in range(8)) / 8
        extra = np.asarray([float(prob[rank]), e0_rank[index] / 20,
                            (scores[index] - best) / std,
                            len(head) / n, len(surviving) / len(pool), agree],
                           np.float32)
        rows.append({'index': index, 'old_rank': rank,
                     'plain': feat[rank], 'sensor': np.r_[feat[rank], extra]})
    return rows, surviving


def source_arrays(path, e0):
    tasks, base, wide, matrices, records = load_panel(path)
    plain, sensor, labels, ranks, groups = [], [], [], [], []
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide.get(key, base[key])
        rows, _ = rows_for(task, pool, rec, matrices[key], e0)
        group = []
        for row in rows:
            plain.append(row['plain'])
            sensor.append(row['sensor'])
            labels.append(int(bool(evaluate_program(pool[row['index']]['program'],
                                                    task['hidden'][8:]))))
            ranks.append(row['old_rank'])
            group.append(len(labels) - 1)
        groups.append(group)
    return {'plain': np.asarray(plain, np.float32),
            'sensor': np.asarray(sensor, np.float32),
            'labels': np.asarray(labels, np.int8),
            'ranks': np.asarray(ranks, int), 'groups': groups,
            'tasks': len(tasks)}


def combine(a, b, field):
    return np.concatenate((a[field], b[field]))


def fit_models(a, b):
    all_sensor = combine(a, b, 'sensor')
    all_plain = combine(a, b, 'plain')
    y = combine(a, b, 'labels')
    mask50 = combine(a, b, 'ranks') < 50
    scrambled = b['labels'].copy()
    rng = np.random.default_rng(118391)
    for group in b['groups']:
        if len(group) > 1:
            scrambled[group] = rng.permutation(scrambled[group])
    scrambled_y = np.r_[a['labels'], scrambled]
    return {'a_sensor100': model_for(15).fit(a['sensor'], a['labels']),
            'ab_sensor100': model_for(15).fit(all_sensor, y),
            'ab_plain100': model_for(15).fit(all_plain, y),
            'ab_sensor50': model_for(15).fit(all_sensor[mask50], y[mask50]),
            'ab_scrambled100': model_for(15).fit(all_sensor, scrambled_y)}


def target_scores(path, e0, models, familiar):
    tasks, base, wide, matrices, records = load_panel(path)
    allocation = json.loads((path / 'frozen_allocations.json').read_text())
    outcomes = []
    checked = 0
    predictions = 0
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide.get(key, base[key])
        rows, surviving = rows_for(task, pool, rec, matrices[key], e0)
        baseline = next(i for i in rec['orders']['e0'] if i in surviving)
        choice = {'e0': baseline,
                  'familiar_plain50': rec['wide_choices']['plain'],
                  'familiar_sensor50': rec['wide_choices']['sensor']}
        for name, model in models.items():
            sub = [row for row in rows if name != 'ab_sensor50'
                   or row['old_rank'] < 50]
            if not sub:
                choice[name] = baseline
                continue
            field = 'plain' if 'plain' in name else 'sensor'
            x = np.asarray([row[field] for row in sub], np.float32)
            p = model.predict_proba(x)[:, 1]
            predictions += len(sub)
            pick = max(range(len(sub)), key=lambda i: (float(p[i]), -i))
            choice[name] = sub[pick]['index']
        zero = int(bool(evaluate_program(
            pool[rec['orders']['e0'][0]]['program'], task['hidden'][8:])))
        one = {name: int(bool(evaluate_program(pool[index]['program'],
                    task['hidden'][8:]))) for name, index in choice.items()}
        checked += 1 + len(choice)
        outcomes.append({'id': key, 'seed': task['seed'], 'zero': zero,
                         'one': one, 'top100_survivors': len(rows)})
    names = tuple(outcomes[0]['one'])
    by_seed = defaultdict(list)
    for row in outcomes:
        by_seed[row['seed']].append(row)
    banks = []
    for seed, group in sorted(by_seed.items()):
        chosen = set(allocation[str(seed)]['cheap'])
        banks.append({'seed': seed, 'zero': sum(r['zero'] for r in group),
                      'one_each': {name: sum(r['one'][name] for r in group)
                                   for name in names},
                      'budgeted': {name: sum(r['one'][name] if r['id'] in chosen
                                             else r['zero'] for r in group)
                                   for name in names}})
    totals = {field: {name: sum(bank[field][name] for bank in banks)
                      for name in names} for field in ('one_each', 'budgeted')}
    comparisons = {}
    for name in names:
        if name == 'e0':
            continue
        comparisons[name] = {}
        for field in ('one_each', 'budgeted'):
            diff = [bank[field][name] - bank[field]['e0'] for bank in banks]
            comparisons[name][field] = {
                'gain': sum(diff), 'positive_banks': sum(x > 0 for x in diff),
                'losing_banks': sum(x < 0 for x in diff),
                'interval': interval(diff)}
    return {'tasks': len(tasks), 'candidate_choices_checked': checked,
            'new_model_predictions': predictions,
            'zero_e0': sum(b['zero'] for b in banks),
            'top100_survivor_rows': sum(r['top100_survivors'] for r in outcomes),
            'totals': totals, 'comparisons': comparisons, 'banks': banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development output exists')
    e0 = joblib.load(E0)
    a = source_arrays(A, e0)
    b = source_arrays(B, e0)
    models = fit_models(a, b)
    MODELS.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, MODELS / f'{name}.joblib', compress=3)
    familiar = {name: joblib.load(FAMILIAR_MODELS / f'{name}.joblib')
                for name in ('plain', 'sensor')}
    target = target_scores(C, e0, models, familiar)
    result = {'scope': 'opened development; no fresh promotion claim',
              'shifted_source_tasks_a': a['tasks'],
              'shifted_source_tasks_ab': a['tasks'] + b['tasks'],
              'source_survivor_labels_a': len(a['labels']),
              'source_survivor_labels_ab': len(a['labels']) + len(b['labels']),
              'source_positive_labels_ab': int(a['labels'].sum() + b['labels'].sum()),
              'model_sha256': {name: sha(MODELS / f'{name}.joblib')
                               for name in models},
              'target': target}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'target'},
                      'target': {k: v for k, v in target.items() if k != 'banks'}},
                     indent=2))


if __name__ == '__main__':
    main()
