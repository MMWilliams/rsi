"""Opened cross-fit screen for routing between validated familiar and shifted rankers."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier,HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import features
from zero_query_router_development import public_row
from familiar_ast_zero_query_development import MODELS as FAMILIAR_MODELS
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from cross_family_meta_improver_transfer import interval


PANEL=(ROOT/'runs/zero-query-mixed-integration-transfer-20260918',
       ROOT/'runs/three-action-improver-transfer-20260918')
VISIBLE=ROOT/'runs/zero-query-mixed-integration-transfer-20260918/visible_later.joblib'
OUT=ROOT/'analysis/dual-specialist-router-development-20260918.json'


def public_pair(task,rec,pool,candidate,familiar,visible):
    public=public_row(task,rec,pool,candidate)
    old=rec['orders']['old']
    n=min(100,len(old))
    x=features(task,pool,rec,n)
    p=familiar.predict_proba(x)[:,1]
    order=sorted(range(n),key=lambda i:(-float(p[i]),i))
    fam=old[order[0]]
    shift=public['choices']['ab']
    score=np.asarray(rec['old_scores'],float)
    std=max(float(score.std()),.05)
    rank={index:i for i,index in enumerate(old)}
    fv=public['features']+[float(p[order[0]]),
        float(p[order[0]]-p[order[1]]) if n>1 else 0.,
        rank[fam]/100.,(score[fam]-score[shift])/std,
        float(fam==shift)]
    prob=float(visible.predict_proba(np.asarray(
        [public['features']],np.float32))[0,1])
    return {'features':fv,'visible_probability':prob,
            'choices':{'familiar':fam,'shifted':shift},
            'confidence_difference':public['features'][-7]-float(p[order[0]]),
            'candidate_scores':{'a':n,'ab':n,'familiar':n}}


def rows_for(path,candidate,familiar,visible):
    tasks,base,wide,_,records=load_panel(path)
    rows=[]
    for task,rec in zip(tasks,records):
        pool=wide.get(task['id'],base[task['id']])
        public=public_pair(task,rec,pool,candidate,familiar,visible)
        labels={name:int(bool(evaluate_program(pool[index]['program'],
                                                task['hidden'][8:])))
                for name,index in public['choices'].items()}
        rows.append({'id':task['id'],'seed':task['seed'],
            'domain':'shifted' if task['family']=='shifted_ast' else 'familiar',
            'features':public['features'],
            'visible_probability':public['visible_probability'],
            'labels':labels,'effect':labels['shifted']-labels['familiar'],
            'confidence_difference':public['confidence_difference']})
    return rows


def fit(rows):
    x=np.asarray([r['features'] for r in rows],np.float32)
    effect=np.asarray([r['effect'] for r in rows],float)
    domain=np.asarray([r['domain']=='shifted' for r in rows],int)
    clf=lambda:HistGradientBoostingClassifier(max_depth=3,max_iter=70,
        learning_rate=.05,min_samples_leaf=16,l2_regularization=5,
        random_state=221)
    reg=HistGradientBoostingRegressor(max_depth=3,max_iter=70,
        learning_rate=.05,min_samples_leaf=16,l2_regularization=5,
        random_state=221).fit(x,effect)
    familiar=clf().fit(x,np.asarray([r['labels']['familiar'] for r in rows],int))
    shifted=clf().fit(x,np.asarray([r['labels']['shifted'] for r in rows],int))
    scaler=StandardScaler().fit(x)
    ridge=Ridge(alpha=30.).fit(scaler.transform(x),effect)
    return {'reg':reg,'familiar':familiar,'shifted':shifted,
            'domain':clf().fit(x,domain),'scaler':scaler,'ridge':ridge}


def decisions(model,rows):
    x=np.asarray([r['features'] for r in rows],np.float32)
    effect=model['reg'].predict(x)
    heads=(model['shifted'].predict_proba(x)[:,1]-
           model['familiar'].predict_proba(x)[:,1])
    ridge=model['ridge'].predict(model['scaler'].transform(x))
    domain=model['domain'].predict_proba(x)[:,1]
    return {'effect':effect>0,'twohead':heads>0,
            'ridge':ridge>0,'domain':domain>=.6}


def score(rows,choices):
    groups=defaultdict(list)
    for i,r in enumerate(rows):groups[r['seed']].append(i)
    banks=[]
    for seed,ids in sorted(groups.items()):
        bank={'seed':seed}
        for name,selection in choices.items():
            bank[name]=sum(rows[i]['labels']['shifted' if selection[i]
                             else 'familiar'] for i in ids)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(rows[i]['labels'][
                    'shifted' if selection[i] else 'familiar'] for i in ids
                    if rows[i]['domain']==domain)
        bank['oracle_two']=sum(max(rows[i]['labels'].values()) for i in ids)
        banks.append(bank)
    totals={k:sum(b[k] for b in banks) for k in banks[0] if k!='seed'}
    comparisons={}
    for name in choices:
        if name=='shifted':continue
        d=[b[name]-b['shifted'] for b in banks]
        comparisons[name]={'gain':sum(d),'wins':sum(v>0 for v in d),
            'losses':sum(v<0 for v in d),'interval':interval(d)}
    return {'tasks':len(rows),'totals':totals,'comparisons':comparisons,
            'banks':banks}


def main():
    if OUT.exists():raise RuntimeError('development exists')
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANEL)
    candidate={name:joblib.load(SHIFTED_MODELS/f'{name}_top100.joblib')
               for name in ('a','ab')}
    familiar=joblib.load(FAMILIAR_MODELS/'early.joblib')
    visible=joblib.load(VISIBLE)
    panels=[rows_for(p,candidate,familiar,visible) for p in PANEL]
    rows=[]
    for train,test in ((panels[0],panels[1]),(panels[1],panels[0])):
        model=fit(train)
        pred=decisions(model,test)
        for i,row in enumerate(test):
            rows.append({**row,'decisions':{name:bool(v[i])
                                           for name,v in pred.items()}})
    rows.sort(key=lambda r:(r['seed'],r['id']))
    choices={'familiar':np.zeros(len(rows),bool),
             'shifted':np.ones(len(rows),bool),
             'prior_visible':np.asarray([r['visible_probability']>=.6
                                         for r in rows]),
             'confidence':np.asarray([r['confidence_difference']>0
                                      for r in rows]),
             'type_oracle':np.asarray([r['domain']=='shifted' for r in rows])}
    for name in ('effect','twohead','ridge','domain'):
        choices[name]=np.asarray([r['decisions'][name] for r in rows])
    result=score(rows,choices)
    result['source']={'panels':[p.name for p in PANEL],
                      'tasks_per_panel':[len(x) for x in panels],
                      'familiar_correct':[sum(r['labels']['familiar'] for r in x)
                                          for x in panels],
                      'shifted_correct':[sum(r['labels']['shifted'] for r in x)
                                         for x in panels]}
    result['scope']='opened cross-fit development only'
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='banks'},indent=2))


if __name__=='__main__':
    main()
