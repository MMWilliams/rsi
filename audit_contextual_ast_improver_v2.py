"""Separate-process reconstruction of contextual AST improver checkpoints."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import pools_for,updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs,rank
from contextual_ast_improver_v2 import (DEST,RANKER,PROTOCOL,DEVELOPMENT,
    MIXED_A,AST_A,MIXED_T,AST_T,MODELS,FIXED,sha,source_tables,source_paths,
    train,stage_rows,task_banks,allocations,admission_gate,summarize)


def source():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['development_sha256']==sha(DEVELOPMENT)
    assert manifest['source_hashes']=={str(p.relative_to(ROOT)):sha(p) for p in source_paths()}
    tables=source_tables()
    parent={name:train(name,tables[name]) for name in MODELS}
    assert parent==json.loads((DEST/'parent_models.json').read_text())
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    gate=admission_gate(admission)
    assert gate==json.loads((DEST/'admission_gate.json').read_text())
    extra=stage_rows('admission')
    child={name:train(name,tables[name]+extra) for name in MODELS}
    assert child==json.loads((DEST/'child_models.json').read_text())
    record=json.loads((DEST/'child_training.json').read_text())
    assert record['admission_result_sha256']==sha(DEST/'admission/results.json')
    assert record['source_manifest_sha256']==sha(DEST/'source_manifest.json')
    assert record['new_task_ids']==[r['task']['id'] for r in extra]
    result={'passed':True,'source_files_rechecked':len(manifest['source_hashes']),
            'parent_models_retrained':len(parent),'child_models_retrained':len(child),
            'admission_gate_reconstructed':True}
    write_json(DEST/'audit_source.json',result)
    print(json.dumps(result,indent=2))


def stage(name):
    directory=DEST/name
    mixed,ast=(MIXED_A,AST_A) if name=='admission' else (MIXED_T,AST_T)
    model_file=DEST/('parent_models.json' if name=='admission' else 'child_models.json')
    models=json.loads(model_file.read_text())
    protected=None
    if name=='transfer':
        gate=json.loads((DEST/'admission_gate.json').read_text())
        protected={key:gate[key]['admit'] for key in gate}
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'contextual_ast_improver_v2.py')
    assert manifest['ranker_sha256']==sha(RANKER)
    assert manifest['model_sha256']==sha(model_file)
    if protected is not None:
        assert manifest['protected_sha256']==sha(DEST/'admission_gate.json')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    pools=json.loads((directory/'candidate_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    frozen=json.loads((directory/'frozen_allocations.json').read_text())
    scored=json.loads((directory/'results.json').read_text())
    assert tasks==task_banks(mixed,ast)
    regenerated,_=pools_for(tasks)
    assert regenerated==pools
    public=[({'id':task['id'],'probe_inputs':[v for v,_ in task['hidden'][:8]]},
             pools[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    ranker=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key]
        assert key==record['id'] and digest(rows)==record['pool_sha256']
        scores,order=rank(task,rows,ranker)
        assert order==record['order'] and np.allclose(scores,record['scores'],atol=1e-6)
        assert choose_probe(key,predicted[key],order,scores,set(range(len(rows))),[],
                            'top20_entropy')==record['first_probe']
    assert allocations(tasks,records,predicted,models,protected)==frozen
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key];matrix=predicted[key]
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        checked+=len(labels)
        order=record['order'];scores=record['scores']
        correct=[bool(labels[order[0]])];used=[];remaining=set(range(len(rows)))
        for n in (1,2):
            j=record['first_probe'] if n==1 else choose_probe(
                key,matrix,order,scores,remaining,used,'top20_entropy')
            used.append(j)
            matched={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
            if matched:remaining=matched
            choice=next((i for i in order if i in remaining),order[0])
            correct.append(bool(labels[choice]))
        outcomes.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                         'reachable':any(labels),'correct_by_calls':correct,
                         'query_indices':used})
    assert outcomes==scored['tasks']
    by_id={r['id']:r for r in outcomes}
    for bank in scored['summary']['by_bank']:
        for policy,mapping in frozen[str(bank['seed'])].items():
            assert sum(mapping.values())==8
            assert bank['correct'][policy]==sum(by_id[key]['correct_by_calls'][calls]
                                                for key,calls in mapping.items())
    result={'passed':True,'tasks':len(tasks),'candidate_labels_rechecked':checked,
            'predicted_output_cells_rechecked':sum(len(v)*8 for v in predicted.values()),
            'allocation_banks_rechecked':len(mixed)+len(ast)}
    write_json(DEST/f'audit_{name}.json',result)
    print(json.dumps(result,indent=2))


def final():
    parts=[json.loads((DEST/f'audit_{name}.json').read_text())
           for name in ('source','admission','transfer')]
    assert all(part['passed'] for part in parts)
    assert summarize()==json.loads((DEST/'summary.json').read_text())
    result={'passed':True,'source':parts[0],'admission':parts[1],'transfer':parts[2]}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'source':source,'admission':lambda:stage('admission'),
     'transfer':lambda:stage('transfer'),'final':final}[sys.argv[1]]()
