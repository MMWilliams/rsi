"""Opened mixed-bank screen of feedback-driven zero-query evaluator routing."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from shifted_zero_query_reranker_development import MODELS
from wide_candidate_reranker_development import features
from specialist_applicability_development import pair_features
from cross_family_meta_improver_transfer import interval


SHIFTED = ROOT / 'runs/zero-query-shifted-feedback-transfer-20260918'
FAMILIAR = ROOT / 'runs/combined-ranker-query-transfer-20260918'
MIXED = ROOT / 'runs/specialist-applicability-transfer-20260918'
OUT = ROOT / 'analysis/zero-query-router-development-20260918.json'
SOURCE = (SHIFTED, FAMILIAR)


def public_row(task, rec, pool, models):
    old = rec['orders']['old']
    n = min(100, len(old))
    x = features(task, pool, rec, n)
    score = np.asarray(rec['old_scores'], float)
    std = max(float(score.std()), .05)
    top = {}
    confidence = {}
    for name, model in models.items():
        p = model.predict_proba(x)[:, 1]
        order = sorted(range(n), key=lambda i: (-float(p[i]), i))
        top[name] = old[order[0]]
        confidence[name] = (float(p[order[0]]),
                            float(p[order[0]] - p[order[1]]) if n > 1 else 0.)
    e0 = rec['orders']['e0'][0]
    old_rank = {index: rank for rank, index in enumerate(old)}
    ab = top['ab']
    a = top['a']
    data = pair_features(task['visible'][0])
    data.extend([len(pool)/512., n/100., std,
                 old_rank[ab]/100., old_rank[a]/100., old_rank[e0]/100.,
                 (score[ab]-score[e0])/std,
                 (score[a]-score[e0])/std,
                 confidence['ab'][0], confidence['ab'][1],
                 confidence['a'][0], confidence['a'][1],
                 float(ab == e0), float(a == e0), float(ab == a)])
    return {'features': data, 'choices': {'e0':e0, 'a':a, 'ab':ab},
            'candidate_scores':{'a':n,'ab':n}}


def rows_for(path, models):
    tasks, base, wide, _, records = load_panel(path)
    result = []
    for task, rec in zip(tasks, records):
        if task['family'] not in ('ast_transition', 'shifted_ast'):
            continue
        pool = wide.get(task['id'], base[task['id']])
        public = public_row(task, rec, pool, models)
        labels = {name: int(bool(evaluate_program(pool[index]['program'],
                                                   task['hidden'][8:])))
                  for name, index in public['choices'].items()}
        result.append({'id': task['id'], 'seed': task['seed'],
                       'domain': 'shifted' if task['family']=='shifted_ast'
                       else 'familiar', 'features': public['features'],
                       'labels': labels, 'effect': labels['ab']-labels['e0']})
    return result


def learner(rows):
    x = np.asarray([r['features'] for r in rows], np.float32)
    effect = np.asarray([r['effect'] for r in rows], float)
    domain = np.asarray([r['domain']=='shifted' for r in rows], int)
    e0 = np.asarray([r['labels']['e0'] for r in rows], int)
    ab = np.asarray([r['labels']['ab'] for r in rows], int)
    reg = HistGradientBoostingRegressor(max_depth=3, max_iter=70,
        learning_rate=.05, min_samples_leaf=16, l2_regularization=5,
        random_state=221).fit(x, effect)
    clf = lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=70,
        learning_rate=.05, min_samples_leaf=16, l2_regularization=5,
        random_state=221)
    scaler = StandardScaler().fit(x)
    return {'effect': reg, 'domain': clf().fit(x, domain),
            'e0': clf().fit(x, e0), 'ab': clf().fit(x, ab),
            'ridge': Ridge(alpha=30.).fit(scaler.transform(x), effect),
            'scaler': scaler}


def decisions(models, rows):
    x = np.asarray([r['features'] for r in rows], np.float32)
    effect = models['effect'].predict(x)
    two = (models['ab'].predict_proba(x)[:,1] -
           models['e0'].predict_proba(x)[:,1])
    ridge = models['ridge'].predict(models['scaler'].transform(x))
    domain = models['domain'].predict_proba(x)[:,1]
    return {'effect': effect > 0., 'twohead': two > 0.,
            'ridge': ridge > 0., 'visible': domain >= .5}


def score(rows, choices):
    by_bank = defaultdict(list)
    for i, row in enumerate(rows):
        by_bank[row['seed']].append(i)
    banks = []
    for seed, ids in sorted(by_bank.items()):
        bank = {'seed': seed}
        for name, choose in choices.items():
            bank[name] = sum(rows[i]['labels']['ab'] if choose[i]
                             else rows[i]['labels']['e0'] for i in ids)
            bank[name+'_familiar'] = sum(
                rows[i]['labels']['ab'] if choose[i] else rows[i]['labels']['e0']
                for i in ids if rows[i]['domain']=='familiar')
            bank[name+'_shifted'] = sum(
                rows[i]['labels']['ab'] if choose[i] else rows[i]['labels']['e0']
                for i in ids if rows[i]['domain']=='shifted')
        banks.append(bank)
    totals = {key: sum(b[key] for b in banks) for key in banks[0] if key!='seed'}
    comparisons = {}
    for name in choices:
        if name == 'e0':
            continue
        diffs = [b[name]-b['e0'] for b in banks]
        comparisons[name] = {'gain': sum(diffs),
            'positive_banks': sum(x>0 for x in diffs),
            'losing_banks': sum(x<0 for x in diffs),
            'interval': interval(diffs)}
    return {'tasks': len(rows), 'totals': totals, 'comparisons': comparisons,
            'banks': banks}


def evaluate(model, rows):
    d = decisions(model, rows)
    d.update({'e0': np.zeros(len(rows), bool),
              'ab': np.ones(len(rows), bool),
              'type_oracle': np.asarray([r['domain']=='shifted' for r in rows])})
    return score(rows, d)


def crossfit(source, mixed):
    # Two fixed bank halves; each later parent receives 12 mixed banks and
    # transfers only to the opposite 12. Controls preserve record counts.
    seeds = sorted({r['seed'] for r in mixed})
    halves = [set(seeds[:12]), set(seeds[12:])]
    all_rows = []
    for target_seeds in halves:
        train = [r for r in mixed if r['seed'] not in target_seeds]
        test = [r for r in mixed if r['seed'] in target_seeds]
        early = learner(source)
        later = learner(source+train)
        d0 = decisions(early, test)
        d1 = decisions(later, test)
        for i, row in enumerate(test):
            all_rows.append({**row, 'early_decisions':
                             {k: bool(v[i]) for k,v in d0.items()},
                             'later_decisions':
                             {k: bool(v[i]) for k,v in d1.items()}})
    all_rows.sort(key=lambda r: (r['seed'],r['id']))
    choices = {'e0': np.zeros(len(all_rows), bool),
               'ab': np.ones(len(all_rows), bool)}
    for stage in ('early','later'):
        for name in ('effect','twohead','ridge','visible'):
            choices[stage+'_'+name] = np.asarray(
                [r[stage+'_decisions'][name] for r in all_rows])
    return score(all_rows, choices)


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    assert all(json.loads((p/'audit.json').read_text())['passed']
               for p in SOURCE+(MIXED,))
    models = {name: joblib.load(MODELS/f'{name}_top100.joblib')
              for name in ('a','ab')}
    source = [r for path in SOURCE for r in rows_for(path, models)]
    mixed = rows_for(MIXED, models)
    assert len(source)==288 and len(mixed)==192
    early = evaluate(learner(source), mixed)
    crossed = crossfit(source, mixed)
    result = {'scope': 'opened development only', 'source_tasks':len(source),
              'source_shifted':sum(r['domain']=='shifted' for r in source),
              'source_familiar':sum(r['domain']=='familiar' for r in source),
              'mixed_tasks':len(mixed), 'early':early, 'crossfit':crossed}
    write_json(OUT,result)
    print(json.dumps({k: {z:v for z,v in value.items() if z!='banks'}
                      if k in ('early','crossfit') else value
                      for k,value in result.items()},indent=2))


if __name__ == '__main__':
    main()
