"""Fresh fixed-pool transfer of a learned classifier/pairwise evaluator router."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import representation
from mixed_probe_diagnostic import pool,bool_safe_structure
from mixed_evaluator_transfer import choose
from evaluator_router_development import features
import seed_growth


ROUTER=ROOT/'analysis/evaluator-router-frozen.json'
COMPONENTS=ROOT/'analysis/pairwise-evaluator-development.json'
DEST=ROOT/'runs/evaluator-router-transfer-20260917'
SEEDS=tuple(range(902216,902222))
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
PER_BANK=32
A='E192_classification';B='pairwise_random';C='combined_pairwise_random'


def choices(task,rows,models,router):
    if not rows:
        return {'id':task['id'],'seed':task['seed'],'family':task['family'],
                'pool_sha256':digest(rows),'selected':{name:None for name in
                  (A,B,C,'learned_router','higher_margin','random_router')},
                'scores':{name:[] for name in (A,B,C)},'router_score':0.}
    x=representation({'id':task['id'],'visible':task['visible']},rows)['structural']
    scores={name:(1/(1+np.exp(-np.clip(x@models[name],-30,30)))).tolist()
            for name in (A,B,C)}
    selected={name:choose(scores[name],rows) for name in (A,B,C)}
    detail={}
    for name in (A,B):
        p=np.asarray(scores[name])
        top=np.partition(p,-2)[-2:] if len(p)>1 else np.r_[p,p]
        detail[name]={'index':selected[name],'top_probability':float(top[-1]),
                      'margin':float(top[-1]-top[-2])}
    row={'n':len(rows),'selected':detail}
    value=np.asarray(features(row),dtype=float)
    scale=np.asarray(router['scale']);w=np.asarray(router['weights'])
    router_score=float(np.r_[value[:-1]/scale,1.]@w)
    selected['learned_router']=selected[B if router_score>0 else A]
    selected['higher_margin']=selected[B if detail[B]['margin']>detail[A]['margin'] else A]
    random_name=B if hashlib.sha256(('router:'+task['id']).encode()).digest()[0]<128 else A
    selected['random_router']=selected[random_name]
    return {'id':task['id'],'seed':task['seed'],'family':task['family'],
            'pool_sha256':digest(rows),'selected':selected,
            'scores':scores,'router_score':router_score}


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    DEST.mkdir(parents=True)
    seed_growth.structure=bool_safe_structure
    router_bytes=ROUTER.read_bytes();component_bytes=COMPONENTS.read_bytes()
    router=json.loads(router_bytes);component=json.loads(component_bytes)
    models={name:np.asarray(component['weights'][name],dtype=float)
            for name in (A,B,C)}
    tasks=[]
    for seed in SEEDS:
        for task in random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23):
            tasks.append({**task,'seed':seed})
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[choices(task,pools[task['id']],models,router) for task in tasks]
    manifest={'protocol':'EXPERIMENT-evaluator-router-transfer.md',
              'router_sha256':hashlib.sha256(router_bytes).hexdigest(),
              'components_sha256':hashlib.sha256(component_bytes).hexdigest(),
              'runner_sha256':hashlib.sha256(
                  (ROOT/'evaluator_router_transfer.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_decisions.json',records)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),
                      'candidates':sum(len(v) for v in pools.values()),
                      'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['router_sha256']==hashlib.sha256(ROUTER.read_bytes()).hexdigest()
    assert manifest['components_sha256']==hashlib.sha256(COMPONENTS.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'evaluator_router_transfer.py').read_bytes()).hexdigest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,record in zip(tasks,records):
        assert task['id']==record['id']
        rows=pools[task['id']]
        assert digest(rows)==record['pool_sha256']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        correct={name:bool(labels[index]) if index is not None else False
                 for name,index in record['selected'].items()}
        outcomes.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'correct':correct,
                         'oracle_union':correct[A] or correct[B]})
    names=list(outcomes[0]['correct'])
    def aggregate(group):
        return {'tasks':len(group),'reachable':sum(r['reachable'] for r in group),
                'correct':{name:sum(r['correct'][name] for r in group) for name in names},
                'oracle_union':sum(r['oracle_union'] for r in group)}
    by_bank=[{'seed':seed,**aggregate([r for r in outcomes if r['seed']==seed])}
             for seed in SEEDS]
    summary={'scope':'fresh zero-query evaluator-router transfer',
             'overall':aggregate(outcomes),'by_bank':by_bank,
             'by_family':{family:aggregate([r for r in outcomes if r['family']==family])
                          for family in FAMILIES},
             'router_minus_E192_by_bank':[b['correct']['learned_router']-
                                          b['correct'][A] for b in by_bank]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
