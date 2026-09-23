"""Full six-mechanism, fixed-budget AST output-sensor integration."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,FIXED,BLOCK_AST
from gated_ast_replay_integration import models as evaluator_models,select as evaluator_select
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features,predict,allocate,fixed


DEST=ROOT/'runs/full-mixed-ast-sensor-20260918'
SEEDS=tuple(range(902342,902348))
PER_BANK=48
RANKER=ROOT/'analysis/ast-feedback-replay-model.json'
ALLOCATOR=ROOT/'analysis/ast-query-allocation-development.json'
PARENT=ROOT/'analysis/temperature-ranker-development.json'
POLICIES=('fixed_map','ast_ranker','top20_one','minimax_one','random_one',
          'learned_eight','random_eight','top20_two')


def tasks_for():
    return [{**task,'seed':seed} for seed in SEEDS
            for task in random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)]


def allocator_model():
    raw=json.loads(ALLOCATOR.read_text(encoding='utf-8'))['model']
    return tuple(np.asarray(raw[key],dtype=float) for key in ('mean','scale','w1','w2'))


def allocations(tasks,decisions,predicted,model):
    lookup={r['id']:r for r in decisions}
    result={}
    for seed in SEEDS:
        group=[task for task in tasks if task['seed']==seed and public_block(task)==BLOCK_AST]
        assert len(group)==8
        ids=[task['id'] for task in group]
        x=np.stack([features(task,{**lookup[task['id']],
                                   'first_probe':{'top20_entropy':lookup[task['id']]['first_probe']['top20_entropy']}},
                             predicted[task['id']]) for task in group])
        u1,u2=predict(model,x)
        result[str(seed)]={'learned':dict(zip(ids,allocate(u1,u2,8))),
                           'random':dict(zip(ids,fixed(ids,x,8,'random')))}
        assert all(sum(row.values())==8 for row in result[str(seed)].values())
    return result


def prepare():
    if DEST.exists():raise RuntimeError('fresh run directory exists')
    tasks=tasks_for();start=time.perf_counter()
    base,ast_wide,elapsed=pools_for(tasks)
    ast=[task for task in tasks if public_block(task)==BLOCK_AST]
    public=[({'id':task['id'],'probe_inputs':[text for text,_ in task['hidden'][:8]]},
             ast_wide[task['id']]) for task in ast]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    evaluator=evaluator_models();ranker=updated_model()
    decisions=[]
    for task in tasks:
        key=task['id'];block=public_block(task);rows=ast_wide.get(key,base[key])
        selected=evaluator_select(task,rows,evaluator)
        entry={'id':key,'seed':task['seed'],'public_block':block,
               'base_sha256':digest(base[key]),'wide_sha256':digest(rows),
               'fixed_temperature':FIXED[block],
               'fixed_choice':selected[FIXED[block]]}
        if block==BLOCK_AST:
            scores,order=rank(task,rows,ranker)
            first={mode:choose_probe(key,predicted[key],order,scores,
                                     set(range(len(rows))),[],mode)
                   for mode in ('top20_entropy','minimax','random')}
            entry.update({'scores':scores,'order':order,'first_probe':first})
        decisions.append(entry)
    allocation=allocations(tasks,decisions,predicted,allocator_model())
    manifest={'protocol':'EXPERIMENT-full-mixed-ast-sensor.md',
              'seeds':SEEDS,'per_bank':PER_BANK,'calls_per_bank':8,
              'ranker_sha256':hashlib.sha256(RANKER.read_bytes()).hexdigest(),
              'allocator_sha256':hashlib.sha256(ALLOCATOR.read_bytes()).hexdigest(),
              'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),
              'runner_sha256':hashlib.sha256((ROOT/'full_mixed_ast_sensor.py').read_bytes()).hexdigest(),
              'sensor_sha256':hashlib.sha256((ROOT/'ast_probe_sensor_development.py').read_bytes()).hexdigest(),
              'base_candidates':sum(len(rows) for rows in base.values()),
              'ast_wide_candidates':sum(len(rows) for rows in ast_wide.values()),
              'predicted_output_cells':sum(len(rows)*8 for rows in ast_wide.values()),
              'generation_seconds':sum(elapsed.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'base_pools.json',base)
    write_json(DEST/'ast_wide_pools.json',ast_wide)
    write_json(DEST/'predicted_probe_outputs.json',predicted)
    write_json(DEST/'frozen_decisions.json',decisions)
    write_json(DEST/'frozen_allocations.json',allocation)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared',**manifest},indent=2))


def probe_result(task,record,matrix,labels,mode,count):
    order=record['order'];scores=record['scores']
    remaining=set(range(len(order)));used=[]
    for n in range(count):
        j=record['first_probe'][mode] if n==0 else choose_probe(
            task['id'],matrix,order,scores,remaining,used,mode)
        used.append(j)
        matched={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
        if matched:remaining=matched
    index=next((i for i in order if i in remaining),order[0])
    return bool(labels[index]),used


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results exist')
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['runner_sha256']==hashlib.sha256((ROOT/'full_mixed_ast_sensor.py').read_bytes()).hexdigest()
    assert manifest['ranker_sha256']==hashlib.sha256(RANKER.read_bytes()).hexdigest()
    assert manifest['allocator_sha256']==hashlib.sha256(ALLOCATOR.read_bytes()).hexdigest()
    assert manifest['parent_sha256']==hashlib.sha256(PARENT.read_bytes()).hexdigest()
    assert manifest['sensor_sha256']==hashlib.sha256((ROOT/'ast_probe_sensor_development.py').read_bytes()).hexdigest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    base=json.loads((DEST/'base_pools.json').read_text(encoding='utf-8'))
    ast_wide=json.loads((DEST/'ast_wide_pools.json').read_text(encoding='utf-8'))
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    decisions=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    allocation=json.loads((DEST/'frozen_allocations.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,record in zip(tasks,decisions):
        key=task['id'];block=public_block(task);old=base[key];rows=ast_wide.get(key,old)
        assert key==record['id'] and block==record['public_block']
        assert digest(old)==record['base_sha256'] and digest(rows)==record['wide_sha256']
        base_labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in old]
        labels=base_labels if rows is old else [bool(evaluate_program(row['program'],task['hidden'][8:]))
                                              for row in rows]
        fixed_score=bool(labels[record['fixed_choice']])
        correct={name:fixed_score for name in POLICIES}
        queries={}
        if block==BLOCK_AST:
            matrix=predicted[key]
            correct['ast_ranker']=bool(labels[record['order'][0]])
            for name,mode,count in [('top20_one','top20_entropy',1),
                                    ('minimax_one','minimax',1),
                                    ('random_one','random',1),
                                    ('top20_two','top20_entropy',2)]:
                correct[name],queries[name]=probe_result(task,record,matrix,labels,mode,count)
            for policy,name in [('learned','learned_eight'),('random','random_eight')]:
                action=allocation[str(task['seed'])][policy][key]
                if action:
                    correct[name],queries[name]=probe_result(
                        task,record,matrix,labels,'top20_entropy',action)
                else:
                    correct[name]=correct['ast_ranker'];queries[name]=[]
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'base_reachable':any(base_labels),'wide_reachable':any(labels),
                         'correct':correct,'query_indices':queries})
    def agg(rows):
        return {'tasks':len(rows),'base_reachable':sum(r['base_reachable'] for r in rows),
                'wide_reachable':sum(r['wide_reachable'] for r in rows),
                'correct':{name:sum(r['correct'][name] for r in rows) for name in POLICIES}}
    by_bank=[{'seed':seed,**agg([r for r in outcomes if r['seed']==seed])} for seed in SEEDS]
    summary={'scope':'fresh full mixed fixed-budget AST sensor integration',
             'overall':agg(outcomes),
             'by_family':{family:agg([r for r in outcomes if r['family']==family])
                          for family in FAMILIES},
             'by_bank':by_bank,
             'sensor_minus_fixed_by_bank':[
                 b['correct']['top20_one']-b['correct']['fixed_map'] for b in by_bank],
             'top20_minus_minimax_by_bank':[
                 b['correct']['top20_one']-b['correct']['minimax_one'] for b in by_bank]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
