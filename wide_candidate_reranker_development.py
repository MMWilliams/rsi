"""Opened-bank screen of a top-50 candidate evaluator with exact labels."""
from __future__ import annotations

import hashlib
import json
import time

import joblib
import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import public_block
from ast_evaluator_feedback import features as structural_features
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval


SOURCE=(ROOT/'runs/candidate-reranker-transfer-20260918',
        ROOT/'runs/candidate-reranker-replication-20260918')
TARGET=(ROOT/'runs/shifted-ast-seed-transfer-20260918',
        ROOT/'runs/combined-ranker-query-transfer-20260918')
OUT=ROOT/'analysis/wide-candidate-reranker-development-20260918.json'
MODELS=ROOT/'analysis/wide-candidate-reranker-models-20260918'
BLOCKS=(0x700,0x800,0x900,0xa00,0xc00,0xd00)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def features(task,pool,record,width):
    old=record['orders']['old'];head=old[:width]
    scores=np.asarray(record['old_scores'],float)
    structural=np.asarray(structural_features(task,[pool[i] for i in head]),
                          np.float32)
    assert structural.shape==(len(head),175)
    std=max(float(scores.std()),.05);top=float(scores[old[0]])
    block=np.asarray([float(public_block(task)==b) for b in BLOCKS],np.float32)
    x=[]
    for rank,index in enumerate(head):
        extra=np.asarray([(scores[index]-top)/std,rank/20,
                          np.log1p(len(pool))/8.],np.float32)
        x.append(np.r_[structural[rank],extra,block])
    return np.asarray(x,np.float32)


def load_panel(path):
    assert json.loads((path/'audit.json').read_text())['passed']
    tasks=json.loads((path/'sealed_bank.json').read_text())
    base=json.loads((path/'base_pools.json').read_text())
    wide=json.loads((path/'ast_wide_pools.json').read_text())
    records=json.loads((path/'frozen_records.json').read_text())
    predicted=json.loads((path/'predicted_probe_outputs.json').read_text())
    return tasks,base,wide,records,predicted


def source_arrays():
    xs=[];ys=[];meta=[];top20=[];labels_checked=0
    for path in SOURCE:
        tasks,base,wide,records,_=load_panel(path)
        for task,record in zip(tasks,records):
            key=task['id'];pool=wide.get(key,base[key]);n=min(50,len(pool))
            x=features(task,pool,record,n)
            indices=record['orders']['old'][:n]
            y=np.asarray([int(bool(evaluate_program(pool[i]['program'],
                task['hidden'][8:]))) for i in indices],np.int8)
            labels_checked+=len(y)
            xs.append(x);ys.append(y)
            top20.extend(range(len(meta),len(meta)+min(20,n)))
            meta.extend([{'id':key,'old_rank':i} for i in range(n)])
    x=np.concatenate(xs);y=np.concatenate(ys)
    assert len(x)==len(y)==len(meta)==labels_checked
    return x,y,np.asarray(top20,int),labels_checked


def order_for(model,x,old,width):
    n=min(width,len(old));p=model.predict_proba(x[:n])[:,1]
    indices=sorted(range(n),key=lambda i:(-float(p[i]),i))
    return [old[i] for i in indices]+old[n:]


def target_scores(path,models):
    tasks,base,wide,records,predicted=load_panel(path)
    by_bank={};rows=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);old=record['orders']['old']
        x=features(task,pool,record,min(50,len(pool)))
        matrix=predicted[key];probe=record['probe'];truth=task['hidden'][probe][1]
        surviving={i for i in range(len(pool)) if matrix[i][probe]==truth}
        if not surviving:surviving=set(range(len(pool)))
        row={'id':key,'seed':task['seed'],'outcomes':{}}
        orders={'e0':record['orders']['e0'],
            'top20_same':order_for(models['top20_same'],x,old,20),
            'top50':order_for(models['top50'],x,old,50)}
        for name,order in orders.items():
            first=order[0];post=next(i for i in order if i in surviving)
            zero=int(bool(evaluate_program(pool[first]['program'],
                                           task['hidden'][8:])))
            one=int(bool(evaluate_program(pool[post]['program'],
                                          task['hidden'][8:])))
            checked+=2
            row['outcomes'][name]={'zero':zero,'one':one}
        rows.append(row)
    names=tuple(models)+('e0',)
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        by_bank[str(seed)]={name:{field:sum(r['outcomes'][name][field]
                    for r in group) for field in ('zero','one')}
                    for name in names}
    totals={name:{field:sum(bank[name][field] for bank in by_bank.values())
                   for field in ('zero','one')} for name in names}
    comparisons={}
    for name in models:
        comparisons[name]={}
        for field in ('zero','one'):
            diffs=[bank[name][field]-bank['e0'][field]
                   for bank in by_bank.values()]
            comparisons[name][field]={'gain':sum(diffs),
                'positive_banks':sum(x>0 for x in diffs),
                'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    return {'tasks':len(tasks),'candidate_choices_checked':checked,
            'totals':totals,'comparisons':comparisons,'by_bank':by_bank}


def main():
    if OUT.exists() or MODELS.exists():raise RuntimeError('development output exists')
    start=time.perf_counter();x,y,top20,count=source_arrays()
    models={'top20_same':model_for(15).fit(x[top20],y[top20]),
            'top50':model_for(15).fit(x,y)}
    MODELS.mkdir(parents=True)
    for name,model in models.items():joblib.dump(model,MODELS/f'{name}.joblib',compress=3)
    targets={path.name:target_scores(path,models) for path in TARGET}
    result={'scope':'opened development only; target labels were previously opened',
        'source_tasks':1152,'source_candidate_labels':count,
        'source_top20_labels':len(top20),
        'source_positive_top50':int(y.sum()),
        'source_positive_top20':int(y[top20].sum()),
        'model_sha256':{name:sha(MODELS/f'{name}.joblib') for name in models},
        'targets':targets,'wall_seconds':time.perf_counter()-start}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='targets'} |
        {'targets':{name:{k:v for k,v in target.items() if k!='by_bank'}
                    for name,target in targets.items()}},indent=2))


if __name__=='__main__':main()
