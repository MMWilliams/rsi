"""Replay the incremental query-feedback transfer from frozen sources."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import representation
from mixed_probe_diagnostic import pool,bool_safe_structure
from mixed_evaluator_transfer import choose
from active_probe_diagnostic import program_output
import seed_growth


DEST=ROOT/'runs/query-feedback-update-transfer-20260917'
MODEL=ROOT/'analysis/temperature-ranker-development.json'
EXPERT=ROOT/'analysis/context-expert-evaluator-development.json'
VALUE=ROOT/'analysis/sharp-query-value-frozen.json'
UPDATE=ROOT/'analysis/sharp-query-feedback-updated.json'
SEEDS=tuple(range(902264,902270))
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
POLICIES=('updated','previous','scrambled','duplicated_prior','top_disagreement')
BUDGET=95


def read(name):return json.loads((DEST/name).read_text(encoding='utf-8'))


def predict(model,features):
    x=np.asarray(features,dtype=float)
    return float(np.r_[(x-np.asarray(model['mean']))/np.asarray(model['scale']),1.]@
                 np.asarray(model['weights']))


def audit():
    seed_growth.structure=bool_safe_structure
    manifest=read('manifest.json')
    for name,path in [('model',MODEL),('expert',EXPERT),('value',VALUE)]:
        assert manifest['base_input_sha256'][name]==hashlib.sha256(path.read_bytes()).hexdigest()
    assert manifest['update_sha256']==hashlib.sha256(UPDATE.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'query_feedback_update_transfer.py').read_bytes()).hexdigest()
    tasks=read('sealed_bank.json');pools=read('candidate_pools.json')
    plans=read('frozen_plans.json');result=read('results.json')
    regenerated=[{**task,'seed':seed} for seed in SEEDS for task in
                 random_bank(seed,32,FAMILIES,visible=1,hidden=23)]
    assert tasks==regenerated and len(tasks)==len(plans)==len(result['tasks'])==192
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated={key:rows for key,rows,_ in executor.map(pool,tasks)}
    assert generated==pools
    model=json.loads(MODEL.read_text(encoding='utf-8'))
    weights=model['variants']['0.25']['weights']['120']
    mean=np.asarray(model['normalization_mean'],dtype=np.float32)
    scale=np.asarray(model['normalization_scale'],dtype=np.float32)
    expert=json.loads(EXPERT.read_text(encoding='utf-8'))
    global_w=np.asarray(expert['global_weights'],dtype=float)
    experts={int(k):np.asarray(v,dtype=float) for k,v in expert['expert_weights'].items()}
    previous=json.loads(VALUE.read_text(encoding='utf-8'))
    updated=json.loads(UPDATE.read_text(encoding='utf-8'))['models']
    for task,plan in zip(tasks,plans):
        rows=pools[task['id']]
        assert task['id']==plan['id'] and digest(rows)==plan['pool_sha256']
        f=representation({'id':task['id'],'visible':task['visible']},rows)
        x=np.asarray(f['structural'],dtype=np.float32)
        tx=(x-mean)/scale
        h=np.maximum(tx@np.asarray(weights['layers.0.weight'],dtype=np.float32).T
                     +np.asarray(weights['layers.0.bias'],dtype=np.float32),0)
        sharp=(h@np.asarray(weights['layers.2.weight'],dtype=np.float32).T
               +np.asarray(weights['layers.2.bias'],dtype=np.float32)).flatten()
        assert plan['selected']['temp_0.25_120']==choose(sharp,rows)
        blend_w=.5*global_w+.5*experts[f['block']]
        blend=1/(1+np.exp(-np.clip(x@blend_w,-30,30)))
        assert plan['selected']['blend']==choose(blend,rows)
        assert abs(plan['predicted']['previous']-predict(previous,plan['features']))<1e-9
        for name,value in updated.items():
            assert abs(plan['predicted'][name]-predict(value,plan['features']))<1e-9
    indices=list(range(len(plans)))
    orders={name:sorted(indices,key=lambda i:(-plans[i]['predicted'][name],plans[i]['id']))
            for name in ('updated','previous','scrambled','duplicated_prior')}
    orders['top_disagreement']=sorted(indices,key=lambda i:(
        -plans[i]['top_two_disagreement'],plans[i]['features'][2],plans[i]['id']))
    selected={name:set(order[:BUDGET]) for name,order in orders.items()}
    totals={name:0 for name in ('no_query',*POLICIES)}
    by_bank={seed:totals.copy() for seed in SEEDS}
    reachable=0
    for i,(task,plan,outcome) in enumerate(zip(tasks,plans,result['tasks'])):
        rows=pools[task['id']]
        sharp=plan['selected']['temp_0.25_120'];scores=plan['scores']['temp_0.25_120']
        chosen={'no_query':sharp}
        for name in POLICIES:
            probe=plan['entropy_probe'] if i in selected[name] else None
            assert plan['queries'][name]==outcome['queries'][name]==probe
            if probe is None:chosen[name]=sharp;continue
            inp,truth=task['hidden'][probe]
            matching=[j for j,row in enumerate(rows)
                      if program_output(row['program'],inp)==truth]
            chosen[name]=max(matching,key=lambda j:(scores[j],-len(rows[j]['program']),
                                                    rows[j]['program'])) if matching else sharp
        assert chosen==outcome['chosen']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        reachable+=any(labels)
        for name,index in chosen.items():
            correct=bool(labels[index])
            assert correct==outcome['correct'][name]
            totals[name]+=correct;by_bank[task['seed']][name]+=correct
    assert totals==result['summary']['overall']['correct']
    for bank in result['summary']['by_bank']:
        assert by_bank[bank['seed']]==bank['correct']
    report={'status':'pass','tasks':192,'reachable':reachable,
            'candidate_pools_regenerated':192,
            'public_model_choices_and_update_predictions_recomputed':True,
            'query_allocations_and_oracle_outcomes_recomputed':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':audit()
