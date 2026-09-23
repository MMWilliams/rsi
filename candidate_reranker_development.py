"""Opened-bank top-20 candidate correctness reranker development.

Only public task examples, candidate programs, existing scores and public block
are features. Final labels are exact-oracle targets, never inference features.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES
from gated_ast_feedback import public_block
from ast_evaluator_feedback import features as structural_features


OUT=ROOT/'analysis/candidate-reranker-development-20260918.json'
CACHE=ROOT/'analysis/candidate-reranker-top20-cache-20260918'
META=ROOT/'runs/cross-family-meta-improver-transfer-20260918'
FOCUSED=ROOT/'runs/focused-feedback-transfer-20260918'
PAIR=ROOT/'runs/pairwise-query-transfer-20260918'
BLOCKS=(0x700,0x800,0x900,0xa00,0xc00,0xd00)
K=20


def panel_path(name):
    if name.startswith('meta_'):return META/name.split('_',1)[1]
    return {'focused':FOCUSED,'pairwise':PAIR}[name]


def extract(name):
    directory=panel_path(name)
    target=CACHE/f'{name}.npz';manifest=CACHE/f'{name}.json'
    if target.exists() or manifest.exists():raise RuntimeError(f'{name} cache exists')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    x=[];y=[];meta=[];top20_reachable=0
    for task,record in zip(tasks,records):
        key=task['id'];assert key==record['id']
        pool=wide.get(key,base[key]);scores=np.asarray(record['scores'],float)
        order=record['order'][:K]
        subset=[pool[i] for i in order]
        structure=np.asarray(structural_features(task,subset),np.float32)
        assert structure.shape==(len(subset),175)
        std=max(float(scores.std()),.05);top=float(scores[order[0]])
        rows=[];labels=[]
        for rank,index in enumerate(order):
            block=np.asarray([float(public_block(task)==b) for b in BLOCKS],np.float32)
            extra=np.asarray([(scores[index]-top)/std,rank/K,
                              np.log1p(len(pool))/8.],np.float32)
            rows.append(np.r_[structure[rank],extra,block])
            labels.append(int(bool(evaluate_program(pool[index]['program'],
                                                    task['hidden'][8:]))))
        x.extend(rows);y.extend(labels)
        top20_reachable+=any(labels)
        # Final labels remain outside model features.
        meta.append({'id':key,'seed':task['seed'],'family':task['family'],
                     'candidate_count':len(subset),
                     'baseline_correct':labels[0],
                     'top20_reachable':int(any(labels))})
    assert len(x)==sum(r['candidate_count'] for r in meta) and len(y)==len(x)
    CACHE.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(target,x=np.asarray(x,np.float32),y=np.asarray(y,np.int8))
    hashes={filename:hashlib.sha256((directory/filename).read_bytes()).hexdigest()
            for filename in ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
                             'frozen_records.json','results.json')}
    write_json(manifest,{'scope':'opened-bank candidate labels; research-only cache',
                         'panel':name,'tasks':len(tasks),'top_k':K,
                         'candidate_labels_checked':len(y),
                         'baseline_correct':sum(r['baseline_correct'] for r in meta),
                         'top20_reachable':top20_reachable,
                         'source_sha256':hashes,'tasks_detail':meta})
    print(json.dumps({'panel':name,'tasks':len(tasks),'labels':len(y),
                      'baseline':sum(r['baseline_correct'] for r in meta),
                      'top20_reachable':top20_reachable},indent=2))


def load(name):
    raw=np.load(CACHE/f'{name}.npz');manifest=json.loads((CACHE/f'{name}.json').read_text())
    x=raw['x'];y=raw['y']
    assert len(y)==sum(r['candidate_count'] for r in manifest['tasks_detail'])
    return x,y,manifest['tasks_detail']


def evaluate(model,name):
    x,y,meta=load(name);scores=model.predict_proba(x)[:,1]
    selected=[];choices=[];offset=0
    for row in meta:
        count=row['candidate_count'];local=scores[offset:offset+count]
        choice=int(np.argmax(local+np.linspace(1e-12,0,count)))
        selected.append(int(y[offset+choice]));choices.append(choice)
        offset+=count
    assert offset==len(y)
    by_bank={}
    for i,row in enumerate(meta):
        bank=by_bank.setdefault(row['seed'],{'baseline':0,'reranked':0,
                                             'top20_reachable':0})
        bank['baseline']+=row['baseline_correct']
        bank['reranked']+=selected[i]
        bank['top20_reachable']+=row['top20_reachable']
    return {'tasks':len(meta),'baseline':sum(r['baseline_correct'] for r in meta),
            'reranked':sum(selected),
            'top20_reachable':sum(r['top20_reachable'] for r in meta),
            'changed_choices':sum(choice!=0 for choice in choices),
            'by_bank':[{'seed':seed,**bank} for seed,bank in sorted(by_bank.items())]}


def train_and_evaluate(train_panels,test_panels):
    tables=[load(name) for name in train_panels]
    x=np.concatenate([v[0] for v in tables]);y=np.concatenate([v[1] for v in tables])
    models={'logistic_c0.1':make_pipeline(StandardScaler(),LogisticRegression(
                C=.1,max_iter=1000,random_state=0)),
            'logistic_c1':make_pipeline(StandardScaler(),LogisticRegression(
                C=1.,max_iter=1000,random_state=0)),
            'hgb_leaf7':HistGradientBoostingClassifier(max_leaf_nodes=7,
                min_samples_leaf=80,learning_rate=.05,max_iter=100,
                l2_regularization=1.,random_state=0),
            'hgb_leaf15':HistGradientBoostingClassifier(max_leaf_nodes=15,
                min_samples_leaf=80,learning_rate=.05,max_iter=100,
                l2_regularization=1.,random_state=0)}
    results={}
    for name,model in models.items():
        model.fit(x,y)
        results[name]={panel:evaluate(model,panel) for panel in test_panels}
    return {'train_panels':train_panels,'train_candidates':len(y),
            'positive_candidate_labels':int(y.sum()),'results':results}


def screen():
    if OUT.exists():raise RuntimeError('screen already exists')
    first=train_and_evaluate(('meta_admission','meta_a'),('meta_b',))
    second=train_and_evaluate(('meta_admission','meta_a','meta_b'),
                              ('focused','pairwise'))
    result={'scope':'all test panels previously opened; development screen only',
            'first':first,'second':second,
            'feature_contract':'175 public structural features; old ranker score gap, rank, pool size, public mechanism block',
            'limits':['Only old top-20 candidates are rescored; reachability outside top-20 cannot improve.',
                      'Source and evaluation labels come from an exact research oracle and incur candidate work.',
                      'The models were screened after the target panels had already been opened.']}
    write_json(OUT,result)
    print(json.dumps({stage:{model:{panel:{key:score[key] for key in
        ('baseline','reranked','top20_reachable','changed_choices')}
        for panel,score in panels.items()} for model,panels in data['results'].items()}
        for stage,data in (('first',first),('second',second))},indent=2))


if __name__=='__main__':
    if sys.argv[1]=='extract':extract(sys.argv[2])
    elif sys.argv[1]=='screen':screen()
    else:raise ValueError(sys.argv[1])
