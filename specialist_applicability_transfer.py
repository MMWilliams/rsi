"""Fresh mixed-bank test of a public-evidence specialist applicability rule."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank, shifted_ast_bank
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0, MODELS as TOP20_MODELS
from post_query_feedback_transfer import CHEAP_STATE, normalized
import post_query_feedback_transfer as previous
from specialist_applicability_development import SOURCE, B, panel_rows, public_row
from shifted_survivor_growth_development import rows_for


DEST = ROOT / 'runs/specialist-applicability-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-specialist-applicability-transfer.md'
SPECIALIST = ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918/a_plain100.joblib'
SEEDS = tuple(range(903400, 903424))
PER_BANK = 8
CALLS = 4
NAMES = ('e0', 'specialist', 'effect_conservative', 'effect_zero',
         'visible_route', 'scrambled_route', 'type_oracle')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for():
    tasks = []
    for seed in SEEDS:
        familiar = random_bank(seed, 4, ('ast_transition',), visible=1, hidden=23)
        shifted = shifted_ast_bank(seed + 100000, 4, visible=1, hidden=23)
        for first, second in zip(familiar, shifted):
            tasks.append({**first, 'seed': seed})
            tasks.append({**second, 'seed': seed})
    return tasks


def public_run(tasks):
    old = previous.SEEDS
    previous.SEEDS = SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS = old


def new_regressor():
    return HistGradientBoostingRegressor(
        max_depth=3, max_iter=70, learning_rate=.05,
        min_samples_leaf=16, l2_regularization=5, random_state=27)


def new_classifier():
    return HistGradientBoostingClassifier(
        max_depth=3, max_iter=70, learning_rate=.05,
        min_samples_leaf=16, l2_regularization=5, random_state=27)


def source_models():
    assert all(json.loads((path / 'audit.json').read_text())['passed']
               for path in SOURCE + (B, SPECIALIST.parent))
    e0 = joblib.load(E0)
    specialist = joblib.load(SPECIALIST)
    rows = []
    for path in SOURCE + (B,):
        rows.extend(panel_rows(path, e0, specialist))
    assert len(rows) == 384
    assert sum(r['domain'] == 'familiar' for r in rows) == 192
    assert sum(r['domain'] == 'shifted' for r in rows) == 192
    x_visible = np.asarray([r['visible_features'] for r in rows], np.float32)
    x_effect = np.asarray([r['effect_features'] for r in rows], np.float32)
    domain = np.asarray([r['domain'] == 'shifted' for r in rows], int)
    effect = np.asarray([r['effect'] for r in rows], float)
    rng = np.random.default_rng(14681)
    models = {'visible': new_classifier().fit(x_visible, domain),
              'effect': new_regressor().fit(x_effect, effect),
              'scrambled': new_regressor().fit(x_effect,
                                               effect[rng.permutation(len(effect))])}
    stats = {'source_tasks': len(rows),
             'familiar_tasks': int(sum(domain == 0)),
             'shifted_tasks': int(sum(domain == 1)),
             'effect_positive': int(sum(effect > 0)),
             'effect_negative': int(sum(effect < 0)),
             'effect_zero': int(sum(effect == 0))}
    return models, stats


def freeze_choices(tasks, wide, matrices, records, models):
    e0 = joblib.load(E0)
    specialist = joblib.load(SPECIALIST)
    scored = {'e0_top100_candidate_scores': 0,
              'specialist_candidate_scores': 0}
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide[key]
        public = public_row(task, rec, pool, matrices[key], e0, specialist)
        assert public['choices']['e0'] == rec['choices']['e0']
        x_visible = np.asarray([public['visible_features']], np.float32)
        x_effect = np.asarray([public['effect_features']], np.float32)
        probability = float(models['visible'].predict_proba(x_visible)[0, 1])
        predicted = float(models['effect'].predict(x_effect)[0])
        scrambled = float(models['scrambled'].predict(x_effect)[0])
        base = public['choices']['e0']
        special = public['choices']['specialist']
        rec['router_features'] = public['effect_features']
        rec['router_forecasts'] = {'visible_probability': probability,
                                   'predicted_effect': predicted,
                                   'scrambled_effect': scrambled}
        rec['router_choices'] = {
            'e0': base, 'specialist': special,
            'effect_conservative': special if predicted > .15 else base,
            'effect_zero': special if predicted > 0. else base,
            'visible_route': special if probability >= .5 else base,
            'scrambled_route': special if scrambled > .15 else base,
            'type_oracle': special if task['family'] == 'shifted_ast' else base}
        assert set(rec['router_choices']) == set(NAMES)
        for name in scored:
            scored[name] += public[name]
    return records, scored


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    models, source = source_models()
    tasks = tasks_for()
    assert len(tasks) == len(SEEDS) * PER_BANK
    base, wide, matrices, records, allocations, forecasts, cost = public_run(tasks)
    records, scored = freeze_choices(tasks, wide, matrices, records, models)
    cost.update(scored)
    DEST.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, DEST / f'{name}.joblib', compress=3)
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'base_pools.json', base)
    write_json(DEST / 'ast_wide_pools.json', wide)
    write_json(DEST / 'predicted_probe_outputs.json', matrices)
    write_json(DEST / 'frozen_records.json', records)
    write_json(DEST / 'frozen_allocations.json', allocations)
    write_json(DEST / 'frozen_forecasts.json', forecasts)
    manifest = {'protocol_sha256': sha(PROTOCOL),
                'runner_sha256': sha(ROOT / 'specialist_applicability_transfer.py'),
                'e0_sha256': sha(E0), 'specialist_sha256': sha(SPECIALIST),
                'cheap_state_sha256': sha(CHEAP_STATE),
                'top20_model_sha256': {name: sha(TOP20_MODELS / f'{name}.joblib')
                                       for name in ('plain', 'sensor')},
                'model_file_sha256': {name: sha(DEST / f'{name}.joblib')
                                       for name in models},
                'model_object_hash': {name: joblib.hash(model)
                                      for name, model in models.items()},
                'source': source, 'seeds': SEEDS, 'tasks': len(tasks),
                'calls_per_bank': CALLS, 'cost': cost,
                'frozen_sha256': {name: sha(DEST / name) for name in
                                  ('sealed_bank.json', 'base_pools.json',
                                   'ast_wide_pools.json', 'predicted_probe_outputs.json',
                                   'frozen_records.json', 'frozen_allocations.json',
                                   'frozen_forecasts.json')}}
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'frozen', 'manifest': manifest}, indent=2))


def outcomes_for(tasks, wide, records):
    result = []
    checked = 0
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide[key]
        assert key == rec['id'] and digest(pool) == rec['pool_sha256']
        assert rec['probe_output'] == task['hidden'][rec['probe']][1]
        labels = [int(bool(evaluate_program(item['program'], task['hidden'][8:])))
                  for item in pool]
        checked += len(labels)
        result.append({'id': key, 'seed': task['seed'],
                       'domain': 'shifted' if task['family'] == 'shifted_ast'
                       else 'familiar', 'zero': labels[rec['orders']['e0'][0]],
                       'full_reachable': int(any(labels)),
                       'top100_reachable': int(any(labels[i] for i in
                                                    rec['orders']['old'][:100])),
                       'one': {name: labels[index] for name, index in
                               rec['router_choices'].items()}})
    return result, checked


def comparison(banks, policy, baseline, field):
    diff = [b[field][policy] - b[field][baseline] for b in banks]
    return {'gain': sum(diff), 'positive_banks': sum(x > 0 for x in diff),
            'losing_banks': sum(x < 0 for x in diff),
            'interval': interval(diff), 'bank_differences': diff}


def summarize(outcomes, allocations, checked):
    banks = []
    for seed in SEEDS:
        group = [r for r in outcomes if r['seed'] == seed]
        chosen = set(allocations[str(seed)])
        entry = {'seed': seed, 'zero': sum(r['zero'] for r in group),
                 'full_reachable': sum(r['full_reachable'] for r in group),
                 'top100_reachable': sum(r['top100_reachable'] for r in group),
                 'one_each': {name: sum(r['one'][name] for r in group)
                              for name in NAMES},
                 'budgeted': {name: sum(r['one'][name] if r['id'] in chosen
                                        else r['zero'] for r in group)
                              for name in NAMES}}
        for domain in ('familiar', 'shifted'):
            subset = [r for r in group if r['domain'] == domain]
            entry[domain] = {field: {name: sum(
                r['one'][name] if (field == 'one_each' or r['id'] in chosen)
                else r['zero'] for r in subset) for name in NAMES}
                for field in ('one_each', 'budgeted')}
        banks.append(entry)
    totals = {field: {name: sum(b[field][name] for b in banks)
                      for name in NAMES} for field in ('one_each', 'budgeted')}
    subgroups = {domain: {field: {name: sum(b[domain][field][name] for b in banks)
                                  for name in NAMES}
                          for field in ('one_each', 'budgeted')}
                 for domain in ('familiar', 'shifted')}
    comparisons = {}
    for name in NAMES[1:]:
        comparisons[name] = {field: comparison(banks, name, 'e0', field)
                             for field in ('one_each', 'budgeted')}
    primary = comparisons['effect_conservative']['budgeted']
    versus_specialist = comparison(banks, 'effect_conservative', 'specialist',
                                   'budgeted')
    familiar_diff = [b['familiar']['budgeted']['effect_conservative'] -
                     b['familiar']['budgeted']['e0'] for b in banks]
    shifted_diff = [b['shifted']['budgeted']['effect_conservative'] -
                    b['shifted']['budgeted']['e0'] for b in banks]
    familiar = {'gain': sum(familiar_diff),
                'positive_banks': sum(x > 0 for x in familiar_diff),
                'losing_banks': sum(x < 0 for x in familiar_diff),
                'interval': interval(familiar_diff)}
    shifted = {'gain': sum(shifted_diff),
               'positive_banks': sum(x > 0 for x in shifted_diff),
               'losing_banks': sum(x < 0 for x in shifted_diff),
               'interval': interval(shifted_diff)}
    gate = (primary['gain'] >= 8 and primary['positive_banks'] >= 10 and
            primary['interval'][0] > 0 and
            versus_specialist['gain'] >= 4 and
            versus_specialist['interval'][0] > 0 and
            familiar['gain'] >= 0 and familiar['losing_banks'] <= 1 and
            familiar['interval'][0] >= 0 and shifted['gain'] >= 8 and
            totals['budgeted']['effect_conservative'] >
            totals['budgeted']['scrambled_route'])
    return {'tasks': len(outcomes), 'final_candidate_labels_checked': checked,
            'calls_budgeted': len(SEEDS) * CALLS,
            'calls_one_each': len(outcomes),
            'total_reachable': sum(r['full_reachable'] for r in outcomes),
            'top100_reachable': sum(r['top100_reachable'] for r in outcomes),
            'totals': totals, 'subgroups': subgroups,
            'comparisons': comparisons,
            'primary_vs_specialist': versus_specialist,
            'primary_subgroup_effects': {'familiar': familiar,
                                         'shifted': shifted},
            'integration_gate': gate, 'banks': banks}


def verify_manifest(manifest):
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    assert manifest['runner_sha256'] == sha(ROOT / 'specialist_applicability_transfer.py')
    assert manifest['e0_sha256'] == sha(E0)
    assert manifest['specialist_sha256'] == sha(SPECIALIST)
    assert manifest['cheap_state_sha256'] == sha(CHEAP_STATE)
    assert all(sha(TOP20_MODELS / f'{name}.joblib') == digest
               for name, digest in manifest['top20_model_sha256'].items())
    assert all(sha(DEST / f'{name}.joblib') == digest
               for name, digest in manifest['model_file_sha256'].items())
    assert all(sha(DEST / name) == digest for name, digest in
               manifest['frozen_sha256'].items())


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
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ('banks', 'comparisons')}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_manifest(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    assert tasks == normalized(tasks_for())
    models, source = source_models()
    assert source == manifest['source']
    assert all(joblib.hash(model) == manifest['model_object_hash'][name]
               for name, model in models.items())
    base, wide, matrices, records, allocations, forecasts, cost = public_run(tasks)
    records, scored = freeze_choices(tasks, wide, matrices, records, models)
    cost.update(scored)
    for name, value in (('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('predicted_probe_outputs.json', matrices),
                        ('frozen_records.json', records),
                        ('frozen_allocations.json', allocations),
                        ('frozen_forecasts.json', forecasts)):
        assert normalized(value) == json.loads((DEST / name).read_text())
    for name in ('base_candidates', 'extra_ast_candidates',
                 'predicted_output_cells', 'e0_candidate_scores',
                 'post_query_candidate_scores',
                 'e0_top100_candidate_scores',
                 'specialist_candidate_scores'):
        assert cost[name] == manifest['cost'][name]
    outcomes, checked = outcomes_for(tasks, wide, records)
    saved = json.loads((DEST / 'results.json').read_text())
    assert saved['manifest_sha256'] == sha(DEST / 'manifest.json')
    assert saved['tasks'] == outcomes
    assert saved['summary'] == summarize(outcomes, allocations, checked)
    result = {'passed': True, 'tasks_rebuilt': len(tasks),
              'source_effect_tasks_rechecked': source['source_tasks'],
              'predicted_output_cells_rechecked': cost['predicted_output_cells'],
              'final_candidate_labels_rechecked': checked}
    write_json(DEST / 'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
