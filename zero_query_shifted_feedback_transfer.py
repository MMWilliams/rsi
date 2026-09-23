"""Frozen fresh-bank test of evaluator growth from verified candidate feedback."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import shifted_ast_bank
from cross_family_meta_improver_transfer import interval
from wide_candidate_reranker_development import features, MODELS as FAMILIAR
from shifted_zero_query_reranker_development import MODELS
import post_query_feedback_transfer as previous


DEST = ROOT / 'runs/zero-query-shifted-feedback-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-zero-query-shifted-feedback-transfer.md'
SCRIPT = ROOT / 'zero_query_shifted_feedback_transfer.py'
SEEDS = tuple(range(903500, 903524))
NAMES = ('e0', 'familiar_top50', 'a_top100', 'ab_top100', 'ab_scrambled')
MODEL_NAMES = NAMES[2:]
SOURCE = (ROOT / 'runs/shifted-ast-seed-transfer-20260918',
          ROOT / 'runs/post-query-feedback-transfer-20260918')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False))


def tasks_for():
    return [{**t, 'seed': s} for s in SEEDS
            for t in shifted_ast_bank(s, 8, visible=1, hidden=23)]


def public_run(tasks):
    old = previous.SEEDS
    previous.SEEDS = SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS = old


def models_for():
    models = {name: joblib.load(MODELS / f'{name}.joblib')
              for name in MODEL_NAMES}
    models['familiar_top50'] = joblib.load(FAMILIAR / 'top50.joblib')
    return models


def freeze_orders(tasks, wide, records, models):
    count = {name: 0 for name in models}
    for task, rec in zip(tasks, records):
        pool = wide[task['id']]
        old = rec['orders']['old']
        n = min(100, len(old))
        x = features(task, pool, rec, n)
        orders = {'e0': rec['orders']['e0']}
        for name, model in models.items():
            width = min(50, n) if name == 'familiar_top50' else n
            scores = model.predict_proba(x[:width])[:, 1]
            count[name] += width
            indices = sorted(range(width), key=lambda i: (-float(scores[i]), i))
            orders[name] = [old[i] for i in indices] + old[width:]
        rec['zero_query_orders'] = orders
    return records, count


def manifest_for(cost, count):
    return {'protocol_sha256': sha(PROTOCOL), 'script_sha256': sha(SCRIPT),
            'model_sha256': {name: sha(MODELS / f'{name}.joblib')
                             for name in MODEL_NAMES},
            'familiar_sha256': sha(FAMILIAR / 'top50.joblib'),
            'source_audit_sha256': [sha(p / 'audit.json') for p in SOURCE],
            'seeds': SEEDS, 'tasks': 192, 'calls_per_bank': 4,
            'candidate_score_count': count,
            'cost': cost,
            'frozen_sha256': {name: sha(DEST / name) for name in
                              ('sealed_bank.json', 'base_pools.json',
                               'ast_wide_pools.json', 'predicted_probe_outputs.json',
                               'frozen_records.json', 'frozen_allocations.json',
                               'frozen_forecasts.json')}}


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    assert all(json.loads((p / 'audit.json').read_text())['passed'] for p in SOURCE)
    models = models_for()
    tasks = tasks_for()
    base, wide, predicted, records, allocation, forecasts, cost = public_run(tasks)
    records, count = freeze_orders(tasks, wide, records, models)
    DEST.mkdir(parents=True)
    for name, value in (('sealed_bank.json', tasks), ('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('predicted_probe_outputs.json', predicted),
                        ('frozen_records.json', records),
                        ('frozen_allocations.json', allocation),
                        ('frozen_forecasts.json', forecasts)):
        write_json(DEST / name, value)
    cost['zero_query_candidate_scores'] = count
    manifest = manifest_for(cost, count)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'frozen', 'tasks': len(tasks),
                      'predicted_output_cells': cost['predicted_output_cells'],
                      'candidate_score_count': count}, indent=2))


def outcomes_for(tasks, wide, predicted, records):
    outcomes = []
    checked = 0
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide[key]
        assert rec['id'] == key and digest(pool) == rec['pool_sha256']
        labels = [int(bool(evaluate_program(row['program'], task['hidden'][8:])))
                  for row in pool]
        checked += len(labels)
        truth = task['hidden'][rec['probe']][1]
        survivors = {i for i in range(len(pool))
                     if predicted[key][i][rec['probe']] == truth}
        if not survivors:
            survivors = set(range(len(pool)))
        old = rec['orders']['old']
        zero = {name: labels[order[0]] for name, order in
                rec['zero_query_orders'].items()}
        one = {name: labels[next(i for i in order if i in survivors)]
               for name, order in rec['zero_query_orders'].items()}
        outcomes.append({'id': key, 'seed': task['seed'],
                         'full_reachable': int(any(labels)),
                         'top100_reachable': int(any(labels[i] for i in old[:100])),
                         'zero': zero, 'one': one})
    return outcomes, checked


def compare(banks, left, right, field):
    diffs = [b[field][left] - b[field][right] for b in banks]
    return {'gain': sum(diffs), 'positive_banks': sum(v > 0 for v in diffs),
            'losing_banks': sum(v < 0 for v in diffs),
            'interval': interval(diffs), 'bank_differences': diffs}


def summarize(outcomes, allocation, checked):
    banks = []
    for seed in SEEDS:
        group = [r for r in outcomes if r['seed'] == seed]
        chosen = set(allocation[str(seed)])
        banks.append({'seed': seed,
                      'full_reachable': sum(r['full_reachable'] for r in group),
                      'top100_reachable': sum(r['top100_reachable'] for r in group),
                      'zero': {name: sum(r['zero'][name] for r in group)
                               for name in NAMES},
                      'one_each': {name: sum(r['one'][name] for r in group)
                                   for name in NAMES},
                      'budgeted': {name: sum(r['one'][name] if r['id'] in chosen
                                              else r['zero'][name] for r in group)
                                   for name in NAMES}})
    totals = {field: {name: sum(b[field][name] for b in banks)
                      for name in NAMES}
              for field in ('zero', 'one_each', 'budgeted')}
    totals['full_reachable'] = sum(b['full_reachable'] for b in banks)
    totals['top100_reachable'] = sum(b['top100_reachable'] for b in banks)
    pairs = (('a_top100', 'e0'), ('a_top100', 'familiar_top50'),
             ('ab_top100', 'a_top100'), ('ab_top100', 'ab_scrambled'))
    contrasts = {f'{a}_minus_{b}': {
        field: compare(banks, a, b, field)
        for field in ('zero', 'one_each', 'budgeted')}
        for a, b in pairs}
    component = contrasts['a_top100_minus_e0']['zero']
    later = contrasts['ab_top100_minus_a_top100']['zero']
    scramble = contrasts['ab_top100_minus_ab_scrambled']['zero']
    gates = {'component': component['gain'] >= 20 and
             component['positive_banks'] >= 12 and component['interval'][0] > 0,
             'incremental_evaluator': later['gain'] >= 5 and
             later['positive_banks'] >= 8 and later['interval'][0] > 0 and
             scramble['gain'] >= 5}
    return {'tasks': len(outcomes), 'calls': len(SEEDS)*4,
            'candidate_labels_checked': checked, 'totals': totals,
            'contrasts': contrasts, 'gates': gates, 'banks': banks}


def verify_manifest(manifest):
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    assert manifest['script_sha256'] == sha(SCRIPT)
    assert manifest['seeds'] == list(SEEDS)
    assert all(manifest['model_sha256'][name] == sha(MODELS / f'{name}.joblib')
               for name in MODEL_NAMES)
    assert manifest['familiar_sha256'] == sha(FAMILIAR / 'top50.joblib')
    assert manifest['source_audit_sha256'] == [sha(p / 'audit.json') for p in SOURCE]
    assert all(manifest['frozen_sha256'][name] == sha(DEST / name)
               for name in manifest['frozen_sha256'])


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    verify_manifest(json.loads((DEST / 'manifest.json').read_text()))
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    wide = json.loads((DEST / 'ast_wide_pools.json').read_text())
    predicted = json.loads((DEST / 'predicted_probe_outputs.json').read_text())
    records = json.loads((DEST / 'frozen_records.json').read_text())
    allocation = json.loads((DEST / 'frozen_allocations.json').read_text())
    outcomes, checked = outcomes_for(tasks, wide, predicted, records)
    summary = summarize(outcomes, allocation, checked)
    write_json(DEST / 'results.json', {'manifest_sha256': sha(DEST / 'manifest.json'),
                                      'summary': summary, 'tasks': outcomes})
    print(json.dumps({k: v for k, v in summary.items() if k != 'banks'}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_manifest(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    assert tasks == normalize(tasks_for())
    base, wide, predicted, records, allocation, forecasts, cost = public_run(tasks)
    records, count = freeze_orders(tasks, wide, records, models_for())
    for name, value in (('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('predicted_probe_outputs.json', predicted),
                        ('frozen_records.json', records),
                        ('frozen_allocations.json', allocation),
                        ('frozen_forecasts.json', forecasts)):
        assert normalize(value) == json.loads((DEST / name).read_text())
    assert count == manifest['candidate_score_count']
    stable_costs = ('base_candidates', 'extra_ast_candidates',
                    'predicted_output_cells', 'e0_candidate_scores',
                    'post_query_candidate_scores')
    assert all(cost[k] == manifest['cost'][k] for k in stable_costs)
    outcomes, checked = outcomes_for(tasks, wide, predicted, records)
    saved = json.loads((DEST / 'results.json').read_text())
    assert saved['manifest_sha256'] == sha(DEST / 'manifest.json')
    assert saved['tasks'] == outcomes
    assert saved['summary'] == summarize(outcomes, allocation, checked)
    result = {'passed': True, 'tasks_rebuilt': len(tasks),
              'predicted_output_cells_rechecked': cost['predicted_output_cells'],
              'target_candidate_labels_rechecked': checked,
              'candidate_scores_rechecked': count}
    write_json(DEST / 'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
