"""Fresh source/target same-base feedback acquisition comparison."""
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
from mixed_evaluator_source import train
from mixed_evaluator_transfer import choose
from improver_acquisition_development import priority,probabilities
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-checkpoints.json'
DEST=ROOT/'runs/improver-acquisition-transfer-20260917'
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
SOURCE_SEED=902209
TARGET_SEEDS=tuple(range(902210,902216))
PER_BANK=32
SOURCE_COUNT=192
BUDGET=7000
METHODS=('order','low_confidence','uncertainty','small_pool','random',
         'iterative_low_confidence')


def public_record(task,rows):
    features=representation({'id':task['id'],'visible':task['visible']},rows)
    return {'id':task['id'],'n':len(rows),'programs':[r['program'] for r in rows],
            'structural':features['structural'].tolist(),
            'pool_sha256':digest(rows)}


def sorted_public(rows,w,method):
    if method=='order':return list(rows)
    return sorted(rows,key=lambda r:(-priority(r,w,method),r['id']))


def acquire(method,public,initial,source_tasks,pools,label_cache):
    source_by_id={t['id']:t for t in source_tasks}
    tactic=method.removeprefix('iterative_')
    bands=(BUDGET//3,BUDGET//3,BUDGET-2*(BUDGET//3)) if method.startswith('iterative_') else (BUDGET,)
    remaining=list(public);chosen=[];log=[];state=initial
    for batch_index,band in enumerate(bands):
        used=0
        for row in sorted_public(remaining,state,tactic):
            room=band-used
            if room<=0:break
            count=min(row['n'],room)
            task=source_by_id[row['id']]
            labels=[]
            for i in range(count):
                key=(row['id'],i)
                if key not in label_cache:
                    label_cache[key]=bool(evaluate_program(
                        pools[row['id']][i]['program'],task['hidden'][8:]))
                labels.append(label_cache[key])
            selected={**row,'n':count,'programs':row['programs'][:count],
                      'structural':row['structural'][:count],'labels':labels}
            chosen.append(selected)
            log.append({'batch':batch_index,'id':row['id'],'candidate_labels':count,
                        'positive_labels':sum(labels)})
            used+=count
            remaining=[r for r in remaining if r['id']!=row['id']]
        assert used==band
        state=train(chosen)
    assert sum(r['n'] for r in chosen)==BUDGET
    return state,log


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    DEST.mkdir(parents=True)
    seed_growth.structure=bool_safe_structure
    raw=SOURCE.read_bytes();checkpoint=json.loads(raw)
    initial=np.asarray(checkpoint['weights']['E0'],dtype=float)
    source=random_bank(SOURCE_SEED,SOURCE_COUNT,FAMILIES,visible=1,hidden=23)
    target=[]
    for seed in TARGET_SEEDS:
        target += [{**task,'seed':seed,'family':FAMILIES[i%len(FAMILIES)]}
                   for i,task in enumerate(random_bank(seed,PER_BANK,FAMILIES,
                                                        visible=1,hidden=23))]
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,source+target))
    pools={key:rows for key,rows,_ in generated}
    public=[public_record(task,pools[task['id']]) for task in source]
    available=[r for r in public if r['n']>0]
    label_cache={};children={};acquisitions={}
    for method in METHODS:
        weights,log=acquire(method,available,initial,source,pools,label_cache)
        children[method]=weights.tolist()
        acquisitions[method]=log
    target_decisions=[]
    for task in target:
        rows=pools[task['id']]
        public_task=public_record(task,rows)
        if rows:
            predictions={'E0':probabilities(public_task,initial).tolist(),
                         'E192':probabilities(public_task,
                            np.asarray(checkpoint['weights']['E192'])).tolist()}
            for method in METHODS:
                predictions[method]=probabilities(public_task,np.asarray(children[method])).tolist()
        else:
            predictions={name:[] for name in ('E0','E192',*METHODS)}
        selected={name:choose(score,rows) if rows else None
                  for name,score in predictions.items()}
        target_decisions.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
            'pool_sha256':public_task['pool_sha256'],'selected':selected,
            'predicted':predictions})
    manifest={'protocol':'EXPERIMENT-improver-acquisition-transfer.md',
              'source_sha256':hashlib.sha256(raw).hexdigest(),
              'runner_sha256':hashlib.sha256(
                  (ROOT/'improver_acquisition_transfer.py').read_bytes()).hexdigest(),
              'source_seed':SOURCE_SEED,'target_seeds':TARGET_SEEDS,
              'per_target_bank':PER_BANK,'candidate_label_budget':BUDGET,
              'preparation_wall_seconds':time.perf_counter()-start,
              'unique_source_candidate_labels_executed':len(label_cache)}
    write_json(DEST/'source_bank.json',source)
    write_json(DEST/'target_bank.json',target)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'source_public_records.json',public)
    write_json(DEST/'opened_source_labels.json',
               [{'id':key[0],'index':key[1],'correct':value}
                for key,value in sorted(label_cache.items())])
    write_json(DEST/'acquisition_logs.json',acquisitions)
    write_json(DEST/'child_weights.json',children)
    write_json(DEST/'frozen_target_decisions.json',target_decisions)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','source_tasks':len(source),
        'target_tasks':len(target),'charged_candidate_labels_per_arm':BUDGET,
        'unique_source_labels_executed':len(label_cache),
        'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'improver_acquisition_transfer.py').read_bytes()).hexdigest()
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    target=json.loads((DEST/'target_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    decisions=json.loads((DEST/'frozen_target_decisions.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,decision in zip(target,decisions):
        rows=pools[task['id']]
        assert task['id']==decision['id']
        assert digest(rows)==decision['pool_sha256']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        correct={name:bool(labels[index]) if index is not None else False
                 for name,index in decision['selected'].items()}
        brier={name:float(np.mean((np.asarray(scores)-np.asarray(labels,dtype=float))**2))
               if labels else None
               for name,scores in decision['predicted'].items()}
        outcomes.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'correct':correct,'brier':brier})
    names=list(outcomes[0]['correct'])
    def aggregate(rows):
        return {'tasks':len(rows),'reachable':sum(r['reachable'] for r in rows),
                'correct':{name:sum(r['correct'][name] for r in rows) for name in names},
                'mean_task_brier':{name:sum(r['brier'][name] for r in rows
                                              if r['brier'][name] is not None)/
                                   max(1,sum(r['brier'][name] is not None for r in rows))
                                   for name in names}}
    by_bank=[{'seed':seed,**aggregate([r for r in outcomes if r['seed']==seed])}
             for seed in TARGET_SEEDS]
    summary={'scope':'fresh same-base 7000-label acquisition transfer',
             'overall':aggregate(outcomes),'by_bank':by_bank,
             'by_family':{family:aggregate([r for r in outcomes if r['family']==family])
                          for family in FAMILIES},
             'low_confidence_minus_order_by_bank':[b['correct']['low_confidence']-
                b['correct']['order'] for b in by_bank]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
