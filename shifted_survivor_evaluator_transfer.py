"""Fresh transfer of top-100 feedback-trained candidate evaluator checkpoints."""
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
from post_query_candidate_development import E0, MODELS as TOP20_MODELS
import post_query_feedback_transfer as previous
from shifted_survivor_growth_development import (A, B, source_arrays,
                                                  rows_for)
from wide_post_query_development import MODELS as FAMILIAR_MODELS
from candidate_reranker_transfer import model_for


DEST = ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-shifted-survivor-evaluator-transfer.md'
SEEDS = tuple(range(903300, 903324))
PER_BANK = 8
CALLS = 4
NAMES = ('e0', 'familiar_plain50', 'a_plain100', 'ab_plain100',
         'ab_scrambled100', 'ab_duplicate100', 'ab_sensor100')
TRAINED = NAMES[2:]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for():
    return [{**task, 'seed': seed} for seed in SEEDS
            for task in shifted_ast_bank(seed, PER_BANK, visible=1, hidden=23)]


def public_run(tasks):
    previous_seeds = previous.SEEDS
    previous.SEEDS = SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS = previous_seeds


def train_models():
    assert all(json.loads((path / 'audit.json').read_text())['passed']
               for path in (A, B))
    e0 = joblib.load(E0)
    a = source_arrays(A, e0)
    b = source_arrays(B, e0)
    assert a['tasks'] == 96 and b['tasks'] == 192
    plain = np.r_[a['plain'], b['plain']]
    sensor = np.r_[a['sensor'], b['sensor']]
    label = np.r_[a['labels'], b['labels']]
    shuffled = b['labels'].copy()
    rng = np.random.default_rng(138731)
    for group in b['groups']:
        if len(group) > 1:
            shuffled[group] = rng.permutation(shuffled[group])
    controls = np.r_[a['labels'], shuffled]
    models = {
        'a_plain100': model_for(15).fit(a['plain'], a['labels']),
        'ab_plain100': model_for(15).fit(plain, label),
        'ab_scrambled100': model_for(15).fit(plain, controls),
        'ab_duplicate100': model_for(15).fit(np.tile(a['plain'], (3, 1)),
                                               np.tile(a['labels'], 3)),
        'ab_sensor100': model_for(15).fit(sensor, label)}
    stats = {'source_a_tasks': 96, 'source_b_tasks': 192,
             'source_a_survivor_labels': len(a['labels']),
             'source_ab_survivor_labels': len(label),
             'source_ab_positive_labels': int(label.sum()),
             'duplicate_nominal_rows': len(a['labels']) * 3}
    return models, stats


def freeze_choices(tasks, wide, matrices, records, models):
    e0 = joblib.load(E0)
    familiar = joblib.load(FAMILIAR_MODELS / 'plain.joblib')
    score_count = {name: 0 for name in NAMES[1:]}
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide[key]
        rows, surviving = rows_for(task, pool, rec, matrices[key], e0)
        choice = {'e0': next(i for i in rec['orders']['e0'] if i in surviving)}
        assert choice['e0'] == rec['choices']['e0']
        for name in NAMES[1:]:
            model = familiar if name == 'familiar_plain50' else models[name]
            sub = ([row for row in rows if row['old_rank'] < 50]
                   if name == 'familiar_plain50' else rows)
            if not sub:
                choice[name] = choice['e0']
                continue
            field = 'sensor' if name == 'ab_sensor100' else 'plain'
            x = np.asarray([row[field] for row in sub], np.float32)
            p = model.predict_proba(x)[:, 1]
            score_count[name] += len(sub)
            pick = max(range(len(sub)), key=lambda i: (float(p[i]), -i))
            choice[name] = sub[pick]['index']
        assert all(index in surviving for index in choice.values())
        rec['top100_choices'] = choice
        rec['top100_survivors'] = len(rows)
    return records, score_count


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    models, stats = train_models()
    tasks = tasks_for()
    assert len(tasks) == 192
    base, wide, predicted, records, allocations, forecasts, cost = public_run(tasks)
    records, scores = freeze_choices(tasks, wide, predicted, records, models)
    DEST.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, DEST / f'{name}.joblib', compress=3)
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'base_pools.json', base)
    write_json(DEST / 'ast_wide_pools.json', wide)
    write_json(DEST / 'predicted_probe_outputs.json', predicted)
    write_json(DEST / 'frozen_records.json', records)
    write_json(DEST / 'frozen_allocations.json', allocations)
    write_json(DEST / 'frozen_forecasts.json', forecasts)
    cost['top100_survivor_rows'] = sum(r['top100_survivors'] for r in records)
    cost['top100_model_scores'] = scores
    manifest = {'protocol_sha256': sha(PROTOCOL),
                'runner_sha256': sha(ROOT / 'shifted_survivor_evaluator_transfer.py'),
                'e0_sha256': sha(E0),
                'familiar_plain_sha256': sha(FAMILIAR_MODELS / 'plain.joblib'),
                'top20_model_sha256': {name: sha(TOP20_MODELS / f'{name}.joblib')
                                       for name in ('plain', 'sensor')},
                'model_file_sha256': {name: sha(DEST / f'{name}.joblib')
                                       for name in TRAINED},
                'model_object_hash': {name: joblib.hash(model)
                                      for name, model in models.items()},
                'seeds': SEEDS, 'tasks': len(tasks), 'calls_per_bank': CALLS,
                'source': stats, 'cost': cost,
                'frozen_sha256': {name: sha(DEST / name) for name in
                                  ('sealed_bank.json', 'base_pools.json',
                                   'ast_wide_pools.json', 'predicted_probe_outputs.json',
                                   'frozen_records.json', 'frozen_allocations.json',
                                   'frozen_forecasts.json')}}
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'frozen', 'manifest': manifest}, indent=2))


def outcomes_for(tasks, wide, records):
    outcome = []
    checked = 0
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide[key]
        assert key == rec['id'] and digest(pool) == rec['pool_sha256']
        assert rec['probe_output'] == task['hidden'][rec['probe']][1]
        labels = [int(bool(evaluate_program(item['program'], task['hidden'][8:])))
                  for item in pool]
        checked += len(labels)
        old = rec['orders']['old']
        outcome.append({'id': key, 'seed': task['seed'],
                        'full_reachable': int(any(labels)),
                        'top20_reachable': int(any(labels[i] for i in old[:20])),
                        'top50_reachable': int(any(labels[i] for i in old[:50])),
                        'top100_reachable': int(any(labels[i] for i in old[:100])),
                        'zero': labels[rec['orders']['e0'][0]],
                        'one': {name: labels[index] for name, index in
                                rec['top100_choices'].items()}})
    return outcome, checked


def compare(banks, newer, older, field):
    diffs = [b[field][newer] - b[field][older] for b in banks]
    return {'gain': sum(diffs), 'positive_banks': sum(v > 0 for v in diffs),
            'losing_banks': sum(v < 0 for v in diffs),
            'interval': interval(diffs), 'bank_differences': diffs}


def summarize(outcomes, allocations, checked):
    banks = []
    for seed in SEEDS:
        group = [r for r in outcomes if r['seed'] == seed]
        chosen = set(allocations[str(seed)])
        banks.append({'seed': seed, 'zero': sum(r['zero'] for r in group),
                      'full_reachable': sum(r['full_reachable'] for r in group),
                      'top20_reachable': sum(r['top20_reachable'] for r in group),
                      'top50_reachable': sum(r['top50_reachable'] for r in group),
                      'top100_reachable': sum(r['top100_reachable'] for r in group),
                      'one_each': {name: sum(r['one'][name] for r in group)
                                   for name in NAMES},
                      'budgeted': {name: sum(r['one'][name] if r['id'] in chosen
                                             else r['zero'] for r in group)
                                   for name in NAMES}})
    totals = {name: sum(b[name] for b in banks) for name in
              ('zero', 'full_reachable', 'top20_reachable',
               'top50_reachable', 'top100_reachable')}
    for field in ('one_each', 'budgeted'):
        totals[field] = {name: sum(b[field][name] for b in banks)
                         for name in NAMES}
    comparisons = {}
    pairs = (('a_plain100', 'e0'), ('a_plain100', 'familiar_plain50'),
             ('ab_plain100', 'a_plain100'),
             ('ab_plain100', 'ab_scrambled100'),
             ('ab_plain100', 'ab_duplicate100'),
             ('ab_sensor100', 'ab_plain100'))
    for newer, older in pairs:
        comparisons[f'{newer}_minus_{older}'] = {
            field: compare(banks, newer, older, field)
            for field in ('one_each', 'budgeted')}
    first = [comparisons[f'a_plain100_minus_{name}']['budgeted']
             for name in ('e0', 'familiar_plain50')]
    component_gate = all(c['gain'] >= 10 and c['positive_banks'] >= 12
                         and c['interval'][0] > 0 for c in first)
    extras = [comparisons[f'ab_plain100_minus_{name}']['budgeted']
              for name in ('a_plain100', 'ab_scrambled100', 'ab_duplicate100')]
    incremental_gate = (extras[0]['gain'] >= 4 and
                        extras[0]['positive_banks'] >= 8 and
                        all(c['interval'][0] > 0 for c in extras))
    sensor = comparisons['ab_sensor100_minus_ab_plain100']['budgeted']
    sensor_gate = sensor['gain'] > 0 and sensor['interval'][0] > 0
    return {'tasks': len(outcomes), 'final_candidate_labels_checked': checked,
            'calls_budgeted': len(SEEDS) * CALLS,
            'calls_one_each': len(outcomes), 'totals': totals,
            'comparisons': comparisons,
            'component_gate': component_gate,
            'incremental_feedback_gate': incremental_gate,
            'sensor_feature_gate': sensor_gate, 'banks': banks}


def verify_manifest(manifest):
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    assert manifest['runner_sha256'] == sha(ROOT / 'shifted_survivor_evaluator_transfer.py')
    assert manifest['e0_sha256'] == sha(E0)
    assert manifest['familiar_plain_sha256'] == sha(FAMILIAR_MODELS / 'plain.joblib')
    assert all(sha(TOP20_MODELS / f'{name}.joblib') == digest
               for name, digest in manifest['top20_model_sha256'].items())
    assert all(sha(DEST / f'{name}.joblib') == digest
               for name, digest in manifest['model_file_sha256'].items())
    assert all(sha(DEST / name) == digest
               for name, digest in manifest['frozen_sha256'].items())


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_manifest(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    wide = json.loads((DEST / 'ast_wide_pools.json').read_text())
    records = json.loads((DEST / 'frozen_records.json').read_text())
    allocations = json.loads((DEST / 'frozen_allocations.json').read_text())
    outcomes, checked = outcomes_for(tasks, wide, records)
    summary = summarize(outcomes, allocations, checked)
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes,
                                      'manifest_sha256': sha(DEST / 'manifest.json')})
    print(json.dumps({k: v for k, v in summary.items() if k != 'banks'}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_manifest(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    assert tasks == previous.normalized(tasks_for())
    models, stats = train_models()
    assert stats == manifest['source']
    assert all(joblib.hash(model) == manifest['model_object_hash'][name]
               for name, model in models.items())
    base, wide, predicted, records, allocations, forecasts, cost = public_run(tasks)
    records, scores = freeze_choices(tasks, wide, predicted, records, models)
    cost['top100_survivor_rows'] = sum(r['top100_survivors'] for r in records)
    cost['top100_model_scores'] = scores
    for name, value in (('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('predicted_probe_outputs.json', predicted),
                        ('frozen_records.json', records),
                        ('frozen_allocations.json', allocations),
                        ('frozen_forecasts.json', forecasts)):
        assert previous.normalized(value) == json.loads((DEST / name).read_text())
    for name in ('base_candidates', 'extra_ast_candidates',
                 'predicted_output_cells', 'e0_candidate_scores',
                 'post_query_candidate_scores', 'top100_survivor_rows'):
        assert cost[name] == manifest['cost'][name]
    assert cost['top100_model_scores'] == manifest['cost']['top100_model_scores']
    outcomes, checked = outcomes_for(tasks, wide, records)
    saved = json.loads((DEST / 'results.json').read_text())
    assert saved['manifest_sha256'] == sha(DEST / 'manifest.json')
    assert saved['tasks'] == outcomes
    assert saved['summary'] == summarize(outcomes, allocations, checked)
    result = {'passed': True, 'tasks_rebuilt': len(tasks),
              'source_survivor_labels_rechecked': stats['source_ab_survivor_labels'],
              'predicted_output_cells_rechecked': cost['predicted_output_cells'],
              'target_candidate_labels_rechecked': checked}
    write_json(DEST / 'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
