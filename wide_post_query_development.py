"""Opened-bank screen of top-50 survivor ranking after exact output feedback."""
from __future__ import annotations

import hashlib
import json
import time

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import SOURCE, E0, load_panel
from wide_candidate_reranker_development import features


TARGET = (ROOT / 'runs/shifted-ast-seed-transfer-20260918',
          ROOT / 'runs/post-query-feedback-transfer-20260918',
          ROOT / 'runs/combined-ranker-query-transfer-20260918')
OUT = ROOT / 'analysis/wide-post-query-development-20260918.json'
MODELS = ROOT / 'analysis/wide-post-query-models-20260918'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_for(task, pool, rec, matrix, e0):
    old = rec['orders']['old']
    n = min(50, len(pool))
    feat = features(task, pool, rec, n)
    prob = e0.predict_proba(feat)[:, 1]
    probe = rec['probe']
    truth = task['hidden'][probe][1]
    surviving = {i for i in range(len(pool)) if matrix[i][probe] == truth}
    if not surviving:
        surviving = set(range(len(pool)))
    head = [(rank, i) for rank, i in enumerate(old[:n]) if i in surviving]
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
        rows.append((index, feat[rank], np.r_[feat[rank], extra]))
    return rows, surviving


def source_arrays(e0):
    plain, sensor, labels, counts = [], [], [], []
    for path in SOURCE:
        tasks, base, wide, matrices, records = load_panel(path)
        count = 0
        for task, rec in zip(tasks, records):
            key = task['id']
            pool = wide.get(key, base[key])
            rows, _ = rows_for(task, pool, rec, matrices[key], e0)
            for index, p, s in rows:
                plain.append(p)
                sensor.append(s)
                labels.append(int(bool(evaluate_program(pool[index]['program'],
                                                        task['hidden'][8:]))))
                count += 1
        counts.append({'panel': path.name, 'candidate_labels': count})
    return (np.asarray(plain, np.float32), np.asarray(sensor, np.float32),
            np.asarray(labels, np.int8), counts)


def call_ids(path):
    if path.name == 'post-query-feedback-transfer-20260918':
        return {seed: set(ids) for seed, ids in json.loads(
            (path / 'frozen_allocations.json').read_text()).items()}
    if 'shifted-ast' in path.name:
        return {seed: set(row['cheap']) for seed, row in json.loads(
            (path / 'frozen_allocations.json').read_text()).items()}
    children = json.loads((path / 'combined_children.json').read_text())
    return {seed: set(ids) for seed, ids in children['children']['e0_full']['calls'].items()}


def target_scores(path, e0, models):
    tasks, base, wide, matrices, records = load_panel(path)
    calls = call_ids(path)
    rows = []
    checked = 0
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide.get(key, base[key])
        candidates, surviving = rows_for(task, pool, rec, matrices[key], e0)
        baseline = next(i for i in rec['orders']['e0'] if i in surviving)
        choices = {'e0': baseline}
        for name, model in models.items():
            if not candidates:
                choices[name] = baseline
                continue
            x = np.asarray([row[1 if name == 'plain' else 2]
                            for row in candidates], np.float32)
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(candidates)), key=lambda j: (float(p[j]), -j))
            choices[name] = candidates[pick][0]
        one = {name: int(bool(evaluate_program(pool[index]['program'],
                          task['hidden'][8:]))) for name, index in choices.items()}
        zero = int(bool(evaluate_program(
            pool[rec['orders']['e0'][0]]['program'], task['hidden'][8:])))
        checked += len(one) + 1
        rows.append({'id': key, 'seed': task['seed'], 'zero': zero, 'one': one})
    banks = []
    for seed in sorted({r['seed'] for r in rows}):
        group = [r for r in rows if r['seed'] == seed]
        chosen = calls[str(seed)]
        banks.append({'seed': seed, 'zero': sum(r['zero'] for r in group),
                      'one_each': {name: sum(r['one'][name] for r in group)
                                   for name in ('e0',) + tuple(models)},
                      'budgeted': {name: sum(r['one'][name] if r['id'] in chosen
                                             else r['zero'] for r in group)
                                   for name in ('e0',) + tuple(models)}})
    totals = {field: {name: sum(b[field][name] for b in banks)
                      for name in ('e0',) + tuple(models)}
              for field in ('one_each', 'budgeted')}
    comparisons = {}
    for name in models:
        comparisons[name] = {}
        for field in totals:
            diffs = [b[field][name] - b[field]['e0'] for b in banks]
            comparisons[name][field] = {
                'gain': sum(diffs), 'positive_banks': sum(x > 0 for x in diffs),
                'losing_banks': sum(x < 0 for x in diffs),
                'interval': interval(diffs)}
    return {'tasks': len(tasks), 'choices_checked': checked,
            'zero_e0': sum(b['zero'] for b in banks),
            'totals': totals, 'comparisons': comparisons, 'banks': banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development output exists')
    started = time.perf_counter()
    e0 = joblib.load(E0)
    x, z, y, counts = source_arrays(e0)
    models = {'plain': model_for(15).fit(x, y),
              'sensor': model_for(15).fit(z, y)}
    MODELS.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, MODELS / f'{name}.joblib', compress=3)
    targets = {path.name: target_scores(path, e0, models) for path in TARGET}
    result = {'scope': 'opened development only; all target labels previously opened',
              'source_tasks': 1152, 'source_survivor_labels': len(y),
              'source_positive_labels': int(y.sum()), 'source_panels': counts,
              'model_sha256': {name: sha(MODELS / f'{name}.joblib') for name in models},
              'targets': targets, 'wall_seconds': time.perf_counter() - started}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'targets'},
                      'targets': {name: {k: v for k, v in target.items() if k != 'banks'}
                                  for name, target in targets.items()}}, indent=2))


if __name__ == '__main__':
    main()
