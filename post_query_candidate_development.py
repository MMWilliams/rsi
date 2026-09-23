"""Opened-bank screen of sensor-conditioned ranking among surviving candidates."""
from __future__ import annotations

import hashlib
import json
import time

import joblib
import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from candidate_reranker_transfer import candidate_features,model_for
from cross_family_meta_improver_transfer import interval


SOURCE=(ROOT/'runs/candidate-reranker-transfer-20260918',
        ROOT/'runs/candidate-reranker-replication-20260918')
TARGET=(ROOT/'runs/shifted-ast-seed-transfer-20260918',
        ROOT/'runs/combined-ranker-query-transfer-20260918')
E0=ROOT/'runs/candidate-reranker-transfer-20260918/e0.joblib'
OUT=ROOT/'analysis/post-query-candidate-development-20260918.json'
MODELS=ROOT/'analysis/post-query-candidate-models-20260918'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_panel(path):
    assert json.loads((path/'audit.json').read_text())['passed']
    tasks=json.loads((path/'sealed_bank.json').read_text())
    base=json.loads((path/'base_pools.json').read_text())
    wide=json.loads((path/'ast_wide_pools.json').read_text())
    matrix=json.loads((path/'predicted_probe_outputs.json').read_text())
    records=json.loads((path/'frozen_records.json').read_text())
    return tasks,base,wide,matrix,records


def candidate_rows(task,pool,record,matrix,e0):
    old=record['orders']['old'];new=record['orders']['e0'];head=old[:20]
    base=candidate_features(task,pool,record['old_scores'],old)
    p=e0.predict_proba(base)[:,1]
    probe=record['probe'];truth=task['hidden'][probe][1]
    surviving={i for i in range(len(pool)) if matrix[i][probe]==truth}
    if not surviving:surviving=set(range(len(pool)))
    head_surviving=[(rank,index) for rank,index in enumerate(head) if index in surviving]
    e0_rank={index:rank for rank,index in enumerate(new)}
    scores=np.asarray(record['old_scores'],float);std=max(float(scores.std()),.05)
    best_surviving_score=max(scores[i] for i in surviving)
    group_fraction=len(head_surviving)/max(1,len(head))
    rows=[]
    for old_rank,index in head_surviving:
        agree=sum(matrix[index][j]==matrix[new[0]][j] for j in range(8))/8
        extra=np.asarray([float(p[old_rank]),e0_rank[index]/20,
            (scores[index]-best_surviving_score)/std,
            group_fraction,len(surviving)/len(pool),agree],np.float32)
        rows.append((index,base[old_rank],np.r_[base[old_rank],extra]))
    return rows,surviving


def source_arrays(e0):
    plain=[];sensor=[];labels=[];counts=[]
    for path in SOURCE:
        tasks,base,wide,matrices,records=load_panel(path)
        count=0
        for task,record in zip(tasks,records):
            key=task['id'];pool=wide.get(key,base[key])
            rows,_=candidate_rows(task,pool,record,matrices[key],e0)
            for index,p,s in rows:
                plain.append(p);sensor.append(s)
                labels.append(int(bool(evaluate_program(pool[index]['program'],
                                                        task['hidden'][8:]))))
                count+=1
        counts.append({'panel':path.name,'candidate_labels':count})
    x=np.asarray(plain,np.float32);z=np.asarray(sensor,np.float32)
    y=np.asarray(labels,np.int8)
    assert len(x)==len(z)==len(y)
    return x,z,y,counts


def call_ids(path):
    if 'shifted-ast' in path.name:
        frozen=json.loads((path/'frozen_allocations.json').read_text())
        return {seed:set(row['cheap']) for seed,row in frozen.items()}
    frozen=json.loads((path/'combined_children.json').read_text())
    return {seed:set(ids) for seed,ids in
            frozen['children']['e0_full']['calls'].items()}


def target_scores(path,e0,models):
    tasks,base,wide,matrices,records=load_panel(path)
    calls=call_ids(path);rows=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key])
        candidates,surviving=candidate_rows(task,pool,record,matrices[key],e0)
        baseline=next(i for i in record['orders']['e0'] if i in surviving)
        choices={'e0':baseline}
        for name,model in models.items():
            if not candidates:choices[name]=baseline;continue
            x=np.asarray([row[1 if name=='plain' else 2]
                          for row in candidates],np.float32)
            p=model.predict_proba(x)[:,1]
            chosen=max(range(len(candidates)),key=lambda j:(float(p[j]),-j))
            choices[name]=candidates[chosen][0]
        outcome={}
        for name,index in choices.items():
            outcome[name]=int(bool(evaluate_program(pool[index]['program'],
                                                    task['hidden'][8:])))
            checked+=1
        assert all(i in surviving for i in choices.values())
        rows.append({'id':key,'seed':task['seed'],'queried':outcome,
                     'zero_e0':int(bool(evaluate_program(
                         pool[record['orders']['e0'][0]]['program'],
                         task['hidden'][8:]))),
                     'top20_survivors':len(candidates)})
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed];chosen=calls[str(seed)]
        entry={'seed':seed}
        for name in ('e0',)+tuple(models):
            entry[name]={'one_each':sum(r['queried'][name] for r in group),
                'budgeted':sum(r['queried'][name] if r['id'] in chosen
                                else r['zero_e0'] for r in group)}
        banks.append(entry)
    totals={name:{field:sum(b[name][field] for b in banks)
                  for field in ('one_each','budgeted')}
            for name in ('e0',)+tuple(models)}
    comparisons={}
    for name in models:
        comparisons[name]={}
        for field in ('one_each','budgeted'):
            diffs=[b[name][field]-b['e0'][field] for b in banks]
            comparisons[name][field]={'gain':sum(diffs),
                'positive_banks':sum(x>0 for x in diffs),
                'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    return {'tasks':len(rows),'candidate_choices_checked':checked,
        'totals':totals,'comparisons':comparisons,'by_bank':banks,
        'tasks_with_no_top20_survivor':sum(r['top20_survivors']==0 for r in rows)}


def main():
    if OUT.exists() or MODELS.exists():raise RuntimeError('development output exists')
    start=time.perf_counter();e0=joblib.load(E0)
    x,z,y,counts=source_arrays(e0)
    models={'plain':model_for(15).fit(x,y),
            'sensor':model_for(15).fit(z,y)}
    MODELS.mkdir(parents=True)
    for name,model in models.items():joblib.dump(model,MODELS/f'{name}.joblib',compress=3)
    targets={path.name:target_scores(path,e0,models) for path in TARGET}
    result={'scope':'opened development; source tasks disjoint from E0 candidate training',
        'source_tasks':1152,'source_candidate_labels':len(y),
        'source_positive_labels':int(y.sum()),'source_panels':counts,
        'model_sha256':{name:sha(MODELS/f'{name}.joblib') for name in models},
        'targets':targets,'wall_seconds':time.perf_counter()-start}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='targets'} |
        {'targets':{name:{k:v for k,v in target.items() if k!='by_bank'}
                    for name,target in targets.items()}},indent=2))


if __name__=='__main__':main()
