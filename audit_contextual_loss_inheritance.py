"""Independent task, model and policy replay of contextual edit inheritance."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from seed_growth import representation
from mixed_probe_diagnostic import pool,bool_safe_structure
from mixed_evaluator_transfer import choose
import seed_growth


DEST=ROOT/'runs/contextual-loss-inheritance-20260917'
PRIOR=ROOT/'runs/temperature-withheld-families-20260917/results.json'
MODEL=ROOT/'analysis/temperature-ranker-development.json'
SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
SEEDS=tuple(range(902276,902288))
CATALOG=('temp_0.25','temp_0.5','temp_1.0')
POLICIES=('empty','inherited','scrambled')


def read(name):return json.loads((DEST/name).read_text(encoding='utf-8'))


def pick(table):
    return {family:sorted(CATALOG,key=lambda name:(-table[family][name],
                                                   CATALOG.index(name)))[0]
            for family in FAMILIES}


def add(table,rows):
    for row in rows:
        for name in CATALOG:table[row['family']][name]+=row['correct'][name]


def feedback(task,record,rows):
    unique={record['selected'][name] for name in CATALOG}
    truth={i:bool(evaluate_program(rows[i]['program'],task['hidden'][8:])) for i in unique}
    return {'id':task['id'],'family':task['family'],
            'correct':{name:truth[record['selected'][name]] for name in CATALOG}}


def audit():
    seed_growth.structure=bool_safe_structure
    manifest=read('manifest.json')
    assert manifest['prior_sha256']==hashlib.sha256(PRIOR.read_bytes()).hexdigest()
    assert manifest['input_sha256']=={
        'model':hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        'source':hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'contextual_loss_inheritance.py').read_bytes()).hexdigest()
    tasks=read('sealed_bank.json');pools=read('candidate_pools.json')
    decisions=read('frozen_model_decisions.json')
    parent=read('parent_frozen.json');child=read('child_frozen.json')
    result=read('results.json')
    regenerated=[{**task,'seed':seed} for seed in SEEDS for task in
                 random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    assert tasks==regenerated and len(tasks)==len(decisions)==576
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated={key:rows for key,rows,_ in executor.map(pool,tasks)}
    assert generated==pools
    prior=json.loads(PRIOR.read_text(encoding='utf-8'))['summary']['by_family']
    inherited={family:{name:8*(prior[family]['correct'][name]/prior[family]['tasks'])
                       for name in CATALOG} for family in FAMILIES}
    scrambled={family:inherited[FAMILIES[(i+1)%len(FAMILIES)]].copy()
               for i,family in enumerate(FAMILIES)}
    empty={family:dict.fromkeys(CATALOG,0.) for family in FAMILIES}
    priors={'empty':empty,'inherited':inherited,'scrambled':scrambled}
    fixed_context={family:sorted(CATALOG,key=lambda name:(
        -prior[family]['correct'][name],CATALOG.index(name)))[0] for family in FAMILIES}
    assert manifest['prior_tables']==priors
    assert manifest['fixed_context']==fixed_context
    model=json.loads(MODEL.read_text(encoding='utf-8'))
    mean=np.asarray(model['normalization_mean'],dtype=np.float32)
    scale=np.asarray(model['normalization_scale'],dtype=np.float32)
    e192=np.asarray(json.loads(SOURCE.read_text(encoding='utf-8'))['full_weights'],dtype=float)
    for task,record in zip(tasks,decisions):
        rows=pools[task['id']]
        assert task['id']==record['id'] and digest(rows)==record['pool_sha256']
        x=np.asarray(representation({'id':task['id'],'visible':task['visible']},
                                    rows)['structural'],dtype=np.float32)
        tx=(x-mean)/scale
        for temperature in ('0.25','0.5','1.0'):
            state=model['variants'][temperature]['weights']['120']
            h=np.maximum(tx@np.asarray(state['layers.0.weight'],dtype=np.float32).T
                         +np.asarray(state['layers.0.bias'],dtype=np.float32),0)
            scores=(h@np.asarray(state['layers.2.weight'],dtype=np.float32).T
                    +np.asarray(state['layers.2.bias'],dtype=np.float32)).flatten()
            assert record['selected'][f'temp_{temperature}']==choose(scores,rows)
        assert record['selected']['E192']==choose(x@e192,rows)
    assert child['parent_sha256']==hashlib.sha256(
        (DEST/'parent_frozen.json').read_bytes()).hexdigest()
    parent_policy={name:0 for name in (*POLICIES,'fixed_context')}
    child_policy=parent_policy.copy()
    parent_fixed={name:0 for name in CATALOG}
    child_fixed=parent_fixed.copy()
    child_reachable=0
    for episode in range(6):
        offset=episode*96
        p=parent['episodes'][episode];c=child['episodes'][episode]
        r=result['episodes'][episode]
        assert p['episode']==c['episode']==r['episode']==episode
        states=json.loads(json.dumps(priors))
        admission=[feedback(tasks[i],decisions[i],pools[tasks[i]['id']])
                   for i in range(offset,offset+24)]
        assert admission==p['admission']==c['parent_admission']
        for table in states.values():add(table,admission)
        assert states==p['parent_tables']
        parent_choice={name:pick(table) for name,table in states.items()}
        assert parent_choice==p['parent_choice']==c['parent_choice']==r['parent_choice']
        final=[feedback(tasks[i],decisions[i],pools[tasks[i]['id']])
               for i in range(offset+24,offset+48)]
        assert final==c['parent_final']
        for table in states.values():add(table,final)
        child_admission=[feedback(tasks[i],decisions[i],pools[tasks[i]['id']])
                         for i in range(offset+48,offset+72)]
        assert child_admission==c['child_admission']
        for table in states.values():add(table,child_admission)
        assert states==c['child_tables']
        child_choice={name:pick(table) for name,table in states.items()}
        assert child_choice==c['child_choice']==r['child_choice']
        child_final=[]
        for i in range(offset+72,offset+96):
            task=tasks[i];rows=pools[task['id']]
            row=feedback(task,decisions[i],rows)
            row['reachable']=any(evaluate_program(candidate['program'],task['hidden'][8:])
                                 for candidate in rows)
            child_final.append(row)
            child_reachable+=row['reachable']
        assert child_final==r['child_final']
        for name in CATALOG:
            parent_fixed[name]+=sum(row['correct'][name] for row in final)
            child_fixed[name]+=sum(row['correct'][name] for row in child_final)
        for name in POLICIES:
            parent_policy[name]+=sum(row['correct'][parent_choice[name][row['family']]]
                                     for row in final)
            child_policy[name]+=sum(row['correct'][child_choice[name][row['family']]]
                                    for row in child_final)
        parent_policy['fixed_context']+=sum(row['correct'][fixed_context[row['family']]]
                                            for row in final)
        child_policy['fixed_context']+=sum(row['correct'][fixed_context[row['family']]]
                                           for row in child_final)
    summary=result['summary']
    assert parent_fixed==summary['parent_fixed'] and child_fixed==summary['child_fixed']
    assert parent_policy==summary['parent_policy'] and child_policy==summary['child_policy']
    assert child_reachable==summary['child_reachable']
    report={'status':'pass','tasks':576,'episodes':6,'child_reachable':child_reachable,
            'candidate_pools_regenerated':576,'model_choices_recomputed':576*4,
            'parent_and_child_tables_replayed':True,'all_final_outcomes_recomputed':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':audit()
