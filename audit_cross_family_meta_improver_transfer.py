"""Independent regeneration and oracle replay of the bounded meta-improver test."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_family_query_value_development import choose as fixed_choose,CONTROLS
from cross_family_meta_improver_development import parent_tables,train_state,fit_method,select
from cross_family_meta_improver_transfer import (DEST,PROTOCOL,TEMP,RANKER,
    STAGES,PARENTS,sha,tasks_for,admission_gate,summarize)


def source():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['development_sha256']==sha(ROOT/'analysis/cross-family-meta-improver-development.json')
    assert manifest['parent_source_sha256']==sha(ROOT/'analysis/cross-family-meta-improver-parent-models.json')
    for name,value in manifest['prior_effects_sha256'].items():
        assert value==sha(ROOT/name)
    tables=parent_tables()
    assert manifest['parent_tasks']=={name:len(tables[name]) for name in PARENTS}
    parents={name:train_state(tables[name])[0] for name in PARENTS}
    assert parents==json.loads((DEST/'parent_models.json').read_text())
    result={'passed':True,'parent_tasks':manifest['parent_tasks'],'parents_retrained':4}
    write_json(DEST/'audit_source.json',result)
    print(json.dumps(result,indent=2))


def read(stage):
    directory=DEST/stage
    return tuple(json.loads((directory/name).read_text()) for name in (
        'manifest.json','sealed_bank.json','base_pools.json','ast_wide_pools.json',
        'predicted_probe_outputs.json','frozen_records.json','frozen_allocations.json'))


def check_manifest(stage,manifest):
    assert manifest['stage']==stage and tuple(manifest['seeds'])==STAGES[stage]
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'cross_family_meta_improver_transfer.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['temperature_sha256']==sha(TEMP)
    assert manifest['ranker_sha256']==sha(RANKER)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    assert manifest['models_sha256']==sha(model_path)
    assert manifest['gate_sha256']==(None if stage=='admission' else sha(DEST/'admission_gate.json'))


def children():
    tables=parent_tables()
    records=json.loads((DEST/'admission/frozen_records.json').read_text())
    outcomes=json.loads((DEST/'admission/results.json').read_text())['tasks']
    assert len(records)==len(outcomes)==288
    extra=[]
    for r,o in zip(records,outcomes):
        assert r['id']==o['id']
        extra.append({'id':r['id'],'seed':r['seed'],'family':r['family'],
                      'public_block':r['public_block'],'features':r['features'],
                      'zero':int(o['zero']),'one':int(o['one']),
                      'gain':int(o['one'])-int(o['zero'])})
    states={name:train_state(tables[name]+extra)[0] for name in PARENTS}
    parents=json.loads((DEST/'parent_models.json').read_text())
    states['parent_initial']=parents['initial'];states['parent_later']=parents['later']
    later_rows=tables['later']+extra
    for penalty in (10,100):
        method=f'interaction_{penalty}'
        states[f'fixed_{penalty}']={'source_tasks':len(later_rows),
                                   'selected_method':method,
                                   'model':fit_method(later_rows,method),
                                   'source_task_ids':[r['id'] for r in later_rows]}
    assert states==json.loads((DEST/'child_models.json').read_text())
    summary=json.loads((DEST/'admission/results.json').read_text())['summary']
    assert admission_gate(summary)==json.loads((DEST/'admission_gate.json').read_text())
    training=json.loads((DEST/'child_training.json').read_text())
    assert training['new_task_ids']==[r['id'] for r in extra]
    assert training['admission_results_sha256']==sha(DEST/'admission/results.json')
    result={'passed':True,'shared_new_tasks':len(extra),
            'child_methods':training['child_methods'],'states_retrained':len(states)}
    write_json(DEST/'audit_children.json',result)
    print(json.dumps(result,indent=2))


def prepare(stage):
    manifest,tasks,base,wide,predicted,records,choices=read(stage)
    check_manifest(stage,manifest)
    assert tasks==tasks_for(stage)
    regenerated,regenerated_wide,_=pools_for(tasks)
    assert regenerated==base and regenerated_wide==wide
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    evaluators=evaluator_models();replay=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];block=public_block(task);rows=wide.get(key,base[key])
        assert key==record['id'] and block==record['public_block']
        assert record['base_sha256']==digest(base[key])
        assert record['pool_sha256']==digest(rows)
        model=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,order=rank(task,rows,model)
        assert order==record['order'] and np.allclose(scores,record['scores'],atol=1e-6)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(rows))),[],'top20_entropy')
        assert first==record['first_probe']
        x=features(task,{'scores':scores,'order':order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        assert np.allclose(x,record['features'],atol=1e-6)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    states=json.loads(model_path.read_text())
    gate=json.loads((DEST/'admission_gate.json').read_text()) if stage!='admission' else None
    lookup={r['id']:r for r in records};rebuilt={}
    for seed in STAGES[stage]:
        group=[lookup[t['id']] for t in tasks if t['seed']==seed]
        assert len(group)==48
        bank={name:sorted(fixed_choose(group,name)) for name in CONTROLS}
        for name,state in states.items():
            bank[name]=sorted(select(group,state['model']))
        if gate is not None:
            bank['protected_later']=(bank['later'] if gate['admit'] else
                                     bank['transform_mutation'])
        rebuilt[str(seed)]=bank
    assert rebuilt==choices
    result={'passed':True,'stage':stage,'tasks':len(tasks),
            'base_candidates_rechecked':sum(map(len,base.values())),
            'ast_wide_candidates_rechecked':sum(map(len,wide.values())),
            'predicted_output_cells_rechecked':sum(len(wide.get(t['id'],base[t['id']]))*8
                                                 for t in tasks),
            'allocations_rechecked':len(STAGES[stage])*len(next(iter(choices.values())))}
    write_json(DEST/f'audit_prepare_{stage}.json',result)
    print(json.dumps(result,indent=2))


def score(stage):
    manifest,tasks,base,wide,predicted,records,choices=read(stage)
    check_manifest(stage,manifest)
    saved=json.loads((DEST/stage/'results.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in pool]
        checked+=len(labels)
        order=record['order'];first=record['first_probe']
        matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matching if matching else set(range(len(pool)))
        selected=next(i for i in order if i in remaining)
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'zero':bool(labels[order[0]]),
                         'one':bool(labels[selected]),'selected_after_query':selected})
    assert outcomes==saved['tasks']
    summary=saved['summary']
    assert summary['candidate_labels_checked']==checked
    assert summary['reachable']==sum(r['reachable'] for r in outcomes)
    for bank in summary['by_bank']:
        group=[r for r in outcomes if r['seed']==bank['seed']]
        assert len(group)==48
        assert bank['no_query']==sum(r['zero'] for r in group)
        assert bank['one_each_all']==sum(r['one'] for r in group)
        for policy,ids in choices[str(bank['seed'])].items():
            assert len(ids)==len(set(ids))==8
            assert bank['correct'][policy]==sum(r['one'] if r['id'] in set(ids) else r['zero'] for r in group)
    assert summary['correct']=={name:sum(b['correct'][name] for b in summary['by_bank'])
                                for name in summary['correct']}
    result={'passed':True,'stage':stage,'tasks':len(tasks),
            'candidate_labels_rechecked':checked,
            'bank_policy_scores_rechecked':len(STAGES[stage])*len(summary['correct'])}
    write_json(DEST/f'audit_score_{stage}.json',result)
    print(json.dumps(result,indent=2))


def final():
    names=('source','prepare_admission','score_admission','children',
           'prepare_a','score_a','prepare_b','score_b')
    parts={name:json.loads((DEST/f'audit_{name}.json').read_text()) for name in names}
    assert all(p['passed'] for p in parts.values())
    for stage in STAGES:
        _,tasks,_,_,_,records,choices=read(stage)
        model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
        states=json.loads(model_path.read_text())
        gate=json.loads((DEST/'admission_gate.json').read_text()) if stage!='admission' else None
        lookup={r['id']:r for r in records};rebuilt={}
        for seed in STAGES[stage]:
            group=[lookup[t['id']] for t in tasks if t['seed']==seed]
            bank={name:sorted(fixed_choose(group,name)) for name in CONTROLS}
            for name,state in states.items():bank[name]=sorted(select(group,state['model']))
            if gate is not None:
                bank['protected_later']=(bank['later'] if gate['admit'] else
                                         bank['transform_mutation'])
            rebuilt[str(seed)]=bank
        assert rebuilt==choices
    reported=json.loads((DEST/'summary.json').read_text())
    assert summarize()==reported
    banks=[bank for stage in ('a','b') for bank in
           json.loads((DEST/stage/'results.json').read_text())['summary']['by_bank']]
    diffs=[b['correct']['later']-b['correct']['initial'] for b in banks]
    assert reported['primary_child_gate']['differences']==diffs
    assert reported['primary_child_gate']['positive_banks']==sum(d>0 for d in diffs)
    assert reported['transfer']['correct']=={name:sum(b['correct'][name] for b in banks)
                                            for name in banks[0]['correct']}
    result={'passed':True,'independent_allocations_rechecked':240,'parts':parts}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    actions={'source':source,'children':children,'final':final}
    for stage in STAGES:
        actions[f'prepare_{stage}']=lambda stage=stage:prepare(stage)
        actions[f'score_{stage}']=lambda stage=stage:score(stage)
    actions[sys.argv[1]]()
