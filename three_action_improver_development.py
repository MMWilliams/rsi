"""Opened screen of a three-action evaluator controller with paired outcome feedback."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import features
from pooled_zero_query_reranker_development import MODELS as POOLED_MODELS
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from zero_query_router_development import SOURCE, MIXED, rows_for
from cross_family_meta_improver_transfer import interval


TARGET=ROOT/'runs/zero-query-mixed-integration-transfer-20260918'
OUT=ROOT/'analysis/three-action-improver-development-20260918.json'
ACTIONS=('e0','ab','pooled')


def source_rows(path,candidate_models,pooled):
    current=rows_for(path,candidate_models)
    by_id={r['id']:r for r in current}
    tasks,base,wide,_,records=load_panel(path)
    for task,rec in zip(tasks,records):
        if task['id'] not in by_id:
            continue
        pool=wide.get(task['id'],base[task['id']])
        old=rec['orders']['old']
        n=min(100,len(old))
        x=features(task,pool,rec,n)
        p=pooled.predict_proba(x)[:,1]
        index=old[max(range(n),key=lambda i:(float(p[i]),-i))]
        by_id[task['id']]['labels']['pooled']=int(bool(evaluate_program(
            pool[index]['program'],task['hidden'][8:])))
    assert all(set(ACTIONS).issubset(r['labels']) for r in current)
    return current


def target_rows():
    assert json.loads((TARGET/'audit.json').read_text())['passed']
    outcomes=json.loads((TARGET/'results.json').read_text())['tasks']
    records={r['id']:r for r in json.loads((TARGET/'frozen_records.json').read_text())}
    return [{'id':r['id'],'seed':r['seed'],'domain':r['domain'],
             'features':records[r['id']]['zero_route_features'],
             'labels':{name:r['labels'][name] for name in ACTIONS}}
            for r in outcomes]


def fit(rows):
    x=np.asarray([r['features'] for r in rows],np.float32)
    clf=lambda:HistGradientBoostingClassifier(max_depth=3,max_iter=70,
        learning_rate=.05,min_samples_leaf=16,l2_regularization=5,
        random_state=221)
    heads={name:clf().fit(x,np.asarray([r['labels'][name] for r in rows],int))
           for name in ACTIONS}
    scaler=StandardScaler().fit(x)
    z=scaler.transform(x)
    effect={name:Ridge(alpha=30.).fit(z,np.asarray([
        r['labels'][name]-r['labels']['e0'] for r in rows],float))
            for name in ('ab','pooled')}
    return heads,scaler,effect


def predict(model,rows):
    heads,scaler,effect=model
    x=np.asarray([r['features'] for r in rows],np.float32)
    p=np.stack([heads[name].predict_proba(x)[:,1] for name in ACTIONS],axis=1)
    z=scaler.transform(x)
    gains=np.stack([np.zeros(len(rows)),effect['ab'].predict(z),
                    effect['pooled'].predict(z)],axis=1)
    return {'three_head':np.argmax(p,axis=1),
            'two_effect':np.argmax(gains,axis=1)}


def score(rows,choices):
    groups=defaultdict(list)
    for i,row in enumerate(rows):
        groups[row['seed']].append(i)
    banks=[]
    for seed,indices in sorted(groups.items()):
        bank={'seed':seed}
        for name,picks in choices.items():
            bank[name]=sum(rows[i]['labels'][ACTIONS[int(picks[i])]]
                           for i in indices)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(
                    rows[i]['labels'][ACTIONS[int(picks[i])]]
                    for i in indices if rows[i]['domain']==domain)
        banks.append(bank)
    totals={k:sum(b[k] for b in banks) for k in banks[0] if k!='seed'}
    pairs=(('later_three_head','early_three_head'),
           ('later_three_head','scrambled_three_head'),
           ('later_three_head','duplicate_three_head'),
           ('later_two_effect','early_two_effect'),
           ('later_three_head','ab'),('later_three_head','pooled'))
    comparisons={f'{a}_minus_{b}':{'gain':sum(r[a]-r[b] for r in banks),
        'wins':sum(r[a]>r[b] for r in banks),
        'losses':sum(r[a]<r[b] for r in banks),
        'interval':interval([r[a]-r[b] for r in banks])}
        for a,b in pairs}
    return {'tasks':len(rows),'totals':totals,'comparisons':comparisons,
            'banks':banks}


def main():
    if OUT.exists():
        raise RuntimeError('development exists')
    candidate_models={name:joblib.load(SHIFTED_MODELS/f'{name}_top100.joblib')
                      for name in ('a','ab')}
    pooled=joblib.load(POOLED_MODELS/'pooled_equal.joblib')
    source=[r for p in SOURCE for r in source_rows(p,candidate_models,pooled)]
    mixed=source_rows(MIXED,candidate_models,pooled)
    target=target_rows()
    assert len(source)==288 and len(mixed)==192 and len(target)==192
    rng=np.random.default_rng(904011)
    scrambled=[]
    for seed in sorted({r['seed'] for r in mixed}):
        group=[r for r in mixed if r['seed']==seed]
        perm=rng.permutation(len(group))
        scrambled.extend([{**r,'labels':group[int(j)]['labels']}
                          for r,j in zip(group,perm)])
    duplicate=[]
    for domain in ('familiar','shifted'):
        group=[r for r in source if r['domain']==domain]
        duplicate.extend([group[i] for i in rng.choice(len(group),96,replace=True)])
    training={'early':source,'later':source+mixed,
              'scrambled':source+scrambled,'duplicate':source+duplicate}
    choices={name:np.full(len(target),i,int)
             for i,name in enumerate(ACTIONS)}
    for name,rows in training.items():
        for rule,picks in predict(fit(rows),target).items():
            choices[name+'_'+rule]=picks
    result=score(target,choices)
    result['source']={'early_tasks':len(source),
                      'added_mixed_tasks':len(mixed),
                      'early_correct':{name:sum(r['labels'][name] for r in source)
                                       for name in ACTIONS},
                      'mixed_correct':{name:sum(r['labels'][name] for r in mixed)
                                       for name in ACTIONS}}
    result['scope']='opened target; screen only, no fresh claim'
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='banks'},indent=2))


if __name__=='__main__':
    main()
