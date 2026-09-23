"""Opened screen of familiar-AST-specific top-100 candidate feedback."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import features
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from pooled_zero_query_reranker_development import MODELS as POOLED_MODELS


FIRST=(ROOT/'runs/candidate-reranker-transfer-20260918',
       ROOT/'runs/candidate-reranker-replication-20260918')
SECOND=ROOT/'runs/combined-ranker-query-transfer-20260918'
TARGET=(ROOT/'runs/zero-query-mixed-integration-transfer-20260918',
        ROOT/'runs/three-action-improver-transfer-20260918')
OUT=ROOT/'analysis/familiar-ast-zero-query-development-20260918.json'
MODELS=ROOT/'analysis/familiar-ast-zero-query-models-20260918'


def arrays(paths):
    xs=[];ys=[];groups=[];tasks=0
    for path in paths:
        bank,base,wide,_,records=load_panel(path)
        for task,rec in zip(bank,records):
            if task['family']!='ast_transition':
                continue
            pool=wide.get(task['id'],base[task['id']])
            old=rec['orders']['old']
            n=min(100,len(old))
            x=features(task,pool,rec,n)
            y=np.asarray([int(bool(evaluate_program(pool[i]['program'],
                                                     task['hidden'][8:])))
                          for i in old[:n]],np.int8)
            group=list(range(sum(len(v) for v in ys),sum(len(v) for v in ys)+n))
            xs.append(x);ys.append(y);groups.append(group);tasks+=1
    return {'x':np.concatenate(xs),'y':np.concatenate(ys),
            'groups':groups,'tasks':tasks}


def score_panel(path,models):
    bank,base,wide,_,records=load_panel(path)
    ab=joblib.load(SHIFTED_MODELS/'ab_top100.joblib')
    pooled=joblib.load(POOLED_MODELS/'pooled_equal.joblib')
    rows=[]
    for task,rec in zip(bank,records):
        if task['family']!='ast_transition':
            continue
        pool=wide.get(task['id'],base[task['id']])
        old=rec['orders']['old'];n=min(100,len(old))
        x=features(task,pool,rec,n)
        choices={'e0':rec['orders']['e0'][0]}
        for name,model in {**models,'ab':ab,'pooled':pooled}.items():
            p=model.predict_proba(x)[:,1]
            choices[name]=old[max(range(n),key=lambda i:(float(p[i]),-i))]
        labels={name:int(bool(evaluate_program(pool[i]['program'],
                                               task['hidden'][8:])))
                for name,i in choices.items()}
        rows.append({'seed':task['seed'],'labels':labels})
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        banks.append({'seed':seed,**{name:sum(r['labels'][name] for r in group)
                             for name in rows[0]['labels']}})
    totals={name:sum(b[name] for b in banks) for name in banks[0] if name!='seed'}
    pairs=(('early','e0'),('later','early'),('later','scrambled'),
           ('later','duplicate'),('later','pooled'))
    comparisons={f'{a}_minus_{b}':{'gain':sum(r[a]-r[b] for r in banks),
        'wins':sum(r[a]>r[b] for r in banks),
        'losses':sum(r[a]<r[b] for r in banks),
        'interval':interval([r[a]-r[b] for r in banks])}
        for a,b in pairs}
    return {'tasks':len(rows),'totals':totals,'comparisons':comparisons,
            'banks':banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development exists')
    assert all(json.loads((p/'audit.json').read_text())['passed']
               for p in FIRST+(SECOND,)+TARGET)
    a=arrays(FIRST)
    b=arrays((SECOND,))
    assert a['tasks']==192 and b['tasks']==96
    x=np.r_[a['x'],b['x']]
    y=np.r_[a['y'],b['y']]
    rng=np.random.default_rng(904220)
    scrambled=b['y'].copy()
    for group in b['groups']:
        scrambled[group]=rng.permutation(scrambled[group])
    models={'early':model_for(15).fit(a['x'],a['y']),
            'later':model_for(15).fit(x,y),
            'scrambled':model_for(15).fit(x,np.r_[a['y'],scrambled]),
            'duplicate':model_for(15).fit(
                np.r_[a['x'],a['x'][:len(b['x'])]],
                np.r_[a['y'],a['y'][:len(b['y'])]])}
    MODELS.mkdir(parents=True)
    for name,model in models.items():
        joblib.dump(model,MODELS/f'{name}.joblib',compress=3)
    targets={p.name:score_panel(p,models) for p in TARGET}
    result={'scope':'opened development only','source':{
        'early_tasks':a['tasks'],'later_tasks':a['tasks']+b['tasks'],
        'early_labels':len(a['y']),'later_labels':len(y),
        'early_positive':int(a['y'].sum()),'later_positive':int(y.sum())},
        'targets':targets}
    write_json(OUT,result)
    print(json.dumps({'scope':result['scope'],'source':result['source'],
        'targets':{k:{z:v for z,v in value.items() if z!='banks'}
                   for k,value in targets.items()}},indent=2))


if __name__=='__main__':
    main()
