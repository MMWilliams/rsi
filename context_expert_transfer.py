"""Fresh fixed-pool public-context evaluator expert transfer."""
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
from evaluator_router_transfer import choices as router_choices,A,B,C
import seed_growth


EXPERT=ROOT/'analysis/context-expert-evaluator-development.json'
ROUTER=ROOT/'analysis/evaluator-router-frozen.json'
COMPONENTS=ROOT/'analysis/pairwise-evaluator-development.json'
DEST=ROOT/'runs/context-expert-transfer-20260917'
SEEDS=tuple(range(902222,902228))
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
PER_BANK=32


def build_record(task,rows,global_w,experts,router,models):
    record=router_choices(task,rows,models,router)
    if rows:
        f=representation({'id':task['id'],'visible':task['visible']},rows)
        x=f['structural'];block=f['block']
        weights={'expert':experts[block],'blend':.5*global_w+.5*experts[block]}
        for name,w in weights.items():
            p=(1/(1+np.exp(-np.clip(x@w,-30,30)))).tolist()
            record['scores'][name]=p
            record['selected'][name]=choose(p,rows)
        record['public_block']=block
    else:
        record['scores'].update({'expert':[],'blend':[]})
        record['selected'].update({'expert':None,'blend':None})
        record['public_block']=None
    return record


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    DEST.mkdir(parents=True)
    seed_growth.structure=bool_safe_structure
    raw={name:path.read_bytes() for name,path in
         [('expert',EXPERT),('router',ROUTER),('components',COMPONENTS)]}
    expert=json.loads(raw['expert']);router=json.loads(raw['router'])
    components=json.loads(raw['components'])
    global_w=np.asarray(expert['global_weights'],dtype=float)
    experts={int(k):np.asarray(v,dtype=float)
             for k,v in expert['expert_weights'].items()}
    models={name:np.asarray(components['weights'][name],dtype=float)
            for name in (A,B,C)}
    assert np.array_equal(global_w,models[A])
    tasks=[]
    for seed in SEEDS:
        for task in random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23):
            tasks.append({**task,'seed':seed})
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[build_record(task,pools[task['id']],global_w,experts,router,models)
             for task in tasks]
    manifest={'protocol':'EXPERIMENT-context-expert-transfer.md',
              'input_sha256':{name:hashlib.sha256(value).hexdigest()
                              for name,value in raw.items()},
              'runner_sha256':hashlib.sha256(
                  (ROOT/'context_expert_transfer.py').read_bytes()).hexdigest(),
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
    for name,path in [('expert',EXPERT),('router',ROUTER),('components',COMPONENTS)]:
        assert manifest['input_sha256'][name]==hashlib.sha256(path.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'context_expert_transfer.py').read_bytes()).hexdigest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,record in zip(tasks,records):
        rows=pools[task['id']]
        assert task['id']==record['id'] and digest(rows)==record['pool_sha256']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        correct={name:bool(labels[index]) if index is not None else False
                 for name,index in record['selected'].items()}
        outcomes.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'correct':correct})
    names=list(outcomes[0]['correct'])
    def aggregate(group):
        return {'tasks':len(group),'reachable':sum(r['reachable'] for r in group),
                'correct':{name:sum(r['correct'][name] for r in group) for name in names}}
    by_bank=[{'seed':seed,**aggregate([r for r in outcomes if r['seed']==seed])}
             for seed in SEEDS]
    summary={'scope':'fresh public-context expert transfer',
             'overall':aggregate(outcomes),'by_bank':by_bank,
             'by_family':{family:aggregate([r for r in outcomes if r['family']==family])
                          for family in FAMILIES},
             'blend_minus_E192_by_bank':[b['correct']['blend']-b['correct'][A]
                                         for b in by_bank]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
