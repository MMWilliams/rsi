"""Opened development of query/action-value updates from shifted-arithmetic feedback."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib

from rsi.common import ROOT, write_json
from cross_family_meta_improver_development import fit_method, values
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0
from wide_post_query_development import MODELS
from joint_survivor_query_development import (ACTIONS, SOURCE, panel_rows,
                                               model_rows)


SHIFTED_SOURCE = ROOT / 'runs/shifted-ast-seed-transfer-20260918'
TARGET = ROOT / 'runs/post-query-feedback-transfer-20260918'
OUT = ROOT / 'analysis/shifted-feedback-query-development-20260918.json'
METHODS = ('prior', 'shifted_basic_10', 'shifted_basic_100',
           'pooled_4', 'pooled_12')


def fitted(prior, shifted):
    result = {}
    for method in METHODS:
        result[method] = {}
        for action in ACTIONS:
            if method == 'prior':
                source, rule = prior, 'interaction_100'
            elif method == 'shifted_basic_10':
                source, rule = shifted, 'basic_10'
            elif method == 'shifted_basic_100':
                source, rule = shifted, 'basic_100'
            else:
                repeat = int(method.split('_')[1])
                source, rule = prior + shifted * repeat, 'interaction_100'
            result[method][action] = fit_method(model_rows(source, action), rule)
    return result


def score(rows, models):
    by_seed = defaultdict(list)
    for row in rows:
        by_seed[row['seed']].append(row)
    results = {}
    for method, action_models in models.items():
        forecasts = {name: values(model, model_rows(rows, name))
                     for name, model in action_models.items()}
        pred = {row['id']: {name: float(forecasts[name][i])
                            for name in ACTIONS}
                for i, row in enumerate(rows)}
        banks = []
        for seed, group in sorted(by_seed.items()):
            assert len(group) == 8
            bank = {'seed': seed}
            for policy in ('e0', 'route'):
                def value(row):
                    return (pred[row['id']]['e0'] if policy == 'e0'
                            else max(pred[row['id']].values()))
                chosen = {r['id'] for r in sorted(
                    group, key=lambda r: (value(r), r['id']), reverse=True)[:4]}
                def action(row):
                    return ('e0' if policy == 'e0' else max(
                        ACTIONS, key=lambda a: (pred[row['id']][a],
                                                -ACTIONS.index(a))))
                bank[policy] = sum(r['one'][action(r)] if r['id'] in chosen
                                   else r['zero'] for r in group)
            banks.append(bank)
        results[method] = {'e0': sum(b['e0'] for b in banks),
                           'route': sum(b['route'] for b in banks),
                           'banks': banks}
    baseline = results['prior']
    for method, result in results.items():
        result['comparisons'] = {}
        for policy in ('e0', 'route'):
            diffs = [a[policy] - b[policy]
                     for a, b in zip(result['banks'], baseline['banks'])]
            result['comparisons'][policy] = {
                'gain_vs_prior': sum(diffs),
                'positive_banks': sum(d > 0 for d in diffs),
                'losing_banks': sum(d < 0 for d in diffs),
                'interval': interval(diffs)}
    return results


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    e0 = joblib.load(E0)
    candidates = {name: joblib.load(MODELS / f'{name}.joblib')
                  for name in ('plain', 'sensor')}
    prior = []
    prior_checked = 0
    for path in SOURCE:
        rows, count = panel_rows(path, e0, candidates)
        prior += rows
        prior_checked += count
    shifted, shifted_checked = panel_rows(SHIFTED_SOURCE, e0, candidates)
    target, target_checked = panel_rows(TARGET, e0, candidates)
    assert len(prior) == 1152 and len(shifted) == 96 and len(target) == 192
    models = fitted(prior, shifted)
    result = {'scope': 'opened development; target labels already opened',
              'candidate_source_tasks': 1152, 'familiar_query_source_tasks': len(prior),
              'shifted_feedback_source_tasks': len(shifted),
              'target_tasks': len(target),
              'candidate_choices_checked': {
                  'familiar_source': prior_checked, 'shifted_source': shifted_checked,
                  'target': target_checked},
              'target': score(target, models)}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'target'},
                      'target': {name: {k: v for k, v in value.items()
                                        if k != 'banks'}
                                 for name, value in result['target'].items()}},
                     indent=2))


if __name__ == '__main__':
    main()
