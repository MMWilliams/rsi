"""Fresh six-mechanism comparison of evaluator, search and sensor edits."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,FIXED,BLOCK_AST
from gated_ast_replay_integration import models as evaluator_models,select as evaluator_select
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from full_mixed_ast_sensor import probe_result
from adaptive_ast_query_development import simulate
from adaptive_ast_improver import unserialize


DEST=ROOT/'runs/cross-component-mixed-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-cross-component-mixed-transfer.md'
TEMP=ROOT/'analysis/temperature-ranker-development.json'
RANKER=ROOT/'analysis/ast-feedback-replay-model.json'
ADAPTIVE=ROOT/'runs/adaptive-ast-improver-20260918/child_models.json'
SEEDS=tuple(range(902402,902408))
POLICIES=('fixed_map','sharp_global','ast_ranker','sharp_ast_ranker',
          'top20_one','sharp_top20_one','minimax_one','sharp_minimax_one',
          'adaptive','sharp_adaptive')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for():
    return [{**task,'seed':seed} for seed in SEEDS
            for task in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    start=time.perf_counter()
    tasks=tasks_for()
    base,wide,times=pools_for(tasks)
    ast=[t for t in tasks if public_block(t)==BLOCK_AST]
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             wide[t['id']]) for t in ast]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    evaluators=evaluator_models();ranker=updated_model()
    decisions=[]
    for task in tasks:
        key=task['id'];block=public_block(task);rows=wide.get(key,base[key])
        choice=evaluator_select(task,rows,evaluators)
        entry={'id':key,'seed':task['seed'],'family':task['family'],
               'public_block':block,'base_sha256':digest(base[key]),
               'wide_sha256':digest(rows),'fixed_temperature':FIXED[block],
               'fixed_choice':choice[FIXED[block]],
               'sharp_choice':choice['temp_0.25']}
        if block==BLOCK_AST:
            scores,order=rank(task,rows,ranker)
            first={mode:choose_probe(key,predicted[key],order,scores,
                                     set(range(len(rows))),[],mode)
                   for mode in ('top20_entropy','minimax')}
            entry.update({'scores':scores,'order':order,'first_probe':first})
        decisions.append(entry)
    manifest={'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'cross_component_mixed_transfer.py'),
              'sensor_sha256':sha(ROOT/'ast_probe_sensor_development.py'),
              'model_sha256':{'temperature':sha(TEMP),'ranker':sha(RANKER),
                              'adaptive':sha(ADAPTIVE)},
              'seeds':SEEDS,'tasks':len(tasks),'calls_per_bank':8,
              'base_candidates':sum(len(v) for v in base.values()),
              'ast_wide_candidates':sum(len(v) for v in wide.values()),
              'predicted_output_cells':sum(len(v)*8 for v in wide.values()),
              'generation_seconds':sum(times.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'base_pools.json',base)
    write_json(DEST/'ast_wide_pools.json',wide)
    write_json(DEST/'predicted_probe_outputs.json',predicted)
    write_json(DEST/'frozen_decisions.json',decisions)
    write_json(DEST/'manifest.json',manifest)
    return manifest


def score():
    if (DEST/'results.json').exists():raise RuntimeError('results already exist')
    manifest=json.loads((DEST/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'cross_component_mixed_transfer.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['model_sha256']=={'temperature':sha(TEMP),'ranker':sha(RANKER),
                                     'adaptive':sha(ADAPTIVE)}
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    decisions=json.loads((DEST/'frozen_decisions.json').read_text())
    outcomes=[]
    for task,record in zip(tasks,decisions):
        key=task['id'];block=public_block(task);old=base[key];rows=wide.get(key,old)
        assert key==record['id'] and record['base_sha256']==digest(old)
        assert record['wide_sha256']==digest(rows) and block==record['public_block']
        base_labels=[bool(evaluate_program(row['program'],task['hidden'][8:]))
                     for row in old]
        labels=base_labels if rows is old else [bool(evaluate_program(
            row['program'],task['hidden'][8:])) for row in rows]
        fixed=bool(labels[record['fixed_choice']]);sharp=bool(labels[record['sharp_choice']])
        correct={name:(sharp if name.startswith('sharp') else fixed) for name in POLICIES}
        queries={}
        if block==BLOCK_AST:
            correct['ast_ranker']=bool(labels[record['order'][0]])
            correct['sharp_ast_ranker']=correct['ast_ranker']
            for name,mode in (('top20_one','top20_entropy'),('minimax_one','minimax')):
                value,used=probe_result(task,record,predicted[key],labels,mode,1)
                correct[name]=value;correct['sharp_'+name]=value
                queries[name]=used
            # Adaptive actions are determined after each purchased true output.
            correct['adaptive']=correct['ast_ranker']
            correct['sharp_adaptive']=correct['ast_ranker']
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'base_reachable':any(base_labels),'wide_reachable':any(labels),
                         'correct':correct,'query_indices':queries})
    by_task={t['id']:t for t in tasks};by_decision={r['id']:r for r in decisions}
    by_outcome={r['id']:r for r in outcomes}
    model=unserialize(json.loads(ADAPTIVE.read_text())['conditional1'])
    traces={}
    for seed in SEEDS:
        group=[task for task in tasks if task['seed']==seed and public_block(task)==BLOCK_AST]
        assert len(group)==8
        bank=[{'task':task,
               'record':{**by_decision[task['id']],
                         'first_probe':{'top20_entropy':by_decision[task['id']]['first_probe']['top20_entropy']}},
               'matrix':predicted[task['id']],'correct':[0,0,0]}
              for task in group]
        path=simulate(bank,model,'conditional')
        mapping=dict(zip([t['id'] for t in group],path['actions']))
        traces[str(seed)]={'actions':mapping,'trace':path['trace']}
        for task in group:
            key=task['id'];count=mapping[key]
            record=by_decision[key];rows=wide[key]
            labels=[bool(evaluate_program(row['program'],task['hidden'][8:]))
                    for row in rows]
            value,used=(probe_result(task,record,predicted[key],labels,
                                      'top20_entropy',count) if count
                        else (bool(labels[record['order'][0]]),[]))
            by_outcome[key]['correct']['adaptive']=value
            by_outcome[key]['correct']['sharp_adaptive']=value
            by_outcome[key]['query_indices']['adaptive']=used
    def agg(rows):
        return {'tasks':len(rows),'base_reachable':sum(r['base_reachable'] for r in rows),
                'wide_reachable':sum(r['wide_reachable'] for r in rows),
                'correct':{name:sum(r['correct'][name] for r in rows) for name in POLICIES}}
    banks=[{'seed':seed,**agg([r for r in outcomes if r['seed']==seed])} for seed in SEEDS]
    summary={'scope':'fresh six-mechanism cross-component edit transfer',
             'overall':agg(outcomes),'by_bank':banks,
             'by_family':{f:agg([r for r in outcomes if r['family']==f]) for f in FAMILIES},
             'sharp_minus_map_by_bank':[b['correct']['sharp_global']-
                                         b['correct']['fixed_map'] for b in banks],
             'adaptive_minus_top20_by_bank':[b['correct']['adaptive']-
                                               b['correct']['top20_one'] for b in banks]}
    write_json(DEST/'adaptive_traces.json',traces)
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    return summary


if __name__=='__main__':
    print(json.dumps({'prepare':prepare,'score':score}[sys.argv[1]](),indent=2))
