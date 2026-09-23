"""Regenerate and replay full mixed AST sensor integration."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES
from gated_ast_feedback import pools_for,public_block,FIXED,BLOCK_AST
from gated_ast_replay_integration import models as evaluator_models,select as evaluator_select
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from full_mixed_ast_sensor import (DEST,SEEDS,POLICIES,RANKER,ALLOCATOR,PARENT,
                                   tasks_for,allocations,allocator_model,probe_result)


def main():
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    base=json.loads((DEST/'base_pools.json').read_text(encoding='utf-8'))
    ast_wide=json.loads((DEST/'ast_wide_pools.json').read_text(encoding='utf-8'))
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    decisions=json.loads((DEST/'frozen_decisions.json').read_text(encoding='utf-8'))
    allocation=json.loads((DEST/'frozen_allocations.json').read_text(encoding='utf-8'))
    results=json.loads((DEST/'results.json').read_text(encoding='utf-8'))
    assert manifest['runner_sha256']==hashlib.sha256((ROOT/'full_mixed_ast_sensor.py').read_bytes()).hexdigest()
    assert manifest['ranker_sha256']==hashlib.sha256(RANKER.read_bytes()).hexdigest()
    assert manifest['allocator_sha256']==hashlib.sha256(ALLOCATOR.read_bytes()).hexdigest()
    assert manifest['parent_sha256']==hashlib.sha256(PARENT.read_bytes()).hexdigest()
    assert manifest['sensor_sha256']==hashlib.sha256((ROOT/'ast_probe_sensor_development.py').read_bytes()).hexdigest()
    assert tasks_for()==tasks
    new_base,new_wide,_=pools_for(tasks)
    assert new_base==base and new_wide==ast_wide
    ast=[task for task in tasks if public_block(task)==BLOCK_AST]
    public=[({'id':task['id'],'probe_inputs':[text for text,_ in task['hidden'][:8]]},
             ast_wide[task['id']]) for task in ast]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    evaluator=evaluator_models();ranker=updated_model()
    for task,record in zip(tasks,decisions):
        key=task['id'];block=public_block(task);rows=ast_wide.get(key,base[key])
        assert key==record['id'] and block==record['public_block']
        assert digest(base[key])==record['base_sha256'] and digest(rows)==record['wide_sha256']
        selected=evaluator_select(task,rows,evaluator)
        assert record['fixed_temperature']==FIXED[block]
        assert selected[FIXED[block]]==record['fixed_choice']
        if block==BLOCK_AST:
            scores,order=rank(task,rows,ranker)
            assert order==record['order'] and len(scores)==len(record['scores'])
            assert all(abs(a-b)<1e-6 for a,b in zip(scores,record['scores']))
            first={mode:choose_probe(key,predicted[key],order,scores,
                                     set(range(len(rows))),[],mode)
                   for mode in ('top20_entropy','minimax','random')}
            assert first==record['first_probe']
    assert allocations(tasks,decisions,predicted,allocator_model())==allocation
    outcomes=[];checked=0
    for task,record in zip(tasks,decisions):
        key=task['id'];block=public_block(task);old=base[key];rows=ast_wide.get(key,old)
        base_labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in old]
        labels=base_labels if rows is old else [bool(evaluate_program(row['program'],task['hidden'][8:]))
                                              for row in rows]
        checked+=len(base_labels)+(0 if rows is old else len(labels))
        fixed_score=bool(labels[record['fixed_choice']])
        correct={name:fixed_score for name in POLICIES};queries={}
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
    assert outcomes==results['tasks']
    audit={'passed':True,'tasks':len(tasks),'candidate_labels_rechecked':checked,
           'predicted_output_cells_rechecked':sum(len(v)*8 for v in predicted.values()),
           'allocation_banks_rechecked':len(SEEDS),
           'model_hashes':{k:manifest[k] for k in ('ranker_sha256','allocator_sha256','parent_sha256')}}
    write_json(DEST/'audit.json',audit)
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
