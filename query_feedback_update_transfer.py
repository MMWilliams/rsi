"""Fresh matched-query transfer of incremental query-value feedback."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from mixed_probe_diagnostic import pool, bool_safe_structure
from active_probe_diagnostic import program_output
from sharp_query_value_transfer import inputs, public_record
import seed_growth


UPDATE=ROOT/'analysis/sharp-query-feedback-updated.json'
DEST=ROOT/'runs/query-feedback-update-transfer-20260917'
SEEDS=tuple(range(902264,902270))
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
PER_BANK=32
BUDGET=95
POLICIES=('updated','previous','scrambled','duplicated_prior','top_disagreement')


def value(model,values):
    x=np.asarray(values,dtype=float)
    mean=np.asarray(model['mean']);scale=np.asarray(model['scale'])
    weights=np.asarray(model['weights'])
    return float(np.r_[(x-mean)/scale,1.]@weights)


def allocations(records):
    indices=list(range(len(records)))
    order={name:sorted(indices,key=lambda i:(-records[i]['predicted'][name],records[i]['id']))
           for name in ('updated','previous','scrambled','duplicated_prior')}
    order['top_disagreement']=sorted(indices,key=lambda i:(
        -records[i]['top_two_disagreement'],records[i]['features'][2],records[i]['id']))
    return {name:set(values[:BUDGET]) for name,values in order.items()}


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    seed_growth.structure=bool_safe_structure
    base=inputs()
    update_raw=UPDATE.read_bytes();update=json.loads(update_raw)
    tasks=[{**task,'seed':seed} for seed in SEEDS for task in
           random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)]
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[public_record(task,pools[task['id']],base) for task in tasks]
    for record in records:
        record['predicted']={'previous':record['value_prediction']}
        for name,model in update['models'].items():
            record['predicted'][name]=value(model,record['features'])
    selected=allocations(records)
    for i,record in enumerate(records):
        record['queries']={name:record['entropy_probe'] if i in selected[name] else None
                           for name in POLICIES}
    manifest={'protocol':'EXPERIMENT-query-feedback-update-transfer.md',
              'base_input_sha256':{name:hashlib.sha256(raw).hexdigest()
                                    for name,raw in base[0].items()},
              'update_sha256':hashlib.sha256(update_raw).hexdigest(),
              'runner_sha256':hashlib.sha256(
                  (ROOT/'query_feedback_update_transfer.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,'query_budget':BUDGET,
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_plans.json',records)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),
                      'candidates':sum(map(len,pools.values())),
                      'queries_per_policy':{name:len(selected[name]) for name in POLICIES},
                      'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['update_sha256']==hashlib.sha256(UPDATE.read_bytes()).hexdigest()
    assert manifest['base_input_sha256']=={name:hashlib.sha256(raw).hexdigest()
                                            for name,raw in inputs()[0].items()}
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'query_feedback_update_transfer.py').read_bytes()).hexdigest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    plans=json.loads((DEST/'frozen_plans.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,plan in zip(tasks,plans):
        rows=pools[task['id']]
        assert task['id']==plan['id'] and digest(rows)==plan['pool_sha256']
        sharp=plan['selected']['temp_0.25_120'];scores=plan['scores']['temp_0.25_120']
        chosen={'no_query':sharp}
        for name,probe in plan['queries'].items():
            if probe is None:chosen[name]=sharp;continue
            inp,truth=task['hidden'][probe]
            matching=[i for i,row in enumerate(rows)
                      if program_output(row['program'],inp)==truth]
            chosen[name]=max(matching,key=lambda i:(scores[i],-len(rows[i]['program']),
                                                    rows[i]['program'])) if matching else sharp
        unique=set(chosen.values())
        labels={i:bool(evaluate_program(rows[i]['program'],task['hidden'][8:])) for i in unique}
        outcomes.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'chosen':chosen,'queries':plan['queries'],
                         'correct':{name:labels[index] for name,index in chosen.items()}})
    names=('no_query',*POLICIES)
    def aggregate(group):
        return {'tasks':len(group),
                'queries':{name:sum(row['queries'][name] is not None for row in group)
                           for name in POLICIES},
                'correct':{name:sum(row['correct'][name] for row in group) for name in names}}
    banks=[{'seed':seed,**aggregate([row for row in outcomes if row['seed']==seed])}
           for seed in SEEDS]
    summary={'scope':'fresh incremental query-value feedback transfer',
             'overall':aggregate(outcomes),'by_bank':banks,
             'by_family':{family:aggregate([row for row in outcomes if row['family']==family])
                          for family in FAMILIES},
             'updated_minus_previous_by_bank':[
                 bank['correct']['updated']-bank['correct']['previous'] for bank in banks]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
