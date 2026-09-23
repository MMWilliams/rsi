"""Opened-bank matched-call screen of post-query evaluator edits plus call placement."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import public_block
from candidate_query_cost_transfer import cheap_public_features
from cross_family_meta_improver_development import fit_method, values
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0, load_panel
from wide_post_query_development import MODELS, rows_for


SOURCE = (ROOT / 'runs/candidate-conditioned-query-transfer-20260918',
          ROOT / 'runs/candidate-query-cost-transfer-20260918')
TARGET = (ROOT / 'runs/shifted-ast-seed-transfer-20260918',
          ROOT / 'runs/post-query-feedback-transfer-20260918',
          ROOT / 'runs/combined-ranker-query-transfer-20260918')
OUT = ROOT / 'analysis/joint-survivor-query-development-20260918.json'
ACTIONS = ('e0', 'plain', 'sensor')


def panel_rows(path, e0, models):
    tasks, base, wide, matrices, records = load_panel(path)
    result = []
    checked = 0
    for task, rec in zip(tasks, records):
        key = task['id']
        pool = wide.get(key, base[key])
        matrix = matrices[key]
        candidates, survivor = rows_for(task, pool, rec, matrix, e0)
        choices = {'e0': next(i for i in rec['orders']['e0'] if i in survivor)}
        for name, model in models.items():
            if not candidates:
                choices[name] = choices['e0']
                continue
            x = np.asarray([row[1 if name == 'plain' else 2]
                            for row in candidates], np.float32)
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(candidates)), key=lambda j: (float(p[j]), -j))
            choices[name] = candidates[pick][0]
        zero = int(bool(evaluate_program(
            pool[rec['orders']['e0'][0]]['program'], task['hidden'][8:])))
        one = {name: int(bool(evaluate_program(pool[index]['program'],
                    task['hidden'][8:]))) for name, index in choices.items()}
        checked += 1 + len(one)
        result.append({'id': key, 'seed': task['seed'],
                       'public_block': public_block(task),
                       'features': cheap_public_features(rec, matrix),
                       'zero': zero, 'one': one,
                       'gain': {name: one[name] - zero for name in ACTIONS}})
    return result, checked


def model_rows(rows, action):
    return [{'id': row['id'], 'seed': row['seed'],
             'public_block': row['public_block'], 'features': row['features'],
             'gain': row['gain'][action]} for row in rows]


def score_target(rows, models, budget):
    forecast = {name: values(models[name], model_rows(rows, name))
                for name in ACTIONS}
    predicted = {row['id']: {name: float(forecast[name][i])
                             for name in ACTIONS}
                 for i, row in enumerate(rows)}
    by_seed = defaultdict(list)
    for row in rows:
        by_seed[row['seed']].append(row)
    banks = []
    for seed in sorted(by_seed):
        group = by_seed[seed]
        assert len(group) in (8, 48)
        entry = {'seed': seed, 'zero': sum(r['zero'] for r in group)}
        for policy in ('e0', 'plain', 'sensor', 'route'):
            def forecast_for(row):
                if policy == 'route':
                    return max(predicted[row['id']].values())
                return predicted[row['id']][policy]
            selected = {r['id'] for r in sorted(
                group, key=lambda r: (forecast_for(r), r['id']), reverse=True)[:budget]}
            def action_for(row):
                if policy != 'route':
                    return policy
                return max(ACTIONS, key=lambda name: (predicted[row['id']][name],
                                                       -ACTIONS.index(name)))
            entry[policy] = {
                'budgeted': sum(r['one'][action_for(r)] if r['id'] in selected
                                else r['zero'] for r in group),
                'one_each': sum(r['one'][action_for(r)] for r in group),
                'hindsight': entry['zero'] + sum(sorted(
                    (max(r['gain'].values()) if policy == 'route' else
                     r['gain'][policy] for r in group), reverse=True)[:budget])}
        banks.append(entry)
    totals = {name: {field: sum(b[name][field] for b in banks)
                     for field in ('budgeted', 'one_each', 'hindsight')}
              for name in ('e0', 'plain', 'sensor', 'route')}
    comparisons = {}
    for name in ('plain', 'sensor', 'route'):
        diffs = [b[name]['budgeted'] - b['e0']['budgeted'] for b in banks]
        comparisons[name] = {'gain': sum(diffs),
                             'positive_banks': sum(v > 0 for v in diffs),
                             'losing_banks': sum(v < 0 for v in diffs),
                             'interval': interval(diffs)}
    return {'tasks': len(rows), 'budget_per_bank': budget,
            'zero': sum(b['zero'] for b in banks),
            'totals': totals, 'comparisons': comparisons, 'banks': banks}


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    e0 = joblib.load(E0)
    candidate = {name: joblib.load(MODELS / f'{name}.joblib')
                 for name in ('plain', 'sensor')}
    source = []
    source_checked = 0
    for path in SOURCE:
        rows, checked = panel_rows(path, e0, candidate)
        source += rows
        source_checked += checked
    assert len(source) == 1152
    models = {name: fit_method(model_rows(source, name), 'interaction_100')
              for name in ACTIONS}
    targets = {}
    for path in TARGET:
        rows, checked = panel_rows(path, e0, candidate)
        budget = 4 if len(rows) in (96, 192) else 8
        targets[path.name] = {**score_target(rows, models, budget),
                              'candidate_choices_checked': checked}
    result = {'scope': 'opened development; candidate and query training panels disjoint',
              'candidate_source_tasks': 1152,
              'candidate_source_verified_survivors': 19789,
              'query_source_tasks': len(source),
              'query_source_choices_checked': source_checked,
              'query_model_rule': 'interaction_100',
              'targets': targets}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'targets'},
                      'targets': {name: {k: v for k, v in target.items() if k != 'banks'}
                                  for name, target in targets.items()}}, indent=2))


if __name__ == '__main__':
    main()
