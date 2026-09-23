"""Prospective four-slot AST width and sensor package parent/child transfer."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from ast_width_value_development import choose as width_choose,fit as width_fit
from ast_width_improver_development import tables,train_state,PARENTS,OUT as DEVELOPMENT,NAMES
from cross_family_meta_improver_transfer import interval


DEST=ROOT/'runs/ast-width-improver-transfer-20260918-v2'
PROTOCOL=ROOT/'EXPERIMENT-ast-width-improver-transfer.md'
TEMP=ROOT/'analysis/temperature-ranker-development.json'
RANKER=ROOT/'analysis/ast-feedback-replay-model.json'
STAGES={'admission':tuple(range(902468,902474)),
        'a':tuple(range(902474,902480)),
        'b':tuple(range(902480,902486))}
WIDTH_CONTROLS=('random','low_gap','high_entropy')
SOURCE_FILES=tuple(ROOT/f'analysis/ast-width-query-counterfactuals-{run}-{stage}-20260918.json'
                   for run,stages in (('meta',('admission','a','b')),
                                      ('stable',('a','b')))
                   for stage in stages)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for(stage):
    return [{**task,'seed':seed} for seed in STAGES[stage]
            for task in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]


def source():
    if DEST.exists():raise RuntimeError('run already exists')
    sources=tables()
    states={name:train_state(sources[name])[0] for name in NAMES}
    assert states==json.loads(PARENTS.read_text())
    manifest={'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'ast_width_improver_transfer.py'),
              'trainer_sha256':sha(ROOT/'ast_width_improver_development.py'),
              'value_sha256':sha(ROOT/'ast_width_value_development.py'),
              'development_sha256':sha(DEVELOPMENT),
              'source_models_sha256':sha(PARENTS),
              'source_files_sha256':{str(p.relative_to(ROOT)):sha(p) for p in SOURCE_FILES},
              'parent_rows':{name:len(sources[name]) for name in NAMES}}
    write_json(DEST/'source_manifest.json',manifest)
    write_json(DEST/'parent_models.json',states)
    return {'source_manifest_sha256':sha(DEST/'source_manifest.json'),
            'parent_rows':manifest['parent_rows']}


def admission_rows():
    records=json.loads((DEST/'admission/frozen_records.json').read_text())
    outcomes=json.loads((DEST/'admission/results.json').read_text())['tasks']
    assert len(records)==len(outcomes)==288
    rows=[]
    for r,o in zip(records,outcomes):
        assert r['id']==o['id']
        if r['public_block']!=BLOCK_AST:continue
        rows.append({'id':r['id'],'seed':r['seed'],'family':r['family'],
                     'public_block':r['public_block'],'base_features':r['base_features'],
                     'base_one':int(o['base_one']),'wide_one':int(o['wide_one']),
                     'width_one_effect':int(o['wide_one'])-int(o['base_one'])})
    assert len(rows)==48
    return rows


def admission_gate(summary):
    diffs=[b['correct']['later']-b['correct']['random'] for b in summary['by_bank']]
    return {'differences':diffs,'sum':sum(diffs),
            'positive_banks':sum(d>0 for d in diffs),
            'losing_banks':sum(d<0 for d in diffs),
            'later_minus_initial':summary['correct']['later']-summary['correct']['initial'],
            'admit':sum(diffs)>=2 and sum(d>0 for d in diffs)>=4
                    and sum(d<0 for d in diffs)<=1
                    and summary['correct']['later']>=summary['correct']['initial']}


def children():
    if (DEST/'child_models.json').exists():raise RuntimeError('children already exist')
    sources=tables();extra=admission_rows()
    states={name:train_state(sources[name]+extra)[0] for name in NAMES}
    parents=json.loads((DEST/'parent_models.json').read_text())
    states['parent_initial']=parents['initial'];states['parent_later']=parents['later']
    summary=json.loads((DEST/'admission/results.json').read_text())['summary']
    gate=admission_gate(summary)
    write_json(DEST/'admission_gate.json',gate)
    write_json(DEST/'child_models.json',states)
    write_json(DEST/'child_training.json',{
        'admission_results_sha256':sha(DEST/'admission/results.json'),
        'new_task_ids':[r['id'] for r in extra],
        'source_rows':{name:states[name]['source_rows'] for name in NAMES}})
    return {'admission_gate':gate,
            'child_source_rows':{name:states[name]['source_rows'] for name in NAMES}}


def allocations(tasks,records,states,gate=None):
    lookup={r['id']:r for r in records};result={}
    for seed in sorted({t['seed'] for t in tasks}):
        group=[lookup[t['id']] for t in tasks if t['seed']==seed
               and lookup[t['id']]['public_block']==BLOCK_AST]
        assert len(group)==8
        choice={name:sorted(width_choose(group,name)) for name in WIDTH_CONTROLS}
        for name,state in states.items():
            choice[name]=sorted(width_choose(group,'ridge_10',state['model']))
        if gate is not None:
            choice['protected_later']=(choice['later'] if gate['admit'] else choice['low_gap'])
        assert all(len(ids)==4 for ids in choice.values())
        result[str(seed)]=choice
    return result


def prepare(stage):
    directory=DEST/stage
    if directory.exists():raise RuntimeError(f'{stage} already prepared')
    start=time.perf_counter();tasks=tasks_for(stage)
    base,wide,times=pools_for(tasks)
    ast=[t for t in tasks if public_block(t)==BLOCK_AST]
    assert len(ast)==len(STAGES[stage])*8
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},wide[t['id']])
            for t in ast]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    evaluators=evaluator_models();replay=updated_model();records=[]
    for task in tasks:
        key=task['id'];block=public_block(task);old=base[key]
        row={'id':key,'seed':task['seed'],'family':task['family'],
             'public_block':block,'base_sha256':digest(old),
             'pool_sha256':digest(wide.get(key,old)),
             'extra_candidates':len(wide[key])-len(old) if block==BLOCK_AST else 0}
        if block==BLOCK_AST:
            pool=wide[key];mapping={v['program']:i for i,v in enumerate(pool)}
            base_to_wide=[mapping[v['program']] for v in old]
            matrix_base=[predicted[key][i] for i in base_to_wide]
            base_scores,base_order=rank(task,old,replay)
            wide_scores,wide_order=rank(task,pool,replay)
            base_first=choose_probe(key,matrix_base,base_order,base_scores,
                                    set(range(len(old))),[],'top20_entropy')
            wide_first=choose_probe(key,predicted[key],wide_order,wide_scores,
                                    set(range(len(pool))),[],'top20_entropy')
            x=features(task,{'scores':base_scores,'order':base_order,
                             'first_probe':{'top20_entropy':base_first}},matrix_base)
            row.update({'base_to_wide':base_to_wide,
                        'base_scores':base_scores,'base_order':base_order,
                        'wide_scores':wide_scores,'wide_order':wide_order,
                        'base_first':base_first,'wide_first':wide_first,
                        'base_features':x.tolist()})
        else:
            scores,order=rank(task,old,evaluators[FIXED[block]])
            row.update({'fixed_scores':scores,'fixed_order':order})
        records.append(row)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    states=json.loads(model_path.read_text())
    gate=json.loads((DEST/'admission_gate.json').read_text()) if stage!='admission' else None
    choice=allocations(tasks,records,states,gate)
    manifest={'stage':stage,'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'ast_width_improver_transfer.py'),
              'value_sha256':sha(ROOT/'ast_width_value_development.py'),
              'sensor_sha256':sha(ROOT/'ast_probe_sensor_development.py'),
              'temperature_sha256':sha(TEMP),'ranker_sha256':sha(RANKER),
              'models_sha256':sha(model_path),
              'gate_sha256':sha(DEST/'admission_gate.json') if gate else None,
              'seeds':STAGES[stage],'tasks':len(tasks),'width_slots_per_bank':4,
              'query_calls_per_bank':8,
              'base_candidates':sum(len(v) for v in base.values()),
              'ast_wide_candidates':sum(len(v) for v in wide.values()),
              'predicted_output_cells':sum(len(v)*8 for v in wide.values()),
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


def query_result(task,labels,matrix,order,first):
    matching={i for i in range(len(order)) if matrix[i][first]==task['hidden'][first][1]}
    remaining=matching if matching else set(range(len(order)))
    selected=next(i for i in order if i in remaining)
    return int(labels[selected]),selected


def score(stage):
    directory=DEST/stage
    if (directory/'results.json').exists():raise RuntimeError(f'{stage} already scored')
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'ast_width_improver_transfer.py')
    assert manifest['value_sha256']==sha(ROOT/'ast_width_value_development.py')
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
        key=task['id'];block=record['public_block'];pool=wide.get(key,base[key])
        assert key==record['id'] and record['base_sha256']==digest(base[key])
        assert record['pool_sha256']==digest(pool)
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:]))) for row in pool]
        checked+=len(labels)
        if block==BLOCK_AST:
            base_labels=[labels[i] for i in record['base_to_wide']]
            matrix_base=[predicted[key][i] for i in record['base_to_wide']]
            base_one,base_selected=query_result(task,base_labels,matrix_base,
                                                record['base_order'],record['base_first'])
            wide_one,wide_selected=query_result(task,labels,predicted[key],
                                                record['wide_order'],record['wide_first'])
            values={'base_zero':base_labels[record['base_order'][0]],
                    'base_one':base_one,'wide_zero':labels[record['wide_order'][0]],
                    'wide_one':wide_one,'base_reachable':int(any(base_labels)),
                    'wide_reachable':int(any(labels)),
                    'base_selected':base_selected,'wide_selected':wide_selected,
                    'acquisition_unique_probe_calls':len({record['base_first'],record['wide_first']})}
        else:
            values={'fixed_zero':labels[record['fixed_order'][0]],
                    'base_reachable':int(any(labels)),'wide_reachable':int(any(labels))}
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'public_block':block,**values})
    by_id={r['id']:r for r in outcomes};by_record={r['id']:r for r in records};banks=[]
    for seed in STAGES[stage]:
        group=[t for t in tasks if t['seed']==seed]
        ast=[t for t in group if by_id[t['id']]['public_block']==BLOCK_AST]
        nonast=sum(by_id[t['id']]['fixed_zero'] for t in group if t not in ast)
        fixed_scores={'no_query_base':nonast+sum(by_id[t['id']]['base_zero'] for t in ast),
                      'no_query_fullwide':nonast+sum(by_id[t['id']]['wide_zero'] for t in ast),
                      'base_all':nonast+sum(by_id[t['id']]['base_one'] for t in ast),
                      'fullwide':nonast+sum(by_id[t['id']]['wide_one'] for t in ast)}
        correct=dict(fixed_scores);effective_extra={}
        for name,ids in choice[str(seed)].items():
            selected=set(ids)
            correct[name]=nonast+sum(by_id[t['id']]['wide_one'] if t['id'] in selected
                                     else by_id[t['id']]['base_one'] for t in ast)
            effective_extra[name]=sum(by_record[t['id']]['extra_candidates'] for t in ast
                                      if t['id'] in selected)
        banks.append({'seed':seed,'correct':correct,
                      'effective_extra_candidates':effective_extra,
                      'base_reachable':sum(by_id[t['id']]['base_reachable'] for t in group),
                      'wide_reachable':sum(by_id[t['id']]['wide_reachable'] for t in group),
                      'acquisition_unique_probe_calls':sum(by_id[t['id']]['acquisition_unique_probe_calls']
                                                            for t in ast)})
    names=tuple(banks[0]['correct']);active=tuple(choice[str(STAGES[stage][0])])
    summary={'stage':stage,'tasks':len(tasks),'candidate_labels_checked':checked,
             'base_reachable':sum(b['base_reachable'] for b in banks),
             'wide_reachable':sum(b['wide_reachable'] for b in banks),
             'logical_width_slots_per_policy':4*len(banks),
             'logical_query_calls_per_active_policy':8*len(banks),
             'admission_acquisition_unique_probe_calls':sum(b['acquisition_unique_probe_calls']
                                                             for b in banks) if stage=='admission' else 0,
             'correct':{name:sum(b['correct'][name] for b in banks) for name in names},
             'effective_extra_candidates':{name:sum(b['effective_extra_candidates'][name]
                                                    for b in banks) for name in active},
             'by_bank':banks}
    write_json(directory/'results.json',{'summary':summary,'tasks':outcomes})
    return summary


def summarize():
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    panels={s:json.loads((DEST/s/'results.json').read_text())['summary'] for s in ('a','b')}
    banks=panels['a']['by_bank']+panels['b']['by_bank']
    names=tuple(banks[0]['correct'])
    correct={name:sum(b['correct'][name] for b in banks) for name in names}
    extras={name:sum(b['effective_extra_candidates'][name] for b in banks)
            for name in banks[0]['effective_extra_candidates']}
    diffs=[b['correct']['later']-b['correct']['initial'] for b in banks]
    fixed_diffs=[b['correct']['low_gap']-b['correct']['random'] for b in banks]
    gate=json.loads((DEST/'admission_gate.json').read_text())
    primary=(gate['admit'] and sum(d>0 for d in diffs)>=8 and interval(diffs)[0]>0
             and correct['later']>correct['parent_later']
             and correct['later']>correct['scrambled']
             and correct['later']>correct['duplicate']
             and correct['later']>correct['low_gap']
             and correct['later']>correct['random'])
    fixed=(sum(d>0 for d in fixed_diffs)>=8 and interval(fixed_diffs)[0]>0
           and sum(d<0 for d in fixed_diffs)<=2)
    return {'scope':'AST width/ranker/sensor package transfer in mixed banks',
            'admission':admission,'admission_gate':gate,
            'transfer':{'tasks':sum(p['tasks'] for p in panels.values()),
                        'base_reachable':sum(p['base_reachable'] for p in panels.values()),
                        'wide_reachable':sum(p['wide_reachable'] for p in panels.values()),
                        'logical_width_slots_per_policy':48,
                        'logical_query_calls_per_active_policy':96,
                        'correct':correct,'effective_extra_candidates':extras,
                        'by_panel':{s:p['correct'] for s,p in panels.items()},
                        'by_bank':banks},
            'primary_recursive_gate':{'differences':diffs,
                                      'positive_banks':sum(d>0 for d in diffs),
                                      'bank_bootstrap_95_sum':interval(diffs),
                                      'passed':primary},
            'fixed_component_gate':{'differences':fixed_diffs,
                                    'positive_banks':sum(d>0 for d in fixed_diffs),
                                    'losing_banks':sum(d<0 for d in fixed_diffs),
                                    'bank_bootstrap_95_sum':interval(fixed_diffs),
                                    'passed':fixed},
            'historical_ast_effects':{'initial':144,'later':240},
            'shared_new_admission_ast_effects':48}


def final():
    result=summarize();write_json(DEST/'summary.json',result)
    return {'admission_gate':result['admission_gate'],
            'transfer_correct':result['transfer']['correct'],
            'primary_recursive_gate':result['primary_recursive_gate'],
            'fixed_component_gate':result['fixed_component_gate']}


if __name__=='__main__':
    actions={'source':source,'prepare_admission':lambda:prepare('admission'),
             'score_admission':lambda:score('admission'),'children':children,
             'prepare_a':lambda:prepare('a'),'prepare_b':lambda:prepare('b'),
             'score_a':lambda:score('a'),'score_b':lambda:score('b'),'final':final}
    print(json.dumps(actions[sys.argv[1]](),indent=2))
