"""Independent source, preparation and oracle replay for AST width package transfer."""
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
from ast_width_value_development import choose as width_choose
from ast_width_improver_development import tables,train_state,PARENTS,OUT as DEVELOPMENT,NAMES
from ast_width_improver_transfer import (DEST,PROTOCOL,TEMP,RANKER,STAGES,WIDTH_CONTROLS,
    SOURCE_FILES,sha,tasks_for,admission_gate,summarize)


def source():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'ast_width_improver_transfer.py')
    assert manifest['trainer_sha256']==sha(ROOT/'ast_width_improver_development.py')
    assert manifest['value_sha256']==sha(ROOT/'ast_width_value_development.py')
    assert manifest['development_sha256']==sha(DEVELOPMENT)
    assert manifest['source_models_sha256']==sha(PARENTS)
    assert manifest['source_files_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in SOURCE_FILES}
    sources=tables()
    assert manifest['parent_rows']=={name:len(sources[name]) for name in NAMES}
    parents={name:train_state(sources[name])[0] for name in NAMES}
    assert parents==json.loads((DEST/'parent_models.json').read_text())
    result={'passed':True,'parents_retrained':len(parents),
            'parent_rows':manifest['parent_rows'],'source_files_rechecked':len(SOURCE_FILES)}
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
    assert manifest['runner_sha256']==sha(ROOT/'ast_width_improver_transfer.py')
    assert manifest['value_sha256']==sha(ROOT/'ast_width_value_development.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['temperature_sha256']==sha(TEMP)
    assert manifest['ranker_sha256']==sha(RANKER)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    assert manifest['models_sha256']==sha(model_path)
    assert manifest['gate_sha256']==(None if stage=='admission' else sha(DEST/'admission_gate.json'))


def children():
    sources=tables()
    records=json.loads((DEST/'admission/frozen_records.json').read_text())
    outcomes=json.loads((DEST/'admission/results.json').read_text())['tasks']
    assert len(records)==len(outcomes)==288
    extra=[]
    for r,o in zip(records,outcomes):
        assert r['id']==o['id']
        if r['public_block']!=BLOCK_AST:continue
        extra.append({'id':r['id'],'seed':r['seed'],'family':r['family'],
                      'public_block':r['public_block'],'base_features':r['base_features'],
                      'base_one':int(o['base_one']),'wide_one':int(o['wide_one']),
                      'width_one_effect':int(o['wide_one'])-int(o['base_one'])})
    assert len(extra)==48
    states={name:train_state(sources[name]+extra)[0] for name in NAMES}
    parents=json.loads((DEST/'parent_models.json').read_text())
    states['parent_initial']=parents['initial'];states['parent_later']=parents['later']
    assert states==json.loads((DEST/'child_models.json').read_text())
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    assert admission_gate(admission)==json.loads((DEST/'admission_gate.json').read_text())
    training=json.loads((DEST/'child_training.json').read_text())
    assert training['admission_results_sha256']==sha(DEST/'admission/results.json')
    assert training['new_task_ids']==[r['id'] for r in extra]
    result={'passed':True,'shared_new_ast_effects':len(extra),'states_retrained':len(states)}
    write_json(DEST/'audit_children.json',result)
    print(json.dumps(result,indent=2))


def prepare(stage):
    manifest,tasks,base,wide,predicted,records,choices=read(stage)
    check_manifest(stage,manifest)
    assert tasks==tasks_for(stage)
    regenerated,regenerated_wide,_=pools_for(tasks)
    assert regenerated==base and regenerated_wide==wide
    ast=[t for t in tasks if public_block(t)==BLOCK_AST]
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},wide[t['id']])
            for t in ast]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    evaluators=evaluator_models();replay=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];block=public_block(task);old=base[key]
        assert key==record['id'] and block==record['public_block']
        assert record['base_sha256']==digest(old)
        assert record['pool_sha256']==digest(wide.get(key,old))
        if block==BLOCK_AST:
            pool=wide[key];mapping={row['program']:i for i,row in enumerate(pool)}
            base_to_wide=[mapping[row['program']] for row in old]
            assert base_to_wide==record['base_to_wide']
            matrix_base=[predicted[key][i] for i in base_to_wide]
            base_scores,base_order=rank(task,old,replay)
            wide_scores,wide_order=rank(task,pool,replay)
            assert base_order==record['base_order'] and wide_order==record['wide_order']
            assert np.allclose(base_scores,record['base_scores'],atol=1e-6)
            assert np.allclose(wide_scores,record['wide_scores'],atol=1e-6)
            base_first=choose_probe(key,matrix_base,base_order,base_scores,
                                    set(range(len(old))),[],'top20_entropy')
            wide_first=choose_probe(key,predicted[key],wide_order,wide_scores,
                                    set(range(len(pool))),[],'top20_entropy')
            assert base_first==record['base_first'] and wide_first==record['wide_first']
            x=features(task,{'scores':base_scores,'order':base_order,
                             'first_probe':{'top20_entropy':base_first}},matrix_base)
            assert np.allclose(x,record['base_features'],atol=1e-6)
            assert record['extra_candidates']==len(pool)-len(old)
        else:
            scores,order=rank(task,old,evaluators[FIXED[block]])
            assert order==record['fixed_order'] and np.allclose(scores,record['fixed_scores'],atol=1e-6)
            assert record['extra_candidates']==0
    states=json.loads((DEST/('parent_models.json' if stage=='admission' else 'child_models.json')).read_text())
    gate=json.loads((DEST/'admission_gate.json').read_text()) if stage!='admission' else None
    lookup={r['id']:r for r in records};rebuilt={}
    for seed in STAGES[stage]:
        group=[lookup[t['id']] for t in tasks if t['seed']==seed
               and lookup[t['id']]['public_block']==BLOCK_AST]
        assert len(group)==8
        bank={name:sorted(width_choose(group,name)) for name in WIDTH_CONTROLS}
        for name,state in states.items():
            bank[name]=sorted(width_choose(group,'ridge_10',state['model']))
        if gate is not None:
            bank['protected_later']=(bank['later'] if gate['admit'] else bank['low_gap'])
        rebuilt[str(seed)]=bank
    assert rebuilt==choices
    result={'passed':True,'stage':stage,'tasks':len(tasks),
            'base_candidates_rechecked':sum(map(len,base.values())),
            'ast_wide_candidates_rechecked':sum(map(len,wide.values())),
            'predicted_output_cells_rechecked':sum(len(v)*8 for v in wide.values()),
            'allocations_rechecked':len(STAGES[stage])*len(next(iter(choices.values())))}
    write_json(DEST/f'audit_prepare_{stage}.json',result)
    print(json.dumps(result,indent=2))


def score(stage):
    manifest,tasks,base,wide,predicted,records,choices=read(stage)
    check_manifest(stage,manifest)
    saved=json.loads((DEST/stage/'results.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];block=record['public_block'];pool=wide.get(key,base[key])
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:]))) for row in pool]
        checked+=len(labels)
        if block==BLOCK_AST:
            base_labels=[labels[i] for i in record['base_to_wide']]
            matrix_base=[predicted[key][i] for i in record['base_to_wide']]
            def pick(values,matrix,order,probe):
                matching={i for i in range(len(values)) if matrix[i][probe]==task['hidden'][probe][1]}
                remaining=matching if matching else set(range(len(values)))
                index=next(i for i in order if i in remaining)
                return values[index],index
            base_one,base_selected=pick(base_labels,matrix_base,record['base_order'],record['base_first'])
            wide_one,wide_selected=pick(labels,predicted[key],record['wide_order'],record['wide_first'])
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
    assert outcomes==saved['tasks']
    summary=saved['summary'];by_id={r['id']:r for r in outcomes};by_record={r['id']:r for r in records}
    assert summary['candidate_labels_checked']==checked
    for bank in summary['by_bank']:
        seed=bank['seed'];group=[t for t in tasks if t['seed']==seed]
        ast=[t for t in group if by_id[t['id']]['public_block']==BLOCK_AST]
        nonast=sum(by_id[t['id']]['fixed_zero'] for t in group if t not in ast)
        assert len(ast)==8
        fixed={'no_query_base':nonast+sum(by_id[t['id']]['base_zero'] for t in ast),
               'no_query_fullwide':nonast+sum(by_id[t['id']]['wide_zero'] for t in ast),
               'base_all':nonast+sum(by_id[t['id']]['base_one'] for t in ast),
               'fullwide':nonast+sum(by_id[t['id']]['wide_one'] for t in ast)}
        for name,value in fixed.items():assert bank['correct'][name]==value
        for name,ids in choices[str(seed)].items():
            selected=set(ids);assert len(selected)==4
            actual=nonast+sum(by_id[t['id']]['wide_one'] if t['id'] in selected
                              else by_id[t['id']]['base_one'] for t in ast)
            assert bank['correct'][name]==actual
            assert bank['effective_extra_candidates'][name]==sum(
                by_record[t['id']]['extra_candidates'] for t in ast if t['id'] in selected)
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
    assert all(v['passed'] for v in parts.values())
    reported=json.loads((DEST/'summary.json').read_text())
    assert reported==summarize()
    banks=[b for stage in ('a','b') for b in
           json.loads((DEST/stage/'results.json').read_text())['summary']['by_bank']]
    assert reported['transfer']['correct']=={name:sum(b['correct'][name] for b in banks)
                                             for name in banks[0]['correct']}
    result={'passed':True,'parts':parts,
            'candidate_labels_rechecked':sum(parts[f'score_{s}']['candidate_labels_rechecked']
                                              for s in STAGES),
            'predicted_output_cells_rechecked':sum(parts[f'prepare_{s}']['predicted_output_cells_rechecked']
                                                   for s in STAGES)}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    actions={'source':source,'children':children,'final':final}
    for stage in STAGES:
        actions[f'prepare_{stage}']=lambda stage=stage:prepare(stage)
        actions[f'score_{stage}']=lambda stage=stage:score(stage)
    actions[sys.argv[1]]()
