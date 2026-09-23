"""Opened matched-row controls for the incremental public-feature router."""
from __future__ import annotations

import json

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from shifted_zero_query_reranker_development import MODELS
from zero_query_router_development import (SOURCE, MIXED, OUT as SCREEN,
                                           rows_for, score)

OUT = ROOT / 'analysis/zero-query-router-controls-development-20260918.json'


def fit(rows):
    x = np.asarray([r['features'] for r in rows], np.float32)
    y = np.asarray([r['domain']=='shifted' for r in rows], int)
    return HistGradientBoostingClassifier(max_depth=3, max_iter=70,
        learning_rate=.05, min_samples_leaf=16, l2_regularization=5,
        random_state=221).fit(x, y)


def predict(model, rows):
    x = np.asarray([r['features'] for r in rows], np.float32)
    return model.predict_proba(x)[:,1] >= .5


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    assert SCREEN.exists()
    models = {name: joblib.load(MODELS/f'{name}_top100.joblib')
              for name in ('a','ab')}
    source = [r for path in SOURCE for r in rows_for(path, models)]
    mixed = rows_for(MIXED, models)
    assert len(source)==288 and len(mixed)==192
    seeds = sorted({r['seed'] for r in mixed})
    halves = [set(seeds[:12]),set(seeds[12:])]
    all_rows=[]
    for fold,target_seeds in enumerate(halves):
        train=[r for r in mixed if r['seed'] not in target_seeds]
        target=[r for r in mixed if r['seed'] in target_seeds]
        rng=np.random.default_rng(903890+fold)
        scrambled=[]
        for seed in sorted({r['seed'] for r in train}):
            group=[r for r in train if r['seed']==seed]
            labels=rng.permutation([r['domain'] for r in group])
            scrambled.extend([{**r,'domain':str(label)}
                              for r,label in zip(group,labels)])
        repeated=[]
        for domain in ('familiar','shifted'):
            subset=[r for r in source if r['domain']==domain]
            repeated.extend([subset[i] for i in rng.choice(len(subset),48,
                                                            replace=True)])
        candidates={'early':source,
                    'later_true':source+train,
                    'later_scrambled':source+scrambled,
                    'balanced_duplicate':source+repeated}
        predictions={name:predict(fit(rows),target)
                     for name,rows in candidates.items()}
        for i,row in enumerate(target):
            all_rows.append({**row,'choices':
                             {name:bool(p[i]) for name,p in predictions.items()}})
    all_rows.sort(key=lambda r:(r['seed'],r['id']))
    choices={name:np.asarray([r['choices'][name] for r in all_rows])
             for name in ('early','later_true','later_scrambled',
                          'balanced_duplicate')}
    choices['e0']=np.zeros(len(all_rows),bool)
    choices['ab']=np.ones(len(all_rows),bool)
    result=score(all_rows,choices)
    pairs=(('later_true','early'),('later_true','later_scrambled'),
           ('later_true','balanced_duplicate'))
    result['paired']={f'{a}_minus_{b}':{
        'gain':sum(row[a]-row[b] for row in result['banks']),
        'wins':sum(row[a]>row[b] for row in result['banks']),
        'losses':sum(row[a]<row[b] for row in result['banks']),
        'interval':interval([row[a]-row[b] for row in result['banks']])}
        for a,b in pairs}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='banks'},indent=2))


if __name__=='__main__':
    main()
