"""Reconstruct learned and fixed AST query allocation on fresh banks."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import pools_for,updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_query_allocation_transfer import (DEST,SOURCE,RANKER,MIXED_SEEDS,AST_SEEDS,
                                           POLICIES,target_tasks,allocations,model_data)


def main():
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_records.json').read_text(encoding='utf-8'))
    allocation=json.loads((DEST/'frozen_allocations.json').read_text(encoding='utf-8'))
    results=json.loads((DEST/'results.json').read_text(encoding='utf-8'))
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert manifest['ranker_sha256']==hashlib.sha256(RANKER.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256((ROOT/'ast_query_allocation_transfer.py').read_bytes()).hexdigest()
    assert manifest['sensor_sha256']==hashlib.sha256((ROOT/'ast_probe_sensor_development.py').read_bytes()).hexdigest()
    assert target_tasks()==tasks
    regenerated,_=pools_for(tasks)
    assert regenerated==pools
    public=[({'id':task['id'],'probe_inputs':[text for text,_ in task['hidden'][:8]]},
             pools[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    ranker=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key];matrix=predicted[key]
        assert key==record['id'] and digest(rows)==record['pool_sha256']
        scores,order=rank(task,rows,ranker)
        assert order==record['order'] and len(scores)==len(record['scores'])
        assert all(abs(a-b)<1e-6 for a,b in zip(scores,record['scores']))
        assert choose_probe(key,matrix,order,scores,set(range(len(rows))),[],
                            'top20_entropy')==record['first_probe']
    assert allocations(tasks,records,predicted,model_data())==allocation
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key];matrix=predicted[key]
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        checked+=len(labels)
        order=record['order'];scores=record['scores'];correct=[bool(labels[order[0]])]
        remaining=set(range(len(rows)));used=[]
        for n in (1,2):
            j=record['first_probe'] if n==1 else choose_probe(
                key,matrix,order,scores,remaining,used,'top20_entropy')
            used.append(j)
            matched={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
            if matched:remaining=matched
            index=next((i for i in order if i in remaining),order[0])
            correct.append(bool(labels[index]))
        outcomes.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                         'reachable':any(labels),'correct_by_calls':correct,
                         'query_indices':used})
    assert outcomes==results['tasks']
    by_id={r['id']:r for r in outcomes}
    for bank in results['summary']['by_bank']:
        seed=bank['seed']; mapping=allocation[str(seed)]
        assert all(sum(row.values())==8 for row in mapping.values())
        for policy in POLICIES:
            actual=sum(by_id[key]['correct_by_calls'][calls]
                       for key,calls in mapping[policy].items())
            assert actual==bank['correct'][policy]
    audit={'passed':True,'tasks':len(tasks),'candidate_labels_rechecked':checked,
           'predicted_output_cells_rechecked':sum(len(v)*8 for v in predicted.values()),
           'allocation_banks_rechecked':len(MIXED_SEEDS)+len(AST_SEEDS),
           'source_sha256':manifest['source_sha256']}
    write_json(DEST/'audit.json',audit)
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
