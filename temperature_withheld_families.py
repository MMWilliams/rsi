"""Frozen no-query ranker transfer across three unseen task mechanisms."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import torch

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from seed_growth import representation
from mixed_probe_diagnostic import pool,bool_safe_structure
from mixed_evaluator_transfer import choose
from listwise_evaluator_development import Ranker
import seed_growth


MODEL=ROOT/'analysis/temperature-ranker-development.json'
SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
DEST=ROOT/'runs/temperature-withheld-families-20260917'
SEEDS=tuple(range(902270,902276))
PER_BANK=48
KNOWN=('stack_transition','mutation_transition','self_edit_transition')
WITHHELD=tuple(family for family in FAMILIES if family not in KNOWN)
TEMPERATURES=('0.25','0.5','1.0')


def inputs():
    raw={'model':MODEL.read_bytes(),'source':SOURCE.read_bytes()}
    data={name:json.loads(value) for name,value in raw.items()}
    model_data=data['model']
    mean=np.asarray(model_data['normalization_mean'],dtype=np.float32)
    scale=np.asarray(model_data['normalization_scale'],dtype=np.float32)
    models={}
    for temperature in TEMPERATURES:
        model=Ranker(32)
        weights=model_data['variants'][temperature]['weights']['120']
        model.load_state_dict({key:torch.tensor(value,dtype=torch.float32)
                               for key,value in weights.items()})
        model.eval()
        models[temperature]=model
    e192=np.asarray(data['source']['full_weights'],dtype=float)
    return raw,mean,scale,models,e192


def decision(task,rows,data):
    _,mean,scale,models,e192=data
    f=representation({'id':task['id'],'visible':task['visible']},rows)
    x=np.asarray(f['structural'],dtype=np.float32)
    selected={}
    with torch.no_grad():
        tx=torch.from_numpy((x-mean)/scale)
        for temperature,model in models.items():
            selected[f'temp_{temperature}']=choose(model(tx).numpy(),rows)
    selected['E192']=choose(x@e192,rows)
    selected['first_generated']=0
    selected['shortest']=min(range(len(rows)),key=lambda i:(
        len(rows[i]['program']),rows[i]['program']))
    return {'id':task['id'],'seed':task['seed'],'family':task['family'],
            'pool_sha256':digest(rows),'selected':selected}


def prepare():
    if DEST.exists():raise RuntimeError('transfer directory already exists')
    seed_growth.structure=bool_safe_structure
    data=inputs()
    tasks=[{**task,'seed':seed} for seed in SEEDS for task in
           random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)]
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[decision(task,pools[task['id']],data) for task in tasks]
    manifest={'protocol':'EXPERIMENT-temperature-withheld-families.md',
              'input_sha256':{name:hashlib.sha256(value).hexdigest()
                              for name,value in data[0].items()},
              'runner_sha256':hashlib.sha256(
                  (ROOT/'temperature_withheld_families.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,'known':KNOWN,'withheld':WITHHELD,
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_decisions.json',records)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),
                      'candidates':sum(map(len,pools.values())),
                      'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['input_sha256']=={name:hashlib.sha256(value).hexdigest()
                                      for name,value in inputs()[0].items()}
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'temperature_withheld_families.py').read_bytes()).hexdigest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    decisions=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,record in zip(tasks,decisions):
        rows=pools[task['id']]
        assert task['id']==record['id'] and digest(rows)==record['pool_sha256']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        outcomes.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),
                         'correct':{name:bool(labels[index]) for name,index in
                                    record['selected'].items()}})
    names=list(outcomes[0]['correct'])
    def aggregate(group):
        return {'tasks':len(group),'reachable':sum(row['reachable'] for row in group),
                'correct':{name:sum(row['correct'][name] for row in group) for name in names}}
    summary={'scope':'fresh held-out mechanism evaluator transfer',
             'overall':aggregate(outcomes),
             'known':aggregate([row for row in outcomes if row['family'] in KNOWN]),
             'withheld':aggregate([row for row in outcomes if row['family'] in WITHHELD]),
             'by_family':{family:aggregate([row for row in outcomes if row['family']==family])
                          for family in FAMILIES},
             'by_bank':[{**{'seed':seed},**aggregate([row for row in outcomes if row['seed']==seed])}
                        for seed in SEEDS],
             'withheld_025_minus_1_by_bank':[
                 sum(row['correct']['temp_0.25']-row['correct']['temp_1.0']
                     for row in outcomes if row['seed']==seed and row['family'] in WITHHELD)
                 for seed in SEEDS]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
