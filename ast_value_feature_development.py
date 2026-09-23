"""Inspected-bank development of public AST query-value predictors.

All rows here have already been scored. No result from this file is confirmation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from rsi.common import ROOT, write_json
from ast_query_allocation_development import features, fit, predict, allocate, fixed


OUT = ROOT/'analysis/ast-value-feature-development.json'
SENSOR = ROOT/'runs/ast-probe-sensor-transfer-20260918'
QUERY = ROOT/'runs/ast-query-allocation-transfer-20260918'
MIXED = ROOT/'runs/full-mixed-ast-sensor-20260918'
INCREMENTAL = ROOT/'runs/incremental-ast-improver-20260918'


def load_rows():
    specs = [(SENSOR, 'sensor'), (QUERY, 'query'), (MIXED, 'mixed'),
             (INCREMENTAL/'admission', 'query'),
             (INCREMENTAL/'transfer', 'query')]
    result = []
    for path, kind in specs:
        tasks = json.loads((path/'sealed_bank.json').read_text())
        records = json.loads((path/('frozen_decisions.json' if kind == 'mixed'
                                    else 'frozen_records.json')).read_text())
        outcomes = json.loads((path/'results.json').read_text())['tasks']
        predicted = json.loads((path/'predicted_probe_outputs.json').read_text())
        if kind == 'mixed':
            tasks = [task for task in tasks if task['family'] == 'ast_transition']
            records = [record for record in records if 'order' in record]
            outcomes = [outcome for outcome in outcomes if outcome['family'] == 'ast_transition']
        assert all(a['id'] == b['id'] == c['id'] for a,b,c in zip(tasks,records,outcomes))
        for task, record, outcome in zip(tasks, records, outcomes):
            if kind == 'sensor':
                correct = outcome['correct']
                calls = [correct['baseline'], correct['top20_entropy_1'],
                         correct['top20_entropy_2']]
            elif kind == 'mixed':
                correct = outcome['correct']
                calls = [correct['ast_ranker'], correct['top20_one'], correct['top20_two']]
            else: calls = outcome['correct_by_calls']
            first = record['first_probe']
            if isinstance(first, dict): first = first['top20_entropy']
            record = {**record, 'first_probe': {'top20_entropy': first}}
            result.append({'task': task, 'record': record,
                           'matrix': predicted[task['id']],
                           'correct': [int(v) for v in calls],
                           'source': path.name, 'seed': task['seed'],
                           'stream': task.get('stream', 'mixed')})
    assert len(result) == 384 and len({r['task']['id'] for r in result}) == 384
    return result


def expanded(row):
    task, record, matrix = (row[name] for name in ('task', 'record', 'matrix'))
    basic = features(task, record, matrix)
    scores = np.asarray(record['scores'], dtype=float)
    order = record['order']; first = record['first_probe']['top20_entropy']
    std = max(float(scores.std()), .05)
    top = [order[:min(k,len(order))] for k in (10,20,50,100)]
    extra = [math.log1p(len(order)),
             *(float((scores[order[0]]-scores[order[min(k,len(order)-1)]])/std)
               for k in (2,5,10,20,50)),
             float((scores[order[0]]-scores.mean())/std),
             float((scores[order[0]]-scores[-1])/std)]
    for ids in top:
        for j in (first,):
            values = [matrix[i][j] for i in ids]
            counts = {}
            for v in values: counts[v] = counts.get(v,0)+1
            mass = np.asarray(list(counts.values()),dtype=float)/len(ids)
            extra.extend([len(counts)/len(ids),
                          1-counts[matrix[order[0]][j]]/len(ids),
                          float(-sum(p*math.log(p) for p in mass)),
                          float(max(mass))])
    for j in range(8):
        ids = top[1]
        values = [matrix[i][j] for i in ids]
        extra.append(1-sum(v == values[0] for v in values)/len(ids))
    for k in (20,100):
        ids = order[:min(k,len(order))]
        center = max(scores[i] for i in ids)
        for temp in (.25,1.,4.):
            weights = np.exp(np.clip((scores[ids]-center)/temp,-30,0))
            same = np.asarray([matrix[i][first] == matrix[order[0]][first]
                               for i in ids])
            extra.append(1-float(weights[same].sum()/weights.sum()))
    return np.r_[basic,extra]


def linear_fit(x,y1,y2,lam):
    return fit(x,y1,y2,lam)


def rbf_fit(x,y1,y2,lam,gamma):
    mean=x[:,1:].mean(axis=0); scale=np.maximum(x[:,1:].std(axis=0),.1)
    z=np.clip((x[:,1:]-mean)/scale,-5,5)
    d=((z[:,None,:]-z[None,:,:])**2).mean(axis=2)
    kernel=np.exp(-gamma*d)
    a1=np.linalg.solve(kernel+lam*np.eye(len(x)),y1)
    a2=np.linalg.solve(kernel+lam*np.eye(len(x)),y2)
    return mean,scale,z,a1,a2,gamma


def rbf_predict(model,x):
    mean,scale,z,a1,a2,gamma=model
    q=np.clip((x[:,1:]-mean)/scale,-5,5)
    d=((q[:,None,:]-z[None,:,:])**2).mean(axis=2)
    kernel=np.exp(-gamma*d)
    return kernel@a1,kernel@a2


def evaluate(rows, indexes, train_indexes, method, lam, gamma=None):
    x=np.stack([expanded(rows[i]) if method.startswith('expanded') else
                features(rows[i]['task'],rows[i]['record'],rows[i]['matrix'])
                for i in indexes])
    fit_x=np.stack([expanded(rows[i]) if method.startswith('expanded') else
                    features(rows[i]['task'],rows[i]['record'],rows[i]['matrix'])
                    for i in train_indexes])
    y1=np.asarray([rows[i]['correct'][1]-rows[i]['correct'][0]
                   for i in train_indexes],dtype=float)
    y2=np.asarray([rows[i]['correct'][2]-rows[i]['correct'][1]
                   for i in train_indexes],dtype=float)
    if method.endswith('rbf'):
        p1,p2=rbf_predict(rbf_fit(fit_x,y1,y2,lam,gamma),x)
    else:
        p1,p2=predict(linear_fit(fit_x,y1,y2,lam),x)
    return p1,p2


def cross_validate(rows, candidate):
    method,lam,gamma=candidate
    development=[i for i,r in enumerate(rows) if r['source'] != 'transfer']
    seeds=sorted({rows[i]['seed'] for i in development})
    banks=[]
    for seed in seeds:
        held=[i for i in development if rows[i]['seed']==seed]
        source=[i for i in development if rows[i]['seed']!=seed]
        assert len(held)==8
        p1,p2=evaluate(rows,held,source,method,lam,gamma)
        actions=allocate(p1,p2,8)
        ids=[rows[i]['task']['id'] for i in held]
        basic=np.stack([features(rows[i]['task'],rows[i]['record'],rows[i]['matrix'])
                        for i in held])
        controls={name:fixed(ids,basic,8,name) for name in
                  ('one_each','random','entropy','disagreement')}
        outcomes=np.asarray([rows[i]['correct'] for i in held])
        scores={'learned':int(sum(outcomes[i,a] for i,a in enumerate(actions)))}
        scores.update({name:int(sum(outcomes[i,a] for i,a in enumerate(control)))
                       for name,control in controls.items()})
        banks.append({'seed':seed,'stream':rows[held[0]]['stream'],
                      'correct':scores,'actions':actions})
    names=('learned','one_each','random','entropy','disagreement')
    return {'correct':{name:sum(bank['correct'][name] for bank in banks)
                       for name in names},'banks':banks}


def main():
    if OUT.exists(): raise RuntimeError('development already exists')
    rows=load_rows()
    candidates=[('basic_linear',l,None) for l in (1.,10.,100.)]
    candidates += [('expanded_linear',l,None) for l in (1.,10.,100.)]
    candidates += [('expanded_rbf',l,g) for l in (.1,1.,10.)
                   for g in (.05,.2,1.)]
    results={f'{m}:{l}:{g}':cross_validate(rows,(m,l,g)) for m,l,g in candidates}
    ranking=sorted(results,key=lambda key:(results[key]['correct']['learned'],key),reverse=True)
    chosen=ranking[0]
    output={'scope':'inspected development banks only','tasks':len(rows),
            'development_tasks':288,'validation_tasks':96,
            'candidates':{key:result['correct'] for key,result in results.items()},
            'chosen':chosen,'source_cv':results[chosen]}
    write_json(OUT,output)
    print(json.dumps({key:output[key] for key in ('tasks','development_tasks','validation_tasks','chosen','candidates')},indent=2))


if __name__=='__main__':main()
