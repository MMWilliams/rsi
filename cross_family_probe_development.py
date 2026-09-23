"""Inspected development: one exact output query across all six mechanisms."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES
from gated_ast_feedback import public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_component_mixed_transfer import DEST as SOURCE


OUT=ROOT/'analysis/cross-family-probe-development.json'


def ranked(task,rows,models,replay):
    data=replay if public_block(task)==BLOCK_AST else models[FIXED[public_block(task)]]
    return rank(task,rows,data)


def select_budget(group,mode):
    assert len(group)==48
    if mode=='ast_only':return {r['id'] for r in group if r['family']=='ast_transition'}
    if mode=='transform_mutation':
        result=set()
        for family in ('transform_transition','mutation_transition'):
            items=sorted((r for r in group if r['family']==family),
                         key=lambda r:hashlib.sha256((r['id']+':family').encode()).digest())
            result.update(r['id'] for r in items[:4])
        return result
    if mode=='balanced':
        counts={'transform_transition':2,'mutation_transition':2,
                'ast_transition':1,'novel_operator_transition':1,
                'stack_transition':1,'self_edit_transition':1}
        result=set()
        for family,count in counts.items():
            items=sorted((r for r in group if r['family']==family),
                         key=lambda r:hashlib.sha256((r['id']+':balanced').encode()).digest())
            result.update(r['id'] for r in items[:count])
        return result
    if mode=='random':
        ranked_rows=sorted(group,key=lambda r:hashlib.sha256(
            (r['id']+':random').encode()).digest(),reverse=True)
    elif mode=='entropy':ranked_rows=sorted(group,key=lambda r:(r['features'][4],r['id']),reverse=True)
    elif mode=='disagreement':ranked_rows=sorted(group,key=lambda r:(r['features'][9],r['id']),reverse=True)
    elif mode=='uncertainty':ranked_rows=sorted(group,key=lambda r:(-r['features'][2],r['id']),reverse=True)
    elif mode=='hindsight':ranked_rows=sorted(group,key=lambda r:(r['gain'],r['id']),reverse=True)
    else:raise ValueError(mode)
    return {r['id'] for r in ranked_rows[:8]}


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    tasks=json.loads((SOURCE/'sealed_bank.json').read_text())
    base=json.loads((SOURCE/'base_pools.json').read_text())
    wide=json.loads((SOURCE/'ast_wide_pools.json').read_text())
    decisions=json.loads((SOURCE/'frozen_decisions.json').read_text())
    previous=json.loads((SOURCE/'results.json').read_text())['tasks']
    frozen_ast=json.loads((SOURCE/'predicted_probe_outputs.json').read_text())
    public=[({'id':task['id'],'probe_inputs':[v for v,_ in task['hidden'][:8]]},
             base[task['id']]) for task in tasks if public_block(task)!=BLOCK_AST]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    predicted.update(frozen_ast)
    models=evaluator_models();replay=updated_model()
    rows=[]
    for task,old,prior in zip(tasks,decisions,previous):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        scores,order=ranked(task,pool,models,replay)
        expected=(old['order'][0] if public_block(task)==BLOCK_AST
                  else old['fixed_choice'])
        assert order[0]==expected and key==old['id']==prior['id']
        first=choose_probe(key,matrix,order,scores,set(range(len(pool))),[],
                           'top20_entropy')
        matched={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matched if matched else set(range(len(pool)))
        chosen=next(i for i in order if i in remaining)
        zero=bool(prior['correct']['ast_ranker'] if public_block(task)==BLOCK_AST
                  else prior['correct']['fixed_map'])
        one=bool(evaluate_program(pool[chosen]['program'],task['hidden'][8:]))
        if public_block(task)==BLOCK_AST:
            assert one==prior['correct']['top20_one']
        feature=features(task,{'scores':scores,'order':order,
                               'first_probe':{'top20_entropy':first}},matrix)
        rows.append({'id':key,'seed':task['seed'],'family':task['family'],
                     'probe_index':first,'selected_index':chosen,
                     'candidates':len(pool),'zero':zero,'one':one,
                     'gain':int(one)-int(zero),'features':feature.tolist()})
    modes=('ast_only','transform_mutation','balanced','random','entropy',
           'disagreement','uncertainty','hindsight')
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        scores={}
        for mode in modes:
            selected=select_budget(group,mode)
            assert len(selected)==8
            scores[mode]=sum(r['one'] if r['id'] in selected else r['zero'] for r in group)
        banks.append({'seed':seed,'no_query':sum(r['zero'] for r in group),
                      'correct':scores})
    result={'scope':'inspected cross-family output-sensor development',
            'tasks':len(rows),'candidate_output_predictions':sum(r['candidates']*8 for r in rows),
            'no_query':sum(r['zero'] for r in rows),
            'one_each_all_tasks':sum(r['one'] for r in rows),
            'by_family':{f:{'tasks':sum(r['family']==f for r in rows),
                            'zero':sum(r['zero'] for r in rows if r['family']==f),
                            'one':sum(r['one'] for r in rows if r['family']==f),
                            'gains':sum(r['gain']>0 for r in rows if r['family']==f),
                            'harms':sum(r['gain']<0 for r in rows if r['family']==f)}
                         for f in FAMILIES},
            'fixed_8_call_correct':{m:sum(b['correct'][m] for b in banks) for m in modes},
            'by_bank':banks,'tasks_detail':rows}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='tasks_detail'},indent=2))


if __name__=='__main__':main()
