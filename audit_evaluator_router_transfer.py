"""Reconstruct frozen router decisions and final labels."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from mixed_probe_diagnostic import bool_safe_structure
from evaluator_router_transfer import (
    ROUTER,COMPONENTS,DEST,SEEDS,FAMILIES,PER_BANK,A,B,C,choices)
import seed_growth


def main():
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['router_sha256']==hashlib.sha256(ROUTER.read_bytes()).hexdigest()
    assert manifest['components_sha256']==hashlib.sha256(COMPONENTS.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'evaluator_router_transfer.py').read_bytes()).hexdigest()
    seed_growth.structure=bool_safe_structure
    router=json.loads(ROUTER.read_text(encoding='utf-8'))
    raw=json.loads(COMPONENTS.read_text(encoding='utf-8'))
    models={name:np.asarray(raw['weights'][name],dtype=float) for name in (A,B,C)}
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    frozen=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    outcomes=json.loads((DEST/'results.json').read_text(encoding='utf-8'))['tasks']
    assert len(tasks)==len(frozen)==len(outcomes)==PER_BANK*len(SEEDS)
    checked=0
    for seed in SEEDS:
        original=random_bank(seed,PER_BANK,FAMILIES,visible=1,hidden=23)
        positions=[i for i,t in enumerate(tasks) if t['seed']==seed]
        assert len(positions)==PER_BANK
        for local,i in enumerate(positions):
            task=tasks[i];src=original[local];record=frozen[i];out=outcomes[i]
            assert task['id']==src['id']==record['id']==out['id']
            assert task['visible']==src['visible']
            assert task['hidden']==src['hidden']
            rows=pools[task['id']]
            assert digest(rows)==record['pool_sha256']
            assert all(evaluate_program(row['program'],task['visible']) for row in rows)
            rebuilt=choices(task,rows,models,router)
            assert rebuilt==record
            labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
            correct={name:bool(labels[index]) if index is not None else False
                     for name,index in record['selected'].items()}
            assert correct==out['correct']
            assert bool(any(labels))==out['reachable']
            assert bool(correct[A] or correct[B])==out['oracle_union']
            checked+=1
    report={'status':'passed','tasks':checked,'bank_regeneration':True,
            'visible_fit':True,'decision_reconstruction':True,
            'final_label_reconstruction':True}
    write_json(DEST/'audit.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
