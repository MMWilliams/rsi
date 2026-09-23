"""Inspected-bank development of a sequential output-query allocator."""
from __future__ import annotations

import json
import math

import numpy as np

from rsi.common import ROOT,write_json
from ast_query_allocation_development import features,fit,predict,allocate,fixed
from ast_value_feature_development import load_rows
from ast_probe_sensor_development import choose_probe


OUT=ROOT/'analysis/adaptive-ast-query-development.json'
RIDGE=10.


def initial_features(row):
    return features(row['task'],row['record'],row['matrix'])


def after_first(row,observed):
    """Features available only after buying the first true output."""
    task=row['task']; record=row['record']; matrix=row['matrix']
    order=record['order']; scores=np.asarray(record['scores'],float)
    first=record['first_probe']['top20_entropy']
    matched={i for i in range(len(order)) if matrix[i][first]==observed}
    remaining=matched if matched else set(range(len(order)))
    ranked=[i for i in order if i in remaining]
    chosen=ranked[0]
    second=choose_probe(task['id'],matrix,order,scores,remaining,[first],
                        'top20_entropy')
    top=ranked[:20]
    second_values=[matrix[i][second] for i in top]
    counts={}
    for v in second_values:counts[v]=counts.get(v,0)+1
    mass=np.asarray(list(counts.values()),float)/len(top)
    std=max(float(scores.std()),.05)
    original_top=order[0]
    return np.r_[initial_features(row),
                 len(matched)/len(order),len(matched)/max(1,len(order)),
                 len(top)/20,
                 order.index(chosen)/len(order),
                 (scores[order[0]]-scores[chosen])/std,
                 float(chosen!=original_top),
                 float(matrix[original_top][first]==observed),
                 len(observed)/12,
                 len(counts)/len(top),
                 -sum(p*math.log(p) for p in mass),
                 1-counts[matrix[chosen][second]]/len(top),
                 float(second)/7]


def train(rows):
    x=np.stack([initial_features(r) for r in rows])
    y1=np.asarray([r['correct'][1]-r['correct'][0] for r in rows],float)
    y2=np.asarray([r['correct'][2]-r['correct'][1] for r in rows],float)
    prior=fit(x,y1,y2,RIDGE)
    post=np.stack([after_first(r,r['task']['hidden'][
        r['record']['first_probe']['top20_entropy']][1]) for r in rows])
    conditional=fit(post,y2,np.zeros(len(rows)),RIDGE)
    return prior,conditional


def simulate(bank,models,mode):
    """Spend eight calls; reveal a true output only when its action is bought."""
    prior,conditional=models
    x=np.stack([initial_features(r) for r in bank])
    p1,p2=predict(prior,x)
    count=[0]*len(bank); observed=[None]*len(bank); trace=[]
    for step in range(len(bank)):
        offers=[]
        for i,row in enumerate(bank):
            if count[i]==2:continue
            if count[i]==0:value=float(p1[i])
            elif mode=='conditional':
                feat=after_first(row,observed[i])[None,:]
                value=float(predict(conditional,feat)[0][0])
            elif mode=='prior':value=float(p2[i])
            else:raise ValueError(mode)
            offers.append((value,row['task']['id'],i))
        _,_,chosen=max(offers)
        row=bank[chosen];task=row['task'];record=row['record'];matrix=row['matrix']
        if count[chosen]==0:
            j=record['first_probe']['top20_entropy']
            observed[chosen]=task['hidden'][j][1]
        else:
            j0=record['first_probe']['top20_entropy']
            matched={k for k in range(len(matrix)) if matrix[k][j0]==observed[chosen]}
            remaining=matched if matched else set(range(len(matrix)))
            j=choose_probe(task['id'],matrix,record['order'],record['scores'],
                           remaining,[j0],'top20_entropy')
        count[chosen]+=1
        trace.append({'step':step+1,'task_id':task['id'],'query_index':j,
                      'action_number':count[chosen]})
    assert sum(count)==8 and all(v<=2 for v in count)
    return {'correct':sum(r['correct'][count[i]] for i,r in enumerate(bank)),
            'actions':count,'trace':trace}


def static(bank,model):
    x=np.stack([initial_features(r) for r in bank])
    p1,p2=predict(model,x)
    actions=allocate(p1,p2,8)
    return sum(r['correct'][actions[i]] for i,r in enumerate(bank))


def main():
    if OUT.exists():raise RuntimeError('development output already exists')
    rows=load_rows()
    assert len(rows)==384
    seeds=sorted({r['seed'] for r in rows})
    banks=[]
    for seed in seeds:
        held=[r for r in rows if r['seed']==seed]
        source=[r for r in rows if r['seed']!=seed]
        assert len(held)==8
        models=train(source)
        conditional=simulate(held,models,'conditional')
        prior=simulate(held,models,'prior')
        one_each=sum(r['correct'][1] for r in held)
        banks.append({'seed':seed,'stream':held[0]['stream'],
                      'conditional':conditional['correct'],'prior':prior['correct'],
                      'static_ridge':static(held,models[0]),'one_each':one_each,
                      'conditional_actions':conditional['actions'],
                      'conditional_trace':conditional['trace']})
    names=('conditional','prior','static_ridge','one_each')
    summary={'scope':'inspected development only','tasks':len(rows),
             'banks':len(seeds),'calls_per_bank':8,
             'correct':{name:sum(b[name] for b in banks) for name in names},
             'by_bank':banks}
    write_json(OUT,summary)
    print(json.dumps({'tasks':summary['tasks'],'banks':summary['banks'],
                      'correct':summary['correct'],
                      'conditional_minus_static_by_bank':[
                          b['conditional']-b['static_ridge'] for b in banks]},indent=2))


if __name__=='__main__':main()
