"""Freeze an incrementally updated query-value evaluator and controls."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from rsi.common import ROOT, write_json


FIRST = ROOT/'analysis/sharp-query-value-development.json'
SECOND_PLAN = ROOT/'runs/sharp-query-value-transfer-20260917/frozen_plans.json'
SECOND_FEEDBACK = ROOT/'analysis/sharp-residual-diagnostic.json'
OUT = ROOT/'analysis/sharp-query-feedback-updated.json'
RIDGE = 10.
SEED = 902800


def fit(rows):
    x = np.asarray([row['features'] for row in rows], dtype=float)
    y = np.asarray([row['gain'] for row in rows], dtype=float)
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), .1)
    z = np.c_[(x-mean)/scale, np.ones(len(x))]
    penalty = np.diag([RIDGE]*x.shape[1]+[0.])
    weights = np.linalg.solve(z.T@z + penalty, z.T@y)
    return {'mean':mean.tolist(),'scale':scale.tolist(),'weights':weights.tolist(),
            'rows':len(rows),'positive_gains':int(sum(y>0))}


def predict(model, rows):
    x = np.asarray([row['features'] for row in rows], dtype=float)
    mean = np.asarray(model['mean']);scale=np.asarray(model['scale'])
    weights=np.asarray(model['weights'])
    return np.c_[(x-mean)/scale,np.ones(len(x))]@weights


def main():
    if OUT.exists():
        raise RuntimeError('updated evaluator already frozen')
    raw = {'first':FIRST.read_bytes(), 'second_plan':SECOND_PLAN.read_bytes(),
           'second_feedback':SECOND_FEEDBACK.read_bytes()}
    first = json.loads(raw['first'])['tasks']
    plans = json.loads(raw['second_plan'])
    feedback = json.loads(raw['second_feedback'])['tasks']
    assert len(first)==len(plans)==len(feedback)==192
    second = []
    for plan,row in zip(plans,feedback):
        assert plan['id']==row['id']
        second.append({'id':row['id'],'seed':row['seed'],'family':row['family'],
                       'features':plan['features'],'gain':row['entropy_gain'],
                       'before':row['baseline']})
    rows = first + second
    updated=fit(rows)
    rng=np.random.default_rng(SEED)
    scrambled=[]
    for seed in sorted({row['seed'] for row in second}):
        group=[row.copy() for row in second if row['seed']==seed]
        gains=[row['gain'] for row in group]
        rng.shuffle(gains)
        for row,gain in zip(group,gains):
            row['gain']=gain
        scrambled.extend(group)
    scramble_model=fit(first+scrambled)
    duplicated=fit(first+first)
    oof=np.empty(len(rows),dtype=float)
    for seed in sorted({row['seed'] for row in rows}):
        train=[row for row in rows if row['seed']!=seed]
        test=[row for row in rows if row['seed']==seed]
        indices=[i for i,row in enumerate(rows) if row['seed']==seed]
        oof[indices]=predict(fit(train),test)
    panels={}
    for name,left,right in (('first',0,192),('second',192,384)):
        panel=rows[left:right]
        predicted=oof[left:right]
        chosen=set(np.argsort(-predicted,kind='stable')[:95].tolist())
        panels[name]={'correct':int(sum(row['before']+(row['gain'] if i in chosen else 0)
                                        for i,row in enumerate(panel))),
                      'no_query':int(sum(row['before'] for row in panel)),
                      'queries':95,
                      'by_family':{family:int(sum(row['before']+(row['gain'] if i in chosen else 0)
                                                for i,row in enumerate(panel) if row['family']==family))
                                   for family in sorted({row['family'] for row in panel})}}
    summary={'scope':'development only; prior and new bank feedback now inspected',
             'first_tasks':len(first),'new_feedback_tasks':len(second),
             'first_positive_gains':sum(row['gain']>0 for row in first),
             'new_positive_gains':sum(row['gain']>0 for row in second),
             'ridge':RIDGE,'oof_panels':panels,
             'model_rows':{name:model['rows'] for name,model in
                           [('updated',updated),('scrambled',scramble_model),
                            ('duplicated_prior',duplicated)]}}
    write_json(OUT,{'summary':summary,
                    'source_sha256':{name:hashlib.sha256(value).hexdigest()
                                     for name,value in raw.items()},
                    'models':{'updated':updated,'scrambled':scramble_model,
                              'duplicated_prior':duplicated}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
