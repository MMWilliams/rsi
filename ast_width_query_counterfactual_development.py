"""Opened-bank base/wide AST and first-query counterfactuals on identical tasks."""
from __future__ import annotations

import json
import sys

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import public_block,BLOCK_AST
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_family_meta_improver_transfer import sha

RUNS={'meta':ROOT/'runs/cross-family-meta-improver-transfer-20260918',
      'stable':ROOT/'runs/stable-cross-family-improver-transfer-20260918'}


def select_after_one(task,pool,matrix,scores,order):
    key=task['id']
    first=choose_probe(key,matrix,order,scores,set(range(len(pool))),[],'top20_entropy')
    matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
    remaining=matching if matching else set(range(len(pool)))
    selected=next(i for i in order if i in remaining)
    return first,selected


def run(name,stage):
    directory=RUNS[name]/stage
    out=ROOT/f'analysis/ast-width-query-counterfactuals-{name}-{stage}-20260918.json'
    if out.exists():raise RuntimeError(f'{out} exists')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    results=json.loads((directory/'results.json').read_text())['tasks']
    assert len(tasks)==len(records)==len(results)==288
    replay=updated_model();rows=[]
    for task,record,result in zip(tasks,records,results):
        key=task['id'];old=base[key];pool=wide.get(key,old)
        assert key==record['id']==result['id']
        if public_block(task)==BLOCK_AST:
            wide_lookup={row['program']:i for i,row in enumerate(pool)}
            assert all(row['program'] in wide_lookup for row in old)
            matrix=[predicted[key][wide_lookup[row['program']]] for row in old]
            scores,order=rank(task,old,replay)
            first,selected=select_after_one(task,old,matrix,scores,order)
            base_zero=int(bool(evaluate_program(old[order[0]]['program'],task['hidden'][8:])))
            base_one=int(bool(evaluate_program(old[selected]['program'],task['hidden'][8:])))
            base_features=features(task,{'scores':scores,'order':order,
                                         'first_probe':{'top20_entropy':first}},matrix).tolist()
            assert len(pool)>=len(old)
        else:
            first=record['first_probe'];selected=result['selected_after_query']
            base_zero=int(result['zero']);base_one=int(result['one'])
            base_features=record['features']
        wide_zero=int(result['zero']);wide_one=int(result['one'])
        rows.append({'id':key,'seed':task['seed'],'family':task['family'],
                     'public_block':record['public_block'],
                     'base_features':base_features,'wide_features':record['features'],
                     'base_zero':base_zero,'base_one':base_one,
                     'wide_zero':wide_zero,'wide_one':wide_one,
                     'width_zero_effect':wide_zero-base_zero,
                     'width_one_effect':wide_one-base_one,
                     'base_query_gain':base_one-base_zero,
                     'wide_query_gain':wide_one-wide_zero,
                     'base_first_probe':first,
                     'base_selected_after_query':selected,
                     'extra_candidates':len(pool)-len(old)})
    def totals(group):
        return {'tasks':len(group),
                'base_zero':sum(r['base_zero'] for r in group),
                'base_one':sum(r['base_one'] for r in group),
                'wide_zero':sum(r['wide_zero'] for r in group),
                'wide_one':sum(r['wide_one'] for r in group),
                'width_one_gains':sum(r['width_one_effect']>0 for r in group),
                'width_one_harms':sum(r['width_one_effect']<0 for r in group),
                'extra_candidates':sum(r['extra_candidates'] for r in group)}
    result={'scope':'opened-bank counterfactuals; four AST width slots and eight query calls are future budgets',
            'run':name,'stage':stage,
            'source_sha256':{n:sha(directory/n) for n in
                             ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
                              'predicted_probe_outputs.json','frozen_records.json','results.json')},
            'overall':totals(rows),
            'ast':totals([r for r in rows if r['public_block']==BLOCK_AST]),
            'rows':rows}
    write_json(out,result)
    print(json.dumps({'run':name,'stage':stage,'ast':result['ast']},indent=2))


if __name__=='__main__':run(sys.argv[1],sys.argv[2])
