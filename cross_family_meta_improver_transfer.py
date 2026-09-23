"""Fresh parent/admission/child test for bounded evaluator training-rule edits."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_family_query_value_development import choose as fixed_choose,CONTROLS
from cross_family_meta_improver_development import (PARENTS as SOURCE_PARENTS,
    OUT as DEVELOPMENT,parent_tables,train_state,fit_method,values,select,
    matrix,previous_panel)


DEST=ROOT/'runs/cross-family-meta-improver-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-cross-family-meta-improver-transfer.md'
TEMP=ROOT/'analysis/temperature-ranker-development.json'
RANKER=ROOT/'analysis/ast-feedback-replay-model.json'
STAGES={'admission':tuple(range(902420,902426)),
        'a':tuple(range(902426,902432)),
        'b':tuple(range(902432,902438))}
PARENTS=('initial','later','scrambled','duplicate')
FROZEN=('parent_initial','parent_later','fixed_10','fixed_100')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for(stage):
    return [{**task,'seed':seed} for seed in STAGES[stage]
            for task in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]


def stage_rows(stage):
    directory=DEST/stage
    records=json.loads((directory/'frozen_records.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert all(r['id']==o['id'] for r,o in zip(records,outcomes))
    return [{'id':r['id'],'seed':r['seed'],'family':r['family'],
             'public_block':r['public_block'],'features':r['features'],
             'zero':int(o['zero']),'one':int(o['one']),
             'gain':int(o['one'])-int(o['zero'])} for r,o in zip(records,outcomes)]


def train_children():
    if (DEST/'child_models.json').exists():raise RuntimeError('children already exist')
    tables=parent_tables();extra=stage_rows('admission')
    assert len(extra)==288
    states={name:train_state(tables[name]+extra)[0] for name in PARENTS}
    parents=json.loads((DEST/'parent_models.json').read_text())
    states['parent_initial']=parents['initial']
    states['parent_later']=parents['later']
    later_rows=tables['later']+extra
    for penalty in (10,100):
        method=f'interaction_{penalty}'
        states[f'fixed_{penalty}']={'source_tasks':len(later_rows),
                                   'selected_method':method,
                                   'model':fit_method(later_rows,method),
                                   'source_task_ids':[r['id'] for r in later_rows]}
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    gate=admission_gate(admission)
    write_json(DEST/'admission_gate.json',gate)
    write_json(DEST/'child_models.json',states)
    write_json(DEST/'child_training.json',{
        'admission_results_sha256':sha(DEST/'admission/results.json'),
        'source_manifest_sha256':sha(DEST/'source_manifest.json'),
        'new_task_ids':[r['id'] for r in extra],
        'child_methods':{name:states[name]['selected_method'] for name in PARENTS}})
    return {'gate':gate,'child_methods':{name:states[name]['selected_method']
                                         for name in PARENTS},
            'child_source_tasks':{name:states[name]['source_tasks'] for name in PARENTS}}


def admission_gate(summary):
    diffs=[b['correct']['later']-b['correct']['transform_mutation']
           for b in summary['by_bank']]
    return {'differences':diffs,'sum':sum(diffs),
            'positive_banks':sum(d>0 for d in diffs),
            'losing_banks':sum(d<0 for d in diffs),
            'admit':sum(diffs)>=3 and sum(d>0 for d in diffs)>=4
                    and sum(d<0 for d in diffs)<=1}


def prepare_parents():
    if DEST.exists():raise RuntimeError('run already exists')
    tables=parent_tables()
    states={name:train_state(tables[name])[0] for name in PARENTS}
    assert states==json.loads(SOURCE_PARENTS.read_text())
    source={'protocol_sha256':sha(PROTOCOL),
            'development_sha256':sha(DEVELOPMENT),
            'parent_source_sha256':sha(SOURCE_PARENTS),
            'prior_effects_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (
                ROOT/'analysis/cross-family-probe-prior-development.json',
                ROOT/'analysis/cross-family-probe-development.json',
                ROOT/'runs/cross-family-query-transfer-20260918/a/results.json')},
            'parent_tasks':{name:len(tables[name]) for name in PARENTS}}
    write_json(DEST/'source_manifest.json',source)
    write_json(DEST/'parent_models.json',states)
    return {'parent_methods':{name:states[name]['selected_method'] for name in PARENTS},
            'parent_sha256':sha(DEST/'parent_models.json')}


def allocations(tasks,records,states,gate=None):
    by_id={r['id']:r for r in records};result={}
    for seed in sorted({t['seed'] for t in tasks}):
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        assert len(group)==48
        choice={name:sorted(fixed_choose(group,name)) for name in CONTROLS}
        for name,state in states.items():
            choice[name]=sorted(select(group,state['model']))
        if gate is not None:
            choice['protected_later']=(choice['later'] if gate['admit'] else
                                       choice['transform_mutation'])
        assert all(len(v)==8 for v in choice.values())
        result[str(seed)]=choice
    return result


def prepare_stage(stage):
    directory=DEST/stage
    if directory.exists():raise RuntimeError(f'{stage} already prepared')
    start=time.perf_counter();tasks=tasks_for(stage)
    base,wide,times=pools_for(tasks)
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    evaluators=evaluator_models();replay=updated_model();records=[]
    for task in tasks:
        key=task['id'];block=public_block(task);rows=wide.get(key,base[key])
        model=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,order=rank(task,rows,model)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(rows))),[],'top20_entropy')
        x=features(task,{'scores':scores,'order':order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        records.append({'id':key,'seed':task['seed'],'family':task['family'],
                        'public_block':block,'base_sha256':digest(base[key]),
                        'pool_sha256':digest(rows),'scores':scores,'order':order,
                        'first_probe':first,'features':x.tolist()})
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    states=json.loads(model_path.read_text())
    gate=json.loads((DEST/'admission_gate.json').read_text()) if stage!='admission' else None
    choice=allocations(tasks,records,states,gate)
    manifest={'stage':stage,'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'cross_family_meta_improver_transfer.py'),
              'sensor_sha256':sha(ROOT/'ast_probe_sensor_development.py'),
              'temperature_sha256':sha(TEMP),'ranker_sha256':sha(RANKER),
              'models_sha256':sha(model_path),
              'gate_sha256':sha(DEST/'admission_gate.json') if gate else None,
              'seeds':STAGES[stage],'tasks':len(tasks),'calls_per_bank':8,
              'base_candidates':sum(len(v) for v in base.values()),
              'ast_wide_candidates':sum(len(v) for v in wide.values()),
              'candidate_output_cells':sum(len(wide.get(t['id'],base[t['id']]))*8
                                           for t in tasks),
              'generation_seconds':sum(times.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(directory/'sealed_bank.json',tasks)
    write_json(directory/'base_pools.json',base)
    write_json(directory/'ast_wide_pools.json',wide)
    write_json(directory/'predicted_probe_outputs.json',predicted)
    write_json(directory/'frozen_records.json',records)
    write_json(directory/'frozen_allocations.json',choice)
    write_json(directory/'manifest.json',manifest)
    return manifest


def score_stage(stage):
    directory=DEST/stage
    if (directory/'results.json').exists():raise RuntimeError(f'{stage} already scored')
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'cross_family_meta_improver_transfer.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['temperature_sha256']==sha(TEMP)
    assert manifest['ranker_sha256']==sha(RANKER)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    assert manifest['models_sha256']==sha(model_path)
    if stage!='admission':assert manifest['gate_sha256']==sha(DEST/'admission_gate.json')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    choice=json.loads((directory/'frozen_allocations.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        assert key==record['id'] and record['pool_sha256']==digest(pool)
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in pool]
        checked+=len(labels)
        order=record['order'];first=record['first_probe']
        matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matching if matching else set(range(len(pool)))
        selected=next(i for i in order if i in remaining)
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'zero':bool(labels[order[0]]),
                         'one':bool(labels[selected]),'selected_after_query':selected})
    banks=[]
    for seed in STAGES[stage]:
        group=[r for r in outcomes if r['seed']==seed]
        scores={name:sum(r['one'] if r['id'] in set(ids) else r['zero'] for r in group)
                for name,ids in choice[str(seed)].items()}
        banks.append({'seed':seed,'reachable':sum(r['reachable'] for r in group),
                      'no_query':sum(r['zero'] for r in group),
                      'one_each_all':sum(r['one'] for r in group),
                      'correct':scores})
    names=tuple(banks[0]['correct'])
    summary={'stage':stage,'tasks':len(tasks),'candidate_labels_checked':checked,
             'reachable':sum(r['reachable'] for r in outcomes),
             'no_query':sum(b['no_query'] for b in banks),
             'one_each_all':sum(b['one_each_all'] for b in banks),
             'logical_calls_per_policy':8*len(banks),
             'acquisition_probe_calls':len(tasks) if stage=='admission' else 0,
             'correct':{name:sum(b['correct'][name] for b in banks) for name in names},
             'by_bank':banks}
    write_json(directory/'results.json',{'summary':summary,'tasks':outcomes})
    return summary


def interval(diffs):
    counts={0:1}
    for _ in diffs:
        nxt={}
        for total,count in counts.items():
            for d in diffs:nxt[total+d]=nxt.get(total+d,0)+count
        counts=nxt
    total=len(diffs)**len(diffs);cumulative=0;lower=upper=None
    for value,count in sorted(counts.items()):
        cumulative+=count
        if lower is None and cumulative/total>=.025:lower=value
        if upper is None and cumulative/total>=.975:upper=value
    return [lower,upper]


def summarize():
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    panels={name:json.loads((DEST/name/'results.json').read_text())['summary']
            for name in ('a','b')}
    banks=panels['a']['by_bank']+panels['b']['by_bank']
    names=tuple(banks[0]['correct'])
    correct={name:sum(b['correct'][name] for b in banks) for name in names}
    fixed_best=max(CONTROLS,key=lambda name:correct[name])
    diffs=[b['correct']['later']-b['correct']['initial'] for b in banks]
    ci=interval(diffs)
    gate=json.loads((DEST/'admission_gate.json').read_text())
    passed=(sum(d>0 for d in diffs)>=8 and ci[0]>0 and gate['admit'] and
            correct['later']>correct['parent_later'] and
            correct['later']>correct[fixed_best] and
            all(correct['later']>correct[name] for name in
                ('scrambled','duplicate')) and
            correct['later']>=max(correct['fixed_10'],correct['fixed_100']))
    return {'scope':'bounded cross-family training-rule improver transfer',
            'admission':admission,'admission_gate':gate,
            'transfer':{'tasks':sum(p['tasks'] for p in panels.values()),
                        'logical_calls_per_policy':96,'correct':correct,
                        'reachable':sum(p['reachable'] for p in panels.values()),
                        'no_query':sum(p['no_query'] for p in panels.values()),
                        'by_panel':{name:p['correct'] for name,p in panels.items()},
                        'by_bank':banks},
            'primary_child_gate':{'strongest_fixed':fixed_best,
                                  'differences':diffs,'positive_banks':sum(d>0 for d in diffs),
                                  'bank_bootstrap_95_sum':ci,'passed':passed},
            'source_tasks':{'initial':576,'later':864},
            'shared_new_admission_tasks':288,'shared_new_probe_outputs':288}


def final():
    result=summarize()
    write_json(DEST/'summary.json',result)
    return {'admission_gate':result['admission_gate'],
            'transfer_correct':result['transfer']['correct'],
            'primary_child_gate':result['primary_child_gate']}


if __name__=='__main__':
    actions={'parents':prepare_parents,'prepare_admission':lambda:prepare_stage('admission'),
             'score_admission':lambda:score_stage('admission'),
             'children':train_children,'prepare_a':lambda:prepare_stage('a'),
             'prepare_b':lambda:prepare_stage('b'),
             'score_a':lambda:score_stage('a'),'score_b':lambda:score_stage('b'),
             'final':final}
    print(json.dumps(actions[sys.argv[1]](),indent=2))
