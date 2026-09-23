"""Reconstruct sequential AST parent/child models, queries and outcomes."""
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
from adaptive_ast_query_development import simulate
from adaptive_ast_improver import (DEST,PROTOCOL,DEVELOPMENT,RANKER,
    MIXED_A,AST_A,MIXED_T,AST_T,MODELS,sha,source_files,source_tables,
    models_for,stage_rows,task_banks,static_allocations,unserialize,gate_for,
    interval,summarize)


def source():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['development_sha256']==sha(DEVELOPMENT)
    assert manifest['source_hashes']=={str(p.relative_to(ROOT)):sha(p) for p in source_files()}
    tables=source_tables()
    parent=models_for(tables)
    assert parent==json.loads((DEST/'parent_models.json').read_text())
    summary=json.loads((DEST/'admission/results.json').read_text())['summary']
    assert gate_for(summary)==json.loads((DEST/'admission_gate.json').read_text())
    added=stage_rows('admission')
    child=models_for({name:tables[name]+added for name in MODELS})
    assert child==json.loads((DEST/'child_models.json').read_text())
    training=json.loads((DEST/'child_training.json').read_text())
    assert training['admission_results_sha256']==sha(DEST/'admission/results.json')
    assert training['source_manifest_sha256']==sha(DEST/'source_manifest.json')
    assert training['new_task_ids']==[r['task']['id'] for r in added]
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
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'adaptive_ast_improver.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['ranker_sha256']==sha(RANKER)
    assert manifest['models_sha256']==sha(model_file)
    if name=='transfer':assert manifest['gate_sha256']==sha(DEST/'admission_gate.json')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    pools=json.loads((directory/'candidate_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    static=json.loads((directory/'frozen_static_allocations.json').read_text())
    traces=json.loads((directory/'adaptive_traces.json').read_text())
    scored=json.loads((directory/'results.json').read_text())
    assert tasks==task_banks(mixed,ast)
    regenerated,_=pools_for(tasks)
    assert regenerated==pools
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             pools[t['id']]) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    ranker=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key]
        assert key==record['id'] and record['pool_sha256']==digest(rows)
        scores,order=rank(task,rows,ranker)
        assert order==record['order'] and np.allclose(scores,record['scores'],atol=1e-6)
        assert choose_probe(key,predicted[key],order,scores,set(range(len(rows))),[],
                            'top20_entropy')==record['first_probe']
    assert static_allocations(tasks,records,predicted,models)==static
    reconstructed=[];checked=0
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
            match={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
            if match:remaining=match
            index=next((i for i in order if i in remaining),order[0])
            correct.append(bool(labels[index]))
        reconstructed.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                              'reachable':any(labels),'correct_by_calls':correct,
                              'query_indices':used})
    assert reconstructed==scored['tasks']
    by_id={r['id']:r for r in reconstructed}
    gate=json.loads((DEST/'admission_gate.json').read_text()) if name=='transfer' else None
    steps=0
    for bank in scored['summary']['by_bank']:
        seed=bank['seed'];group=[t for t in tasks if t['seed']==seed]
        lookup={r['id']:r for r in records}
        rows=[{'task':t,
               'record':{**lookup[t['id']],
                         'first_probe':{'top20_entropy':lookup[t['id']]['first_probe']}},
               'matrix':predicted[t['id']],'correct':[0,0,0]} for t in group]
        for policy,mapping in static[str(seed)].items():
            assert sum(mapping.values())==8
            actual=sum(by_id[key]['correct_by_calls'][count]
                       for key,count in mapping.items())
            assert actual==bank['correct'][policy]
        for policy,model_name,mode in (
            ('conditional0','conditional0','conditional'),
            ('conditional1','conditional1','conditional'),
            ('scrambled','scrambled','conditional'),
            ('duplicate','duplicate','conditional'),
            ('prior1','conditional1','prior')):
            result=simulate(rows,unserialize(models[model_name]),mode)
            frozen=traces[str(seed)][policy]
            assert result['trace']==frozen['trace']
            assert dict(zip([t['id'] for t in group],result['actions']))==frozen['actions']
            assert sum(frozen['actions'].values())==8
            assert len(frozen['trace'])==8
            steps+=8
            actual=sum(by_id[key]['correct_by_calls'][count]
                       for key,count in frozen['actions'].items())
            assert actual==bank['correct'][policy]
        if gate is not None:
            assert bank['correct']['protected_conditional1']==(
                bank['correct']['conditional1'] if gate['admit']
                else bank['correct']['one_each'])
    result={'passed':True,'tasks':len(tasks),'candidate_labels_rechecked':checked,
            'predicted_output_cells_rechecked':sum(len(v)*8 for v in predicted.values()),
            'sequential_query_actions_replayed':steps,
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
