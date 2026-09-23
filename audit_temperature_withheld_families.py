"""Independent replay of sharp-ranker withheld-mechanism transfer."""
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


DEST=ROOT/'runs/temperature-withheld-families-20260917'
MODEL=ROOT/'analysis/temperature-ranker-development.json'
SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
SEEDS=tuple(range(902270,902276))
TEMPERATURES=('0.25','0.5','1.0')


def read(name):return json.loads((DEST/name).read_text(encoding='utf-8'))


def audit():
    seed_growth.structure=bool_safe_structure
    manifest=read('manifest.json')
    assert manifest['input_sha256']=={
        'model':hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        'source':hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'temperature_withheld_families.py').read_bytes()).hexdigest()
    tasks=read('sealed_bank.json');pools=read('candidate_pools.json')
    decisions=read('frozen_decisions.json');result=read('results.json')
    regenerated=[{**task,'seed':seed} for seed in SEEDS for task in
                 random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    assert tasks==regenerated and len(tasks)==len(decisions)==len(result['tasks'])==288
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated={key:rows for key,rows,_ in executor.map(pool,tasks)}
    assert generated==pools
    model=json.loads(MODEL.read_text(encoding='utf-8'))
    mean=np.asarray(model['normalization_mean'],dtype=np.float32)
    scale=np.asarray(model['normalization_scale'],dtype=np.float32)
    e192=np.asarray(json.loads(SOURCE.read_text(encoding='utf-8'))['full_weights'],dtype=float)
    totals={name:0 for name in result['summary']['overall']['correct']}
    reachable=0
    by_family={family:{name:0 for name in totals} for family in FAMILIES}
    for task,record,outcome in zip(tasks,decisions,result['tasks']):
        rows=pools[task['id']]
        assert task['id']==record['id']==outcome['id']
        assert digest(rows)==record['pool_sha256']
        x=np.asarray(representation({'id':task['id'],'visible':task['visible']},
                                    rows)['structural'],dtype=np.float32)
        tx=(x-mean)/scale
        for temperature in TEMPERATURES:
            state=model['variants'][temperature]['weights']['120']
            h=np.maximum(tx@np.asarray(state['layers.0.weight'],dtype=np.float32).T
                         +np.asarray(state['layers.0.bias'],dtype=np.float32),0)
            scores=(h@np.asarray(state['layers.2.weight'],dtype=np.float32).T
                    +np.asarray(state['layers.2.bias'],dtype=np.float32)).flatten()
            assert record['selected'][f'temp_{temperature}']==choose(scores,rows)
        assert record['selected']['E192']==choose(x@e192,rows)
        assert record['selected']['first_generated']==0
        assert record['selected']['shortest']==min(range(len(rows)),key=lambda i:(
            len(rows[i]['program']),rows[i]['program']))
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        assert outcome['reachable']==any(labels)
        reachable+=any(labels)
        for name,index in record['selected'].items():
            correct=bool(labels[index])
            assert outcome['correct'][name]==correct
            totals[name]+=correct;by_family[task['family']][name]+=correct
    assert reachable==result['summary']['overall']['reachable']
    assert totals==result['summary']['overall']['correct']
    for family in FAMILIES:
        assert by_family[family]==result['summary']['by_family'][family]['correct']
    report={'status':'pass','tasks':len(tasks),'reachable':reachable,
            'candidate_pools_regenerated':len(tasks),
            'model_choices_recomputed':len(tasks)*len(totals),
            'all_outcomes_recomputed':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':audit()
