"""Frozen fresh-bank test of feedback-conditioned post-query candidate ranking."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import shifted_ast_bank
from gated_ast_feedback import pools_for, BLOCK_AST
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs, rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features as query_features
from cross_family_meta_improver_development import values
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import candidate_features
from candidate_query_cost_transfer import cheap_public_features
from post_query_candidate_development import candidate_rows
from shifted_ast_seed_transfer import selected, route_for_generation


DEST = ROOT / 'runs/post-query-feedback-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-post-query-feedback-transfer.md'
E0 = ROOT / 'runs/candidate-reranker-transfer-20260918/e0.joblib'
MODELS = ROOT / 'analysis/post-query-candidate-models-20260918'
CHEAP_STATE = ROOT / 'runs/candidate-query-cost-transfer-20260918/cost_children.json'
SEEDS = tuple(range(903100, 903124))
PER_BANK = 8
CALLS = 4
NAMES = ('e0', 'plain', 'sensor')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def tasks_for():
    return [{**task, 'seed': seed} for seed in SEEDS
            for task in shifted_ast_bank(seed, PER_BANK, visible=1, hidden=23)]


def public_run(tasks):
    started = time.perf_counter()
    base, wide, times = pools_for(route_for_generation(tasks))
    public = [({'id': t['id'],
                'probe_inputs': [x for x, _ in t['hidden'][:8]]}, wide[t['id']])
              for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted = dict(executor.map(predicted_outputs, public))
    old_model = updated_model()
    e0 = joblib.load(E0)
    models = {name: joblib.load(MODELS / f'{name}.joblib')
              for name in ('plain', 'sensor')}
    cheap = json.loads(CHEAP_STATE.read_text())['children']['cheap_initial']['model']
    records = []
    forecasts = {}
    for task in tasks:
        key = task['id']
        pool = wide[key]
        scores, old_order = rank(task, pool, old_model)
        probe = choose_probe(key, predicted[key], old_order, scores,
                             set(range(len(pool))), [], 'top20_entropy')
        qfeat = query_features(task, {'scores': scores, 'order': old_order,
                                       'first_probe': {'top20_entropy': probe}},
                               predicted[key])
        feat = candidate_features(task, pool, scores, old_order)
        prob = e0.predict_proba(feat)[:, 1]
        e0_head = sorted(range(len(feat)), key=lambda i: (-float(prob[i]), i))
        e0_order = [old_order[i] for i in e0_head] + old_order[len(feat):]
        rec = {'id': key, 'seed': task['seed'], 'public_block': BLOCK_AST,
               'old_scores': scores,
               'orders': {'old': old_order, 'e0': e0_order},
               'probe': probe, 'probe_output': task['hidden'][probe][1],
               'pool_sha256': digest(pool), 'query_features': qfeat.tolist()}
        rec['cheap_features'] = cheap_public_features(rec, predicted[key])
        candidates, surviving = candidate_rows(task, pool, rec, predicted[key], e0)
        choice = {'e0': next(i for i in e0_order if i in surviving)}
        for name, model in models.items():
            if not candidates:
                choice[name] = choice['e0']
                continue
            x = np.asarray([row[1 if name == 'plain' else 2]
                            for row in candidates], np.float32)
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(candidates)), key=lambda j: (float(p[j]), -j))
            choice[name] = candidates[pick][0]
        assert all(i in surviving for i in choice.values())
        rec['choices'] = choice
        rec['top20_survivors'] = len(candidates)
        records.append(rec)
    allocations = {}
    for seed in SEEDS:
        group = [r for r in records if r['seed'] == seed]
        rows = [{'id': r['id'], 'public_block': BLOCK_AST,
                 'features': r['cheap_features']} for r in group]
        score = values(cheap, rows)
        allocations[str(seed)] = selected(group, score, CALLS)
        forecasts[str(seed)] = {r['id']: float(v) for r, v in zip(group, score)}
        assert len(allocations[str(seed)]) == CALLS
    cost = {'base_candidates': sum(map(len, base.values())),
            'extra_ast_candidates': sum(len(wide[k]) - len(base[k]) for k in base),
            'predicted_output_cells': sum(len(wide[t['id']]) * 8 for t in tasks),
            'e0_candidate_scores': len(tasks) * 20,
            'post_query_candidate_scores': sum(r['top20_survivors'] for r in records) * 2,
            'generation_seconds': sum(times.values()),
            'public_preparation_wall_seconds': time.perf_counter() - started}
    return base, wide, predicted, records, allocations, forecasts, cost


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    for parent in (E0.parent, CHEAP_STATE.parent):
        assert json.loads((parent / 'audit.json').read_text())['passed']
    tasks = tasks_for()
    assert len(tasks) == len(SEEDS) * PER_BANK
    base, wide, predicted, records, allocations, forecasts, cost = public_run(tasks)
    DEST.mkdir(parents=True)
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'base_pools.json', base)
    write_json(DEST / 'ast_wide_pools.json', wide)
    write_json(DEST / 'predicted_probe_outputs.json', predicted)
    write_json(DEST / 'frozen_records.json', records)
    write_json(DEST / 'frozen_allocations.json', allocations)
    write_json(DEST / 'frozen_forecasts.json', forecasts)
    manifest = {'protocol_sha256': sha(PROTOCOL),
                'runner_sha256': sha(ROOT / 'post_query_feedback_transfer.py'),
                'e0_sha256': sha(E0),
                'model_sha256': {n: sha(MODELS / f'{n}.joblib') for n in ('plain', 'sensor')},
                'cheap_state_sha256': sha(CHEAP_STATE),
                'seeds': SEEDS, 'tasks': len(tasks), 'calls_per_bank': CALLS,
                'source_candidate_labels': 8681, 'cost': cost,
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
        assert rec['id'] == key and rec['pool_sha256'] == digest(pool)
        assert rec['probe_output'] == task['hidden'][rec['probe']][1]
        labels = [int(bool(evaluate_program(row['program'], task['hidden'][8:])))
                  for row in pool]
        checked += len(labels)
        old = rec['orders']['old']
        outcome.append({'id': key, 'seed': task['seed'],
                        'full_reachable': int(any(labels)),
                        'top20_reachable': int(any(labels[i] for i in old[:20])),
                        'zero': labels[rec['orders']['e0'][0]],
                        'one': {n: labels[rec['choices'][n]] for n in NAMES}})
    return outcome, checked


def summarize(outcome, allocations, checked):
    banks = []
    for seed in SEEDS:
        group = [r for r in outcome if r['seed'] == seed]
        chosen = set(allocations[str(seed)])
        banks.append({'seed': seed,
                      'full_reachable': sum(r['full_reachable'] for r in group),
                      'top20_reachable': sum(r['top20_reachable'] for r in group),
                      'zero': sum(r['zero'] for r in group),
                      'one_each': {n: sum(r['one'][n] for r in group) for n in NAMES},
                      'budgeted': {n: sum(r['one'][n] if r['id'] in chosen else r['zero']
                                          for r in group) for n in NAMES}})
    totals = {'full_reachable': sum(b['full_reachable'] for b in banks),
              'top20_reachable': sum(b['top20_reachable'] for b in banks),
              'zero': sum(b['zero'] for b in banks)}
    for field in ('one_each', 'budgeted'):
        totals[field] = {n: sum(b[field][n] for b in banks) for n in NAMES}
    comparisons = {}
    for field in ('one_each', 'budgeted'):
        comparisons[field] = {}
        for baseline in ('e0', 'plain'):
            diffs = [b[field]['sensor'] - b[field][baseline] for b in banks]
            comparisons[field][baseline] = {
                'gain': sum(diffs), 'positive_banks': sum(v > 0 for v in diffs),
                'losing_banks': sum(v < 0 for v in diffs),
                'interval': interval(diffs), 'bank_differences': diffs}
    first = comparisons['one_each']['e0']
    extra = comparisons['one_each']['plain']
    gate = (first['gain'] >= 6 and first['positive_banks'] >= 16
            and first['interval'][0] > 0)
    sensor_gate = gate and extra['interval'][0] > 0
    budget = comparisons['budgeted']['e0']
    integrated_gate = gate and budget['gain'] > 0 and budget['interval'][0] > 0
    return {'tasks': len(outcome), 'final_candidate_labels_checked': checked,
            'calls_one_each': len(outcome), 'calls_budgeted': len(SEEDS) * CALLS,
            'totals': totals, 'comparisons': comparisons,
            'post_query_evaluator_gate': gate,
            'sensor_feature_gate': sensor_gate,
            'integrated_seed_gate': integrated_gate, 'banks': banks}


def verify_frozen(manifest):
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    assert manifest['runner_sha256'] == sha(ROOT / 'post_query_feedback_transfer.py')
    assert manifest['e0_sha256'] == sha(E0)
    assert manifest['cheap_state_sha256'] == sha(CHEAP_STATE)
    assert all(sha(MODELS / f'{name}.joblib') == value
               for name, value in manifest['model_sha256'].items())
    assert all(sha(DEST / name) == value for name, value in manifest['frozen_sha256'].items())


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_frozen(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    wide = json.loads((DEST / 'ast_wide_pools.json').read_text())
    records = json.loads((DEST / 'frozen_records.json').read_text())
    allocations = json.loads((DEST / 'frozen_allocations.json').read_text())
    outcome, checked = outcomes_for(tasks, wide, records)
    summary = summarize(outcome, allocations, checked)
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcome,
                                      'manifest_sha256': sha(DEST / 'manifest.json')})
    print(json.dumps({k: v for k, v in summary.items() if k != 'banks'}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_frozen(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    assert tasks == normalized(tasks_for())
    base, wide, predicted, records, allocations, forecasts, cost = public_run(tasks)
    assert normalized(base) == json.loads((DEST / 'base_pools.json').read_text())
    assert normalized(wide) == json.loads((DEST / 'ast_wide_pools.json').read_text())
    assert normalized(predicted) == json.loads((DEST / 'predicted_probe_outputs.json').read_text())
    assert normalized(records) == json.loads((DEST / 'frozen_records.json').read_text())
    assert normalized(allocations) == json.loads((DEST / 'frozen_allocations.json').read_text())
    assert normalized(forecasts) == json.loads((DEST / 'frozen_forecasts.json').read_text())
    for name in ('base_candidates', 'extra_ast_candidates', 'predicted_output_cells',
                 'e0_candidate_scores', 'post_query_candidate_scores'):
        assert cost[name] == manifest['cost'][name]
    outcome, checked = outcomes_for(tasks, wide, records)
    saved = json.loads((DEST / 'results.json').read_text())
    assert saved['manifest_sha256'] == sha(DEST / 'manifest.json')
    assert saved['tasks'] == outcome
    assert saved['summary'] == summarize(outcome, allocations, checked)
    report = {'passed': True, 'tasks_rebuilt': len(tasks),
              'predicted_output_cells_rechecked': cost['predicted_output_cells'],
              'post_query_candidate_scores_rechecked': cost['post_query_candidate_scores'],
              'final_candidate_labels_rechecked': checked}
    write_json(DEST / 'audit.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
