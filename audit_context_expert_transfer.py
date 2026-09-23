"""Reconstruct public-block expert choices and scored final examples."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from mixed_probe_diagnostic import bool_safe_structure
from context_expert_transfer import (
    EXPERT,ROUTER,COMPONENTS,DEST,SEEDS,FAMILIES,PER_BANK,A,B,C,build_record)
import seed_growth


def main():
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    for name,path in [('expert',EXPERT),('router',ROUTER),('components',COMPONENTS)]:
        assert manifest['input_sha256'][name]==hashlib.sha256(path.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'context_expert_transfer.py').read_bytes()).hexdigest()
    seed_growth.structure=bool_safe_structure
    expert=json.loads(EXPERT.read_text(encoding='utf-8'))
    router=json.loads(ROUTER.read_text(encoding='utf-8'))
    component=json.loads(COMPONENTS.read_text(encoding='utf-8'))
    global_w=np.asarray(expert['global_weights'])
    specialists={int(k):np.asarray(v) for k,v in expert['expert_weights'].items()}
    models={name:np.asarray(component['weights'][name]) for name in (A,B,C)}
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    outcomes=json.loads((DEST/'results.json').read_text(encoding='utf-8'))['tasks']
    assert len(tasks)==len(records)==len(outcomes)==PER_BANK*len(SEEDS)
    checked=0
    for seed in SEEDS:
        original=random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)
        positions=[i for i,t in enumerate(tasks) if t['seed']==seed]
        assert len(positions)==PER_BANK
        for local,i in enumerate(positions):
            task=tasks[i];src=original[local];record=records[i];out=outcomes[i]
            assert task['id']==src['id']==record['id']==out['id']
            assert task['visible']==src['visible'] and task['hidden']==src['hidden']
            rows=pools[task['id']]
            assert digest(rows)==record['pool_sha256']
            assert all(evaluate_program(row['program'],task['visible']) for row in rows)
            assert build_record(task,rows,global_w,specialists,router,models)==record
            labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
            assert {name:bool(labels[index]) if index is not None else False
                    for name,index in record['selected'].items()}==out['correct']
            assert bool(any(labels))==out['reachable']
            checked+=1
    report={'status':'passed','tasks':checked,'bank_regeneration':True,
            'visible_fit':True,'choice_reconstruction':True,
            'outcome_reconstruction':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
