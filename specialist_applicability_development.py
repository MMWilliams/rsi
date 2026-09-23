"""Opened effect-prediction screen for routing a shifted AST evaluator."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0, SOURCE, load_panel
from shifted_survivor_growth_development import B, C, rows_for


SPECIALIST = ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918/a_plain100.joblib'
D = ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918'
FAMILIAR_TARGET = ROOT / 'runs/combined-ranker-query-transfer-20260918'
OUT = ROOT / 'analysis/specialist-applicability-development-v2-20260918.json'
POLICIES = ('e0', 'specialist', 'visible_route', 'effect_route')


def pair_features(pair):
    inp, out = pair
    code = np.asarray([ord(c) - 0x800 for c in inp], float)
    kept = np.asarray([ord(c) - 0x800 for c in out], float)
    if inp.startswith(out):
        omitted = code[len(out):]
        prefix = 1.
    elif inp.endswith(out):
        omitted = code[:len(inp) - len(out)]
        prefix = 0.
    else:
        omitted = code
        prefix = .5
    if len(omitted) == 0:
        omitted = np.asarray([0.])
    return [len(inp) / 10, len(out) / 10, prefix,
            float(code.mean()) / 256, float(code.std()) / 128,
            float(kept.mean()) / 256, float(omitted.mean()) / 256,
            float(kept.std()) / 128, float(omitted.std()) / 128,
            float(np.mean(np.diff(code) > 0)) if len(code) > 1 else 0.,
            float(np.mean(np.diff(code) < 0)) if len(code) > 1 else 0.,
            float(np.mean(code % 2 == 0)), float(np.mean(code % 3 == 0)),
            float(np.mean(code % 5 == 0)), float(np.mean(code % 7 == 0))]


def public_row(task, rec, pool, matrix, e0, specialist):
    candidates, surviving = rows_for(task, pool, rec, matrix, e0)
    old = rec['orders']['old']
    e0_choice = next(i for i in rec['orders']['e0'] if i in surviving)
    if candidates:
        x = np.asarray([row['plain'] for row in candidates], np.float32)
        p = specialist.predict_proba(x)[:, 1]
        chosen = max(range(len(candidates)), key=lambda i: (float(p[i]), -i))
        spec_choice = candidates[chosen]['index']
        spec_prob = float(p[chosen])
        other = sorted((float(v) for j, v in enumerate(p) if j != chosen),
                       reverse=True)
        margin = spec_prob - (other[0] if other else 0.)
        rank = candidates[chosen]['old_rank']
        e0_row = next((r for r in candidates if r['index'] == e0_choice), None)
    else:
        spec_choice = e0_choice
        spec_prob = 0.
        margin = 0.
        rank = len(old)
        e0_row = None
    score = np.asarray(rec['old_scores'], float)
    std = max(float(score.std()), .05)
    ranks = {index: i for i, index in enumerate(old)}
    probe = rec['probe']
    visible = pair_features(task['visible'][0])
    observed = pair_features(task['hidden'][probe])
    actions = [spec_prob, margin, rank / max(1, len(old)),
               ranks[e0_choice] / max(1, len(old)),
               (score[spec_choice] - score[e0_choice]) / std,
               len(candidates) / 100, len(surviving) / len(pool),
               float(spec_choice == e0_choice),
               sum(matrix[spec_choice][j] == matrix[e0_choice][j]
                   for j in range(8)) / 8,
               float(e0_row is not None)]
    return {'id': task['id'], 'visible_features': visible + observed,
            'effect_features': visible + observed + actions,
            'choices': {'e0': e0_choice, 'specialist': spec_choice},
            'e0_top100_candidate_scores': min(100, len(old)),
            'specialist_candidate_scores': len(candidates)}


def task_row(task, rec, pool, matrix, e0, specialist):
    public = public_row(task, rec, pool, matrix, e0, specialist)
    e0_correct = int(bool(evaluate_program(
        pool[public['choices']['e0']]['program'], task['hidden'][8:])))
    specialist_correct = int(bool(evaluate_program(
        pool[public['choices']['specialist']]['program'], task['hidden'][8:])))
    return {'id': task['id'], 'seed': task['seed'],
            'domain': 'shifted' if task['family'] == 'shifted_ast' else 'familiar',
            'visible_features': public['visible_features'],
            'effect_features': public['effect_features'],
            'e0': e0_correct, 'specialist': specialist_correct,
            'effect': specialist_correct - e0_correct}


def panel_rows(path, e0, specialist):
    tasks, base, wide, matrices, records = load_panel(path)
    result = []
    for task, rec in zip(tasks, records):
        if task['family'] not in ('ast_transition', 'shifted_ast'):
            continue
        key = task['id']
        pool = wide.get(key, base[key])
        result.append(task_row(task, rec, pool, matrices[key], e0, specialist))
    return result


def summarize(rows, decisions):
    by_domain = {}
    for domain in ('familiar', 'shifted'):
        subset = [row for row in rows if row['domain'] == domain]
        banks = []
        for seed in sorted({row['seed'] for row in subset}):
            group = [row for row in subset if row['seed'] == seed]
            banks.append({'seed': seed, **{
                name: sum(row['specialist'] if decisions[name][row['id']]
                          else row['e0'] for row in group)
                for name in POLICIES}})
        totals = {name: sum(bank[name] for bank in banks) for name in POLICIES}
        comparison = {}
        for name in POLICIES[1:]:
            diff = [bank[name] - bank['e0'] for bank in banks]
            comparison[name] = {'gain': sum(diff),
                                'positive_banks': sum(x > 0 for x in diff),
                                'losing_banks': sum(x < 0 for x in diff),
                                'interval': interval(diff)}
        by_domain[domain] = {'tasks': len(subset), 'banks': banks,
                             'totals': totals, 'comparisons': comparison}
    total = {name: sum(by_domain[d]['totals'][name] for d in by_domain)
             for name in POLICIES}
    return {'domains': by_domain, 'total': total}


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    assert json.loads((D / 'audit.json').read_text())['passed']
    e0 = joblib.load(E0)
    specialist = joblib.load(SPECIALIST)
    training = []
    for path in SOURCE + (B,):
        training.extend(panel_rows(path, e0, specialist))
    assert sum(r['domain'] == 'shifted' for r in training) == 192
    assert sum(r['domain'] == 'familiar' for r in training) == 192
    visible = HistGradientBoostingClassifier(
        max_depth=3, max_iter=70, learning_rate=.05,
        min_samples_leaf=16, l2_regularization=5, random_state=27).fit(
            np.asarray([r['visible_features'] for r in training], np.float32),
            np.asarray([r['domain'] == 'shifted' for r in training], int))
    effect = HistGradientBoostingRegressor(
        max_depth=3, max_iter=70, learning_rate=.05,
        min_samples_leaf=16, l2_regularization=5, random_state=27).fit(
            np.asarray([r['effect_features'] for r in training], np.float32),
            np.asarray([r['effect'] for r in training], float))
    target = []
    for path in (C, D, FAMILIAR_TARGET):
        target.extend(panel_rows(path, e0, specialist))
    assert sum(r['domain'] == 'shifted' for r in target) == 384
    assert sum(r['domain'] == 'familiar' for r in target) == 96
    vp = visible.predict_proba(np.asarray(
        [r['visible_features'] for r in target], np.float32))[:, 1]
    ep = effect.predict(np.asarray(
        [r['effect_features'] for r in target], np.float32))
    decision = {name: {} for name in POLICIES}
    for row, visible_prob, gain in zip(target, vp, ep):
        decision['e0'][row['id']] = False
        decision['specialist'][row['id']] = True
        decision['visible_route'][row['id']] = bool(visible_prob >= .5)
        decision['effect_route'][row['id']] = bool(gain > 0.)
    result = {'scope': 'opened development; source candidate model disjoint from router rows',
              'training_tasks': len(training), 'target_tasks': len(target),
              'effect_source_distribution': {
                  'positive': sum(r['effect'] > 0 for r in training),
                  'negative': sum(r['effect'] < 0 for r in training),
                  'zero': sum(r['effect'] == 0 for r in training)},
              'routes_to_specialist': {name: sum(decision[name].values())
                                       for name in ('visible_route', 'effect_route')},
              'target_rows': [{'id': row['id'], 'seed': row['seed'],
                               'domain': row['domain'], 'e0': row['e0'],
                               'specialist': row['specialist'],
                               'visible_probability': float(v),
                               'predicted_effect': float(e)}
                              for row, v, e in zip(target, vp, ep)],
              'target': summarize(target, decision)}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'target'},
                      'target': {'total': result['target']['total'],
                                 'domains': {name: {k: v for k, v in value.items()
                                                    if k != 'banks'}
                                             for name, value in
                                             result['target']['domains'].items()}}},
                     indent=2))


if __name__ == '__main__':
    main()
