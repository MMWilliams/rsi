"""Development-only second-query allocation using inspected active probe banks."""
import hashlib
import json
import math
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from active_probe_diagnostic import choose_probe


SOURCE=ROOT/'runs/active-evaluator-transfer-20260917'


def signals(task,record):
    n=record['n']; order=record['ranking']; scores=np.asarray(record['scores'])
    outputs=record['predicted_probe_outputs']; j=record['choices']['weighted_first']
    truth=task['first_output']
    survivors=[i for i in range(n) if outputs[i][j]==truth]
    if not survivors: survivors=list(range(n))
    top=next(i for i in order if i in set(survivors))
    k=choose_probe(task['id'],outputs,survivors,[j],scores,'weighted_entropy')
    groups=defaultdict(list)
    for i in survivors: groups[outputs[i][k]].append(i)
    raw=scores[survivors]; weight=np.exp((raw-raw.max())/.1);weight/=weight.sum()
    weight_by_id=dict(zip(survivors,weight))
    mass=[sum(weight_by_id[i] for i in group) for group in groups.values()]
    maxmass=max(mass)
    entropy=-sum(p*math.log(p) for p in mass if p>0)
    best_group=groups[outputs[top][k]]
    ordered=[i for i in order if i in set(survivors)]
    gap=float(scores[ordered[0]]-scores[ordered[1]]) if len(ordered)>1 else 1.
    selected_first=top
    return {'id':task['id'],'seed':task['seed'],'n':n,'first_choice':selected_first,
            'features':[len(survivors)/n,math.log1p(len(survivors))/5,
                        float(order[0] not in survivors),
                        len(groups)/max(1,len(survivors)),1-maxmass,entropy,
                        1-len(best_group)/max(1,len(survivors)),
                        float(min(max(gap,-1),1)),
                        float(np.std(raw)) if len(raw)>1 else 0.,
                        float(record['choices']['weighted_first']==record['choices']['minimax']),
                        1.],
            'second_probe':k}


def fit(rows):
    x=np.asarray([r['features'] for r in rows],dtype=float)
    y=np.asarray([r['delta'] for r in rows],dtype=float)
    scale=np.maximum(x[:,:-1].std(axis=0),.05)
    z=np.column_stack((x[:,:-1]/scale,np.ones(len(x))))
    penalty=np.eye(z.shape[1])*10;penalty[-1,-1]=0
    w=np.linalg.solve(z.T@z+penalty,z.T@y)
    return scale,w


def rank(row,method,model=None):
    f=row['features'];
    if method=='learned':
        scale,w=model
        return float(np.r_[np.asarray(f[:-1])/scale,1.]@w)
    if method=='survivors': return f[0]
    if method=='entropy': return f[5]
    if method=='top_disagreement': return f[6]
    if method=='random':
        return int.from_bytes(hashlib.sha256((row['id']+':second').encode()).digest()[:8],
                              'little')/2**64
    raise KeyError(method)


def main():
    tasks=json.loads((SOURCE/'sealed_bank.json').read_text(encoding='utf-8'))
    records=json.loads((SOURCE/'frozen_decisions.json').read_text(encoding='utf-8'))
    outcomes=json.loads((SOURCE/'results.json').read_text(encoding='utf-8'))['tasks']
    pools=json.loads((SOURCE/'candidate_pools.json').read_text(encoding='utf-8'))
    from rsi.semantic_invention import evaluate_program
    rows=[]
    for task,record,outcome in zip(tasks,records,outcomes):
        j=record['choices']['weighted_first']
        row=signals({'id':task['id'],'seed':task['seed'],
                     'first_output':task['probe_outputs'][j]},record)
        assert row['second_probe']==outcome['query_choices']['weighted_second']
        row['second_correct']=bool(outcome['correct']['weighted_two'])
        first=evaluate_program(pools[task['id']][row['first_choice']]['program'],task['final'])
        row['first_correct']=bool(first)
        row['delta']=int(row['second_correct'])-int(first)
        rows.append(row)
    seeds=sorted(set(r['seed'] for r in rows))
    methods=('learned','survivors','entropy','top_disagreement','random')
    folds=[]
    for seed in seeds:
        train=[r for r in rows if r['seed']!=seed]
        test=[r for r in rows if r['seed']==seed]
        model=fit(train)
        budget=len(test)//2
        scores={}
        for method in methods:
            ranked=sorted(test,key=lambda r:(-rank(r,method,model),r['id']))[:budget]
            scores[method]=sum(r['first_correct'] for r in test)+sum(r['delta'] for r in ranked)
        oracle=sum(r['first_correct'] for r in test)+sum(
            sorted((r['delta'] for r in test),reverse=True)[:budget])
        folds.append({'seed':seed,'n':len(test),'extra_queries':budget,
                      'one_query':sum(r['first_correct'] for r in test),
                      'all_two_query':sum(r['second_correct'] for r in test),
                      'oracle_budget_upper':oracle,'methods':scores,
                      'model':{'scale':model[0].tolist(),'weights':model[1].tolist()}})
    summary={'scope':'development only; inspected banks; leave-one-bank-out',
             'tasks':len(rows),'first_queries':len(rows),
             'additional_queries':sum(f['extra_queries'] for f in folds),
             'one_query':sum(f['one_query'] for f in folds),
             'all_two_query':sum(f['all_two_query'] for f in folds),
             'oracle_budget_upper':sum(f['oracle_budget_upper'] for f in folds),
             'negative_second_effects':sum(r['delta']<0 for r in rows),
             'positive_second_effects':sum(r['delta']>0 for r in rows),
             'methods':{m:sum(f['methods'][m] for f in folds) for m in methods}}
    write_json(ROOT/'analysis/sequential-budget-development.json',
               {'summary':summary,'folds':folds,'tasks':rows})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
