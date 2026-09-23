"""Opened disjoint-source query learning for top-50 candidate reranking."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import public_block
from candidate_query_cost_transfer import cheap_public_features
from wide_candidate_reranker_development import features,order_for,load_panel,MODELS
from cross_family_meta_improver_development import fit_method,values
from cross_family_meta_improver_transfer import interval


SOURCE=(ROOT/'runs/candidate-conditioned-query-transfer-20260918',
        ROOT/'runs/candidate-query-cost-transfer-20260918')
TARGET=(ROOT/'runs/shifted-ast-seed-transfer-20260918',
        ROOT/'runs/combined-ranker-query-transfer-20260918')
OUT=ROOT/'analysis/wide-ranker-query-development-20260918.json'
NAMES=('e0','top20_same','top50')


def panel_rows(path,models):
    tasks,base,wide,records,predicted=load_panel(path)
    result=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        old=record['orders']['old'];x=features(task,pool,record,min(50,len(pool)))
        probe=record['probe'];truth=task['hidden'][probe][1]
        surviving={i for i in range(len(pool)) if matrix[i][probe]==truth}
        if not surviving:surviving=set(range(len(pool)))
        orders={'e0':record['orders']['e0'],
            'top20_same':order_for(models['top20_same'],x,old,20),
            'top50':order_for(models['top50'],x,old,50)}
        row={'id':key,'seed':task['seed'],'public_block':public_block(task)}
        for name,order in orders.items():
            altered={**record,'orders':{**record['orders'],'e0':order}}
            vector=cheap_public_features(altered,matrix)
            first=order[0];post=next(i for i in order if i in surviving)
            zero=int(bool(evaluate_program(pool[first]['program'],
                                           task['hidden'][8:])))
            one=int(bool(evaluate_program(pool[post]['program'],
                                          task['hidden'][8:])))
            checked+=2
            row[name]={'features':vector,'zero':zero,'one':one,
                       'gain':one-zero}
        result.append(row)
    return result,checked


def model_rows(rows,name):
    return [{'id':r['id'],'seed':r['seed'],'public_block':r['public_block'],
             **r[name]} for r in rows]


def score_target(rows,models,budget):
    predictions={name:values(models[name],model_rows(rows,name)) for name in NAMES}
    lookup={name:{r['id']:float(v) for r,v in zip(rows,predictions[name])}
            for name in NAMES}
    by_seed=defaultdict(list)
    for row in rows:by_seed[row['seed']].append(row)
    banks=[]
    for seed in sorted(by_seed):
        group=by_seed[seed];assert len(group) in (8,48)
        entry={'seed':seed}
        for name in NAMES:
            order=sorted(group,key=lambda r:(lookup[name][r['id']],r['id']),
                         reverse=True)
            selected={r['id'] for r in order[:budget]}
            entry[name]={'zero':sum(r[name]['zero'] for r in group),
                'budgeted':sum(r[name]['one'] if r['id'] in selected
                               else r[name]['zero'] for r in group),
                'one_each':sum(r[name]['one'] for r in group),
                'hindsight':sum(r[name]['zero'] for r in group)+
                    sum(sorted((r[name]['gain'] for r in group),reverse=True)[:budget])}
        banks.append(entry)
    totals={name:{field:sum(b[name][field] for b in banks) for field in
        ('zero','budgeted','one_each','hindsight')} for name in NAMES}
    comparisons={}
    for name in ('top20_same','top50'):
        diffs=[b[name]['budgeted']-b['e0']['budgeted'] for b in banks]
        comparisons[name]={'gain':sum(diffs),'positive_banks':sum(x>0 for x in diffs),
            'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    return {'tasks':len(rows),'budget_per_bank':budget,
        'totals':totals,'comparisons':comparisons,'by_bank':banks}


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    assert json.loads((ROOT/'analysis/wide-candidate-reranker-development-20260918.json').read_text())['source_tasks']==1152
    models={name:joblib.load(MODELS/f'{name}.joblib')
            for name in ('top20_same','top50')}
    source=[];checked=0
    for path in SOURCE:
        rows,count=panel_rows(path,models);source.extend(rows);checked+=count
    assert len(source)==1152
    query_models={name:fit_method(model_rows(source,name),'interaction_100')
                  for name in NAMES}
    targets={}
    for path in TARGET:
        rows,count=panel_rows(path,models)
        budget=4 if len(rows)==96 else 8
        targets[path.name]={**score_target(rows,query_models,budget),
                            'candidate_choices_checked':count}
    result={'scope':'opened development; candidate models and query source disjoint',
        'candidate_model_source_tasks':1152,
        'query_model_source_tasks':len(source),
        'query_source_candidate_choices_checked':checked,
        'targets':targets}
    write_json(OUT,result)
    print(json.dumps({'scope':result['scope'],
        'candidate_model_source_tasks':1152,'query_model_source_tasks':len(source),
        'targets':{name:{k:v for k,v in target.items() if k!='by_bank'}
                   for name,target in targets.items()}},indent=2))


if __name__=='__main__':main()
