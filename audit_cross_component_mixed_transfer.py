"""Independent reconstruction of mixed evaluator-edit catalog decisions."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import pools_for,public_block,FIXED,BLOCK_AST
from gated_ast_replay_integration import models as evaluator_models,select as evaluator_select
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from full_mixed_ast_sensor import probe_result
from adaptive_ast_query_development import simulate
from adaptive_ast_improver import unserialize
from cross_component_mixed_transfer import (DEST,PROTOCOL,TEMP,RANKER,ADAPTIVE,
    SEEDS,POLICIES,sha,tasks_for)
from seed_casebanks import FAMILIES


def read():
    return tuple(json.loads((DEST/name).read_text()) for name in (
        'manifest.json','sealed_bank.json','base_pools.json','ast_wide_pools.json',
        'predicted_probe_outputs.json','frozen_decisions.json'))


def verify_manifest(manifest):
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'cross_component_mixed_transfer.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['model_sha256']=={'temperature':sha(TEMP),'ranker':sha(RANKER),
                                     'adaptive':sha(ADAPTIVE)}


def prepare():
    manifest,tasks,base,wide,predicted,decisions=read()
    verify_manifest(manifest)
    assert tasks==tasks_for()
    regenerated,regenerated_wide,_=pools_for(tasks)
    assert regenerated==base and regenerated_wide==wide
    ast=[task for task in tasks if public_block(task)==BLOCK_AST]
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             wide[t['id']]) for t in ast]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    evaluators=evaluator_models();ranker=updated_model()
    for task,record in zip(tasks,decisions):
        key=task['id'];block=public_block(task);rows=wide.get(key,base[key])
        assert key==record['id'] and block==record['public_block']
        assert digest(base[key])==record['base_sha256'] and digest(rows)==record['wide_sha256']
        choice=evaluator_select(task,rows,evaluators)
        assert record['fixed_temperature']==FIXED[block]
        assert record['fixed_choice']==choice[FIXED[block]]
        assert record['sharp_choice']==choice['temp_0.25']
        if block==BLOCK_AST:
            scores,order=rank(task,rows,ranker)
            assert order==record['order'] and np.allclose(scores,record['scores'],atol=1e-6)
            for mode in ('top20_entropy','minimax'):
                assert choose_probe(key,predicted[key],order,scores,
                                    set(range(len(rows))),[],mode)==record['first_probe'][mode]
    result={'passed':True,'tasks':len(tasks),
            'base_candidates_rechecked':sum(len(v) for v in base.values()),
            'ast_wide_candidates_rechecked':sum(len(v) for v in wide.values()),
            'predicted_output_cells_rechecked':sum(len(v)*8 for v in wide.values()),
            'decisions_rechecked':len(decisions)}
    write_json(DEST/'audit_prepare.json',result)
    print(json.dumps(result,indent=2))


def score():
    manifest,tasks,base,wide,predicted,decisions=read()
    verify_manifest(manifest)
    stored=json.loads((DEST/'results.json').read_text())
    traces=json.loads((DEST/'adaptive_traces.json').read_text())
    labels_by_id={};base_by_id={};checked=0
    for task in tasks:
        key=task['id'];old=base[key];rows=wide.get(key,old)
        old_labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in old]
        labels=old_labels if rows is old else [bool(evaluate_program(row['program'],
            task['hidden'][8:])) for row in rows]
        checked+=len(old_labels)+(0 if rows is old else len(labels))
        base_by_id[key]=old_labels;labels_by_id[key]=labels
    outcomes=[]
    for task,record in zip(tasks,decisions):
        key=task['id'];block=public_block(task);labels=labels_by_id[key]
        fixed=bool(labels[record['fixed_choice']]);sharp=bool(labels[record['sharp_choice']])
        correct={name:(sharp if name.startswith('sharp') else fixed) for name in POLICIES}
        queries={}
        if block==BLOCK_AST:
            correct['ast_ranker']=bool(labels[record['order'][0]])
            correct['sharp_ast_ranker']=correct['ast_ranker']
            for name,mode in (('top20_one','top20_entropy'),('minimax_one','minimax')):
                value,used=probe_result(task,record,predicted[key],labels,mode,1)
                correct[name]=value;correct['sharp_'+name]=value;queries[name]=used
            correct['adaptive']=correct['ast_ranker']
            correct['sharp_adaptive']=correct['ast_ranker']
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'base_reachable':any(base_by_id[key]),'wide_reachable':any(labels),
                         'correct':correct,'query_indices':queries})
    by_record={r['id']:r for r in decisions};by_outcome={r['id']:r for r in outcomes}
    model=unserialize(json.loads(ADAPTIVE.read_text())['conditional1'])
    actions=0
    for seed in SEEDS:
        group=[task for task in tasks if task['seed']==seed and public_block(task)==BLOCK_AST]
        bank=[{'task':task,
               'record':{**by_record[task['id']],
                         'first_probe':{'top20_entropy':by_record[task['id']]['first_probe']['top20_entropy']}},
               'matrix':predicted[task['id']],'correct':[0,0,0]} for task in group]
        path=simulate(bank,model,'conditional')
        frozen=traces[str(seed)]
        assert path['trace']==frozen['trace']
        assert dict(zip([t['id'] for t in group],path['actions']))==frozen['actions']
        assert sum(frozen['actions'].values())==8
        actions+=len(path['trace'])
        for task in group:
            key=task['id'];count=frozen['actions'][key];record=by_record[key]
            value,used=(probe_result(task,record,predicted[key],labels_by_id[key],
                                      'top20_entropy',count) if count else
                        (bool(labels_by_id[key][record['order'][0]]),[]))
            by_outcome[key]['correct']['adaptive']=value
            by_outcome[key]['correct']['sharp_adaptive']=value
            by_outcome[key]['query_indices']['adaptive']=used
    assert outcomes==stored['tasks']
    for bank in stored['summary']['by_bank']:
        group=[r for r in outcomes if r['seed']==bank['seed']]
        assert len(group)==48
        for name in POLICIES:
            assert sum(r['correct'][name] for r in group)==bank['correct'][name]
    for family in FAMILIES:
        group=[r for r in outcomes if r['family']==family]
        for name in POLICIES:
            assert sum(r['correct'][name] for r in group)==stored['summary']['by_family'][family]['correct'][name]
    result={'passed':True,'tasks':len(tasks),'candidate_labels_rechecked':checked,
            'adaptive_actions_replayed':actions,'banks_rechecked':len(SEEDS)}
    write_json(DEST/'audit_score.json',result)
    print(json.dumps(result,indent=2))


def final():
    a=json.loads((DEST/'audit_prepare.json').read_text())
    b=json.loads((DEST/'audit_score.json').read_text())
    assert a['passed'] and b['passed']
    result={'passed':True,'prepare':a,'score':b}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'final':final}[sys.argv[1]]()
