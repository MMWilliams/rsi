"""Frozen same-pool evaluator checkpoint transfer across three mechanisms."""
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
from seed_source_search import read
from seed_growth import representation
from active_probe_diagnostic import program_output,choose_probe
from mixed_probe_diagnostic import pool,bool_safe_structure
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-checkpoints.json'
DEST=ROOT/'runs/mixed-evaluator-transfer-20260917'
SEEDS=tuple(range(902203,902209))
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
PER_BANK=32
CHECKPOINTS=('E0','E48','E96','E192','scrambled192')


def choose(scores,rows):
    return max(range(len(rows)),key=lambda i:(float(scores[i]),
               -len(rows[i]['program']),rows[i]['program']))


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    DEST.mkdir(parents=True)
    source_bytes=SOURCE.read_bytes()
    source=json.loads(source_bytes)
    weights={name:np.asarray(source['weights'][name],dtype=float)
             for name in CHECKPOINTS}
    seed_growth.structure=bool_safe_structure
    tasks=[]
    for seed in SEEDS:
        for task in random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23):
            tasks.append({'id':task['id'],'seed':seed,'family':task['family'],
                          'visible':task['visible'],
                          'probe_inputs':[pair[0] for pair in task['hidden'][:8]],
                          'probe_outputs':[pair[1] for pair in task['hidden'][:8]],
                          'final':task['hidden'][8:]})
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[]
    for task in tasks:
        rows=pools[task['id']]
        assert rows
        public={'id':task['id'],'visible':task['visible']}
        x=representation(public,rows)['structural']
        predicted={name:(1/(1+np.exp(-np.clip(x@w,-30,30)))).tolist()
                   for name,w in weights.items()}
        output=[[program_output(row['program'],inp) for inp in task['probe_inputs']]
                for row in rows]
        entropy_probe=choose_probe(task['id'],output,list(range(len(rows))),[],
                                   predicted['E0'],'entropy')
        selected={name:choose(predicted[name],rows) for name in CHECKPOINTS}
        selected['first_generated']=0
        selected['shortest']=min(range(len(rows)),key=lambda i:(
            len(rows[i]['program']),rows[i]['program']))
        records.append({'id':task['id'],'family':task['family'],'n':len(rows),
                        'pool_sha256':digest(rows),'selected':selected,
                        'predicted':predicted,'probe_outputs_predicted':output,
                        'entropy_probe':entropy_probe})
    manifest={'protocol':'EXPERIMENT-mixed-evaluator-checkpoint-transfer.md',
              'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
              'runner_sha256':hashlib.sha256(
                  (ROOT/'mixed_evaluator_transfer.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,'families':FAMILIES,
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_decisions.json',records)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),
                      'candidate_count':sum(r['n'] for r in records),
                      'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=read(DEST/'manifest.json')
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'mixed_evaluator_transfer.py').read_bytes()).hexdigest()
    tasks=read(DEST/'sealed_bank.json');pools=read(DEST/'candidate_pools.json')
    records=read(DEST/'frozen_decisions.json')
    assert len(tasks)==len(records)==PER_BANK*len(SEEDS)
    outcomes=[]
    for task,rec in zip(tasks,records):
        rows=pools[task['id']];assert task['id']==rec['id']
        assert digest(rows)==rec['pool_sha256']
        labels=[bool(evaluate_program(row['program'],task['final'])) for row in rows]
        j=rec['entropy_probe'];truth=task['probe_outputs'][j]
        matching=[i for i in range(len(rows))
                  if rec['probe_outputs_predicted'][i][j]==truth]
        no_query={name:bool(labels[index]) for name,index in rec['selected'].items()}
        one_query={};brier={}
        for name in CHECKPOINTS:
            scores=rec['predicted'][name]
            index=max(matching,key=lambda i:(float(scores[i]),
                -len(rows[i]['program']),rows[i]['program'])) if matching else rec['selected'][name]
            one_query[name]=bool(labels[index])
            brier[name]=float(np.mean((np.asarray(scores)-np.asarray(labels,dtype=float))**2))
        outcomes.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'no_query':no_query,
                         'one_query':one_query,'brier':brier})
    names=list(outcomes[0]['no_query'])
    def aggregate(group):
        return {'tasks':len(group),'reachable':sum(r['reachable'] for r in group),
                'no_query':{name:sum(r['no_query'][name] for r in group)
                            for name in names},
                'one_query':{name:sum(r['one_query'][name] for r in group)
                             for name in CHECKPOINTS},
                'mean_task_brier':{name:sum(r['brier'][name] for r in group)/len(group)
                                   for name in CHECKPOINTS}}
    by_bank=[{'seed':seed,**aggregate([r for r in outcomes if r['seed']==seed])}
             for seed in SEEDS]
    summary={'scope':'fresh fixed-pool evaluator transfer; all choices frozen pre-label',
             'overall':aggregate(outcomes),'by_bank':by_bank,
             'by_family':{family:aggregate([r for r in outcomes if r['family']==family])
                          for family in FAMILIES},
             'E192_minus_E0_by_bank':[b['no_query']['E192']-b['no_query']['E0']
                                      for b in by_bank],
             'output_query_budget_per_checkpoint':len(outcomes)}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
