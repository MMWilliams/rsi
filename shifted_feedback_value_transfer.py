"""Fresh shifted-AST transfer of feedback-updated query value and joint actions."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import shifted_ast_bank
from gated_ast_feedback import BLOCK_AST
from cross_family_meta_improver_development import fit_method, values
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0
import post_query_feedback_transfer as prior_transfer
from post_query_feedback_transfer import normalized
from wide_post_query_development import MODELS, rows_for
from joint_survivor_query_development import ACTIONS, SOURCE, panel_rows, model_rows


DEST = ROOT / 'runs/shifted-feedback-value-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-shifted-feedback-value-transfer.md'
SHIFTED_SOURCE = ROOT / 'runs/shifted-ast-seed-transfer-20260918'
SEEDS = tuple(range(903200, 903224))
PER_BANK = 8
CALLS = 4
E0_POLICIES = ('cheap', 'prior', 'pooled12', 'shifted100',
               'scrambled', 'duplicate', 'hash_four')
ROUTE_POLICIES = ('route_pooled12', 'route_shifted100')
POLICIES = E0_POLICIES + ROUTE_POLICIES


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for():
    return [{**task, 'seed': seed} for seed in SEEDS
            for task in shifted_ast_bank(seed, PER_BANK, visible=1, hidden=23)]


def public_run_new(tasks):
    """Reuse the frozen public builder with this experiment's bank IDs."""
    previous = prior_transfer.SEEDS
    prior_transfer.SEEDS = SEEDS
    try:
        return prior_transfer.public_run(tasks)
    finally:
        prior_transfer.SEEDS = previous


def source_models():
    e0 = joblib.load(E0)
    candidates = {name: joblib.load(MODELS / f'{name}.joblib')
                  for name in ('plain', 'sensor')}
    prior = []
    checked = 0
    for path in SOURCE:
        rows, count = panel_rows(path, e0, candidates)
        prior += rows
        checked += count
    shifted, shift_count = panel_rows(SHIFTED_SOURCE, e0, candidates)
    checked += shift_count
    assert len(prior) == 1152 and len(shifted) == 96
    rng = np.random.default_rng(17039)
    permutations = {name: rng.permutation(len(shifted)) for name in ACTIONS}
    scrambled = [{**row, 'gain': {name: shifted[int(permutations[name][i])]
                                  ['gain'][name] for name in ACTIONS}}
                 for i, row in enumerate(shifted)]
    configs = {'prior': (prior, 'interaction_100'),
               'pooled12': (prior + shifted * 12, 'interaction_100'),
               'shifted100': (shifted, 'basic_100'),
               'scrambled': (prior + scrambled * 12, 'interaction_100'),
               'duplicate': (prior + prior[:96] * 12, 'interaction_100')}
    models = {policy: {action: fit_method(model_rows(source, action), rule)
                       for action in ACTIONS}
              for policy, (source, rule) in configs.items()}
    return models, checked


def decisions(tasks, wide, matrices, records, cheap_allocations, models):
    e0 = joblib.load(E0)
    candidates = {name: joblib.load(MODELS / f'{name}.joblib')
                  for name in ('plain', 'sensor')}
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide[key]
        rows, surviving = rows_for(task, pool, rec, matrices[key], e0)
        choice = {'e0': next(i for i in rec['orders']['e0'] if i in surviving)}
        assert choice['e0'] == rec['choices']['e0']
        for name, model in candidates.items():
            if not rows:
                choice[name] = choice['e0']
                continue
            x = np.asarray([row[1 if name == 'plain' else 2]
                            for row in rows], np.float32)
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(rows)), key=lambda j: (float(p[j]), -j))
            choice[name] = rows[pick][0]
        rec['wide_choices'] = choice
        rec['wide_survivor_scores'] = len(rows) * len(candidates)
    public_rows = [{'id': r['id'], 'seed': r['seed'],
                    'public_block': BLOCK_AST, 'features': r['cheap_features']}
                   for r in records]
    forecasts = {policy: {action: {
        row['id']: float(v) for row, v in zip(public_rows,
            values(action_model, public_rows))}
        for action, action_model in action_models.items()}
        for policy, action_models in models.items()}
    allocations = {}
    for seed in SEEDS:
        group = [r for r in records if r['seed'] == seed]
        choice = {'cheap': cheap_allocations[str(seed)]}
        for policy in ('prior', 'pooled12', 'shifted100', 'scrambled', 'duplicate'):
            ranking = sorted(group, key=lambda r:
                (forecasts[policy]['e0'][r['id']], r['id']), reverse=True)
            choice[policy] = sorted(r['id'] for r in ranking[:CALLS])
        choice['hash_four'] = sorted(r['id'] for r in sorted(group, key=lambda r:
            hashlib.sha256((r['id'] + ':feedback-four').encode()).digest())[:CALLS])
        for source in ('pooled12', 'shifted100'):
            ranking = sorted(group, key=lambda r:
                (max(forecasts[source][action][r['id']] for action in ACTIONS),
                 r['id']), reverse=True)
            choice['route_' + source] = sorted(r['id'] for r in ranking[:CALLS])
        assert all(len(ids) == CALLS for ids in choice.values())
        allocations[str(seed)] = choice
    return records, forecasts, allocations


def route_action(policy, key, forecasts):
    if policy in E0_POLICIES:
        return 'e0'
    source = policy.removeprefix('route_')
    return max(ACTIONS, key=lambda action:
               (forecasts[source][action][key], -ACTIONS.index(action)))


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    assert all(json.loads((path / 'audit.json').read_text())['passed']
               for path in SOURCE + (SHIFTED_SOURCE,))
    models, source_choices = source_models()
    tasks = tasks_for()
    assert len(tasks) == 192
    base, wide, predicted, records, cheap, cheap_forecast, cost = public_run_new(tasks)
    records, forecasts, allocations = decisions(
        tasks, wide, predicted, records, cheap, models)
    cost['wide_post_query_candidate_scores'] = sum(
        r['wide_survivor_scores'] for r in records)
    DEST.mkdir(parents=True)
    write_json(DEST / 'query_models.json', models)
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'base_pools.json', base)
    write_json(DEST / 'ast_wide_pools.json', wide)
    write_json(DEST / 'predicted_probe_outputs.json', predicted)
    write_json(DEST / 'frozen_records.json', records)
    write_json(DEST / 'frozen_forecasts.json', forecasts)
    write_json(DEST / 'frozen_allocations.json', allocations)
    manifest = {'protocol_sha256': sha(PROTOCOL),
                'runner_sha256': sha(ROOT / 'shifted_feedback_value_transfer.py'),
                'e0_sha256': sha(E0),
                'candidate_model_sha256': {name: sha(MODELS / f'{name}.joblib')
                                            for name in ('plain', 'sensor')},
                'seeds': SEEDS, 'tasks': len(tasks), 'calls_per_bank': CALLS,
                'familiar_query_source_tasks': 1152,
                'shifted_feedback_source_tasks': 96,
                'source_candidate_choices_checked': source_choices,
                'cost': cost,
                'frozen_sha256': {name: sha(DEST / name) for name in
                                  ('query_models.json', 'sealed_bank.json',
                                   'base_pools.json', 'ast_wide_pools.json',
                                   'predicted_probe_outputs.json',
                                   'frozen_records.json', 'frozen_forecasts.json',
                                   'frozen_allocations.json')}}
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
                       'full_reachable': int(any(labels)),
                       'top20_reachable': int(any(labels[i] for i in
                                                  rec['orders']['old'][:20])),
                       'zero': labels[rec['orders']['e0'][0]],
                       'one': {name: labels[index] for name, index in
                               rec['wide_choices'].items()}})
    return result, checked


def summarize(outcomes, allocations, forecasts, checked):
    banks = []
    for seed in SEEDS:
        group = [r for r in outcomes if r['seed'] == seed]
        entry = {'seed': seed, 'zero': sum(r['zero'] for r in group),
                 'full_reachable': sum(r['full_reachable'] for r in group),
                 'top20_reachable': sum(r['top20_reachable'] for r in group)}
        for policy in POLICIES:
            chosen = set(allocations[str(seed)][policy])
            entry[policy] = sum(
                r['one'][route_action(policy, r['id'], forecasts)]
                if r['id'] in chosen else r['zero'] for r in group)
        entry['one_e0'] = sum(r['one']['e0'] for r in group)
        entry['one_sensor'] = sum(r['one']['sensor'] for r in group)
        entry['hindsight_e0'] = entry['zero'] + sum(sorted(
            (r['one']['e0'] - r['zero'] for r in group), reverse=True)[:CALLS])
        entry['hindsight_menu'] = entry['zero'] + sum(sorted(
            (max(r['one'].values()) - r['zero'] for r in group),
            reverse=True)[:CALLS])
        banks.append(entry)
    totals = {name: sum(b[name] for b in banks) for name in
              ('zero', 'full_reachable', 'top20_reachable', 'one_e0',
               'one_sensor', 'hindsight_e0', 'hindsight_menu') + POLICIES}
    comparisons = {}
    for policy in POLICIES:
        if policy == 'cheap':
            continue
        diffs = [b[policy] - b['cheap'] for b in banks]
        comparisons[policy] = {'gain_vs_cheap': sum(diffs),
                               'positive_banks': sum(x > 0 for x in diffs),
                               'losing_banks': sum(x < 0 for x in diffs),
                               'interval': interval(diffs),
                               'bank_differences': diffs}
    primary = comparisons['pooled12']
    ctrl = [sum(b['pooled12'] - b[c] for b in banks)
            for c in ('scrambled', 'duplicate')]
    control_intervals = [interval([b['pooled12'] - b[c] for b in banks])
                         for c in ('scrambled', 'duplicate')]
    evaluator_gate = (primary['gain_vs_cheap'] >= 6 and
                      primary['positive_banks'] >= 8 and
                      primary['interval'][0] > 0 and
                      all(x > 0 for x in ctrl) and
                      all(bounds[0] > 0 for bounds in control_intervals))
    strongest_e0 = max(totals[name] for name in E0_POLICIES)
    route = comparisons['route_pooled12']
    best_e0_policy = max(E0_POLICIES, key=lambda name: totals[name])
    route_diffs = [b['route_pooled12'] - b[best_e0_policy] for b in banks]
    joint_gate = (totals['route_pooled12'] - strongest_e0 >= 6 and
                  sum(x > 0 for x in route_diffs) >= 8 and
                  interval(route_diffs)[0] > 0)
    return {'tasks': len(outcomes), 'final_candidate_labels_checked': checked,
            'calls_per_four_call_policy': len(SEEDS) * CALLS,
            'calls_one_each': len(outcomes), 'totals': totals,
            'comparisons': comparisons,
            'pooled_vs_controls': {'scrambled': {'gain': ctrl[0],
                'interval': control_intervals[0]},
                'duplicate': {'gain': ctrl[1], 'interval': control_intervals[1]}},
            'strongest_e0_policy': best_e0_policy,
            'route_vs_strongest_e0': {'gain': totals['route_pooled12'] - strongest_e0,
                'positive_banks': sum(x > 0 for x in route_diffs),
                'interval': interval(route_diffs)},
            'evaluator_gate': evaluator_gate, 'joint_gate': joint_gate,
            'banks': banks}


def verify_manifest(manifest):
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    assert manifest['runner_sha256'] == sha(ROOT / 'shifted_feedback_value_transfer.py')
    assert manifest['e0_sha256'] == sha(E0)
    assert all(manifest['candidate_model_sha256'][name] ==
               sha(MODELS / f'{name}.joblib') for name in ('plain', 'sensor'))
    assert all(sha(DEST / name) == value for name, value in
               manifest['frozen_sha256'].items())


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_manifest(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    wide = json.loads((DEST / 'ast_wide_pools.json').read_text())
    records = json.loads((DEST / 'frozen_records.json').read_text())
    forecasts = json.loads((DEST / 'frozen_forecasts.json').read_text())
    allocations = json.loads((DEST / 'frozen_allocations.json').read_text())
    outcomes, checked = outcomes_for(tasks, wide, records)
    summary = summarize(outcomes, allocations, forecasts, checked)
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes,
                                      'manifest_sha256': sha(DEST / 'manifest.json')})
    print(json.dumps({k: v for k, v in summary.items() if k != 'banks'}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    verify_manifest(manifest)
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    assert tasks == normalized(tasks_for())
    models, checked_source = source_models()
    assert normalized(models) == json.loads((DEST / 'query_models.json').read_text())
    assert checked_source == manifest['source_candidate_choices_checked']
    base, wide, predicted, records, cheap, cheap_forecast, cost = public_run_new(tasks)
    records, forecasts, allocations = decisions(
        tasks, wide, predicted, records, cheap, models)
    cost['wide_post_query_candidate_scores'] = sum(
        r['wide_survivor_scores'] for r in records)
    for name, value in (('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('predicted_probe_outputs.json', predicted),
                        ('frozen_records.json', records),
                        ('frozen_forecasts.json', forecasts),
                        ('frozen_allocations.json', allocations)):
        assert normalized(value) == json.loads((DEST / name).read_text())
    for name in ('base_candidates', 'extra_ast_candidates',
                 'predicted_output_cells', 'e0_candidate_scores',
                 'post_query_candidate_scores', 'wide_post_query_candidate_scores'):
        assert cost[name] == manifest['cost'][name]
    outcomes, checked = outcomes_for(tasks, wide, records)
    saved = json.loads((DEST / 'results.json').read_text())
    assert saved['manifest_sha256'] == sha(DEST / 'manifest.json')
    assert saved['tasks'] == outcomes
    assert saved['summary'] == summarize(outcomes, allocations, forecasts, checked)
    result = {'passed': True, 'tasks_rebuilt': len(tasks),
              'source_choices_rechecked': checked_source,
              'predicted_output_cells_rechecked': cost['predicted_output_cells'],
              'final_candidate_labels_rechecked': checked}
    write_json(DEST / 'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
