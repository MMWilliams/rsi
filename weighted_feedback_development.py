"""Opened-bank screen for weighted verified-feedback batches."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from feedback_batch_history_development import all_rows,score_panel
from cross_family_meta_improver_development import matrix
from cross_family_meta_improver_transfer import interval


OUT=ROOT/'analysis/weighted-feedback-development-20260918.json'
LAM=100.
WEIGHTS={'first2_only':(0.,0.),'all_equal':(1.,1.),
         'downweight_third_half':(.5,1.),
         'downweight_third_quarter':(.25,1.),
         'skip_third':(0.,1.),
         'downweight_fourth_half':(1.,.5),
         'both_half':(.5,.5)}


def fit(rows,weights):
    x=matrix(rows,'interaction')
    y=np.asarray([r['gain'] for r in rows],float)
    w=np.asarray(weights,float)
    assert np.any(w>0)
    mean=np.average(x[:,1:],axis=0,weights=w)
    scale=np.maximum(np.sqrt(np.average((x[:,1:]-mean)**2,axis=0,weights=w)),.05)
    z=np.c_[np.ones(len(x)),(x[:,1:]-mean)/scale]
    penalty=np.eye(z.shape[1]);penalty[0,0]=0
    beta=np.linalg.solve(z.T@(w[:,None]*z)+LAM*penalty,z.T@(w*y))
    return mean,scale,beta


def predict(model,rows):
    mean,scale,beta=model
    x=matrix(rows,'interaction')
    z=np.c_[np.ones(len(x)),(x[:,1:]-mean)/scale]
    return z@beta


def sample_weights(rows,third,fourth):
    return [1. if r['seed']<902534 else
            third if r['seed']<902546 else fourth for r in rows]


def bank_score(rows,p):
    assert len(rows)==48
    order=sorted(range(len(rows)),key=lambda i:(float(p[i]),rows[i]['id']),
                 reverse=True)
    ids={rows[i]['id'] for i in order[:8]}
    return sum(r['one'] if r['id'] in ids else r['zero'] for r in rows)


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows=all_rows();source=rows[:2304];target=rows[2304:]
    seeds=sorted({r['seed'] for r in source});assert len(seeds)==48
    cv=[]
    for seed in seeds:
        train=[r for r in source if r['seed']!=seed]
        held=[r for r in source if r['seed']==seed]
        entry={'seed':seed}
        for name,(third,fourth) in WEIGHTS.items():
            model=fit(train,sample_weights(train,third,fourth))
            entry[name]=bank_score(held,predict(model,held))
        cv.append(entry)
    opened={}
    for name,(third,fourth) in WEIGHTS.items():
        model=fit(source,sample_weights(source,third,fourth))
        opened[name]=score_panel(target,predict(model,target))
    totals={name:sum(r[name] for r in cv) for name in WEIGHTS}
    comparisons={name:{'gain_vs_equal':totals[name]-totals['all_equal'],
        'interval':interval([r[name]-r['all_equal'] for r in cv])}
        for name in WEIGHTS if name!='all_equal'}
    result={'scope':'opened development only; weighting rule needs fresh transfer',
        'source_tasks':len(source),'opened_validation_tasks':len(target),
        'weights':WEIGHTS,'cv_totals':totals,'cv_comparisons':comparisons,
        'opened_fifth':{name:{'correct':v['correct'],'mse':v['mse']}
                         for name,v in opened.items()},'cv_by_bank':cv}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='cv_by_bank'},indent=2))


if __name__=='__main__':main()
