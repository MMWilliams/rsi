"""Opened-bank simulation of AST width plus frozen cross-family query allocation."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import BLOCK_AST
from ast_probe_sensor_transfer import predicted_outputs
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_family_meta_improver_development import select as model_select
from cross_family_query_value_development import choose as fixed_choose
from cross_family_meta_improver_transfer import sha

RUN=ROOT/'runs/ast-width-improver-transfer-20260918-v2'
SOURCE=ROOT/'runs/cross-family-meta-improver-transfer-20260918/child_models.json'
POLICIES=('base_all','random','low_gap','initial','later','fullwide')
MODELS=('fixed_10','fixed_100')


def outcome(task,pool,matrix,order,first):
    matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
    remaining=matching if matching else set(range(len(pool)))
    selected=next(i for i in order if i in remaining)
    return int(bool(evaluate_program(pool[selected]['program'],task['hidden'][8:])))


def stage(name):
    directory=RUN/name
    out=ROOT/f'analysis/joint-width-query-{name}-20260918.json'
    if out.exists():raise RuntimeError(f'{out} exists')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    width=json.loads((directory/'frozen_allocations.json').read_text())
    scored=json.loads((directory/'results.json').read_text())['tasks']
    assert len(tasks)==len(records)==len(scored)==288
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},base[t['id']])
            for t,r in zip(tasks,records) if r['public_block']!=BLOCK_AST]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted.update(dict(executor.map(predicted_outputs,public)))
    data={};by_record={r['id']:r for r in records}
    for task,record,result in zip(tasks,records,scored):
        key=task['id'];assert key==record['id']==result['id']
        if record['public_block']==BLOCK_AST:
            wide_features=features(task,{'scores':record['wide_scores'],
                                         'order':record['wide_order'],
                                         'first_probe':{'top20_entropy':record['wide_first']}},
                                    predicted[key]).tolist()
            data[key]={'base':{'features':record['base_features'],
                               'zero':result['base_zero'],'one':result['base_one']},
                       'wide':{'features':wide_features,
                               'zero':result['wide_zero'],'one':result['wide_one']}}
        else:
            pool=base[key];matrix=predicted[key]
            first=choose_probe(key,matrix,record['fixed_order'],record['fixed_scores'],
                               set(range(len(pool))),[],'top20_entropy')
            f=features(task,{'scores':record['fixed_scores'],'order':record['fixed_order'],
                             'first_probe':{'top20_entropy':first}},matrix).tolist()
            one=outcome(task,pool,matrix,record['fixed_order'],first)
            data[key]={'base':{'features':f,'zero':result['fixed_zero'],'one':one},
                       'wide':{'features':f,'zero':result['fixed_zero'],'one':one}}
    models=json.loads(SOURCE.read_text())
    banks=[]
    for seed in sorted({t['seed'] for t in tasks}):
        group=[t for t in tasks if t['seed']==seed]
        assert len(group)==48
        bank={'seed':seed,'policies':{}}
        ast_ids={t['id'] for t in group if t['id'] in wide}
        assert len(ast_ids)==8
        for policy in POLICIES:
            if policy=='base_all':selected=set()
            elif policy=='fullwide':selected=ast_ids
            else:selected=set(width[str(seed)][policy])
            rows=[]
            for task in group:
                key=task['id'];variant=data[key]['wide' if key in selected else 'base']
                rows.append({'id':key,'seed':seed,'family':task['family'],
                             'public_block':by_record[key]['public_block'],
                             'features':variant['features'],
                             'zero':variant['zero'],'one':variant['one'],
                             'gain':variant['one']-variant['zero']})
            # The score model is frozen from earlier source; target labels only score choices.
            scores={'no_query':sum(r['zero'] for r in rows)}
            choices={}
            for model_name in MODELS:
                ids=model_select(rows,models[model_name]['model'])
                choices[model_name]=sorted(ids)
                scores[model_name]=sum(r['one'] if r['id'] in ids else r['zero'] for r in rows)
            ids=fixed_choose(rows,'transform_only')
            scores['transform_only']=sum(r['one'] if r['id'] in ids else r['zero'] for r in rows)
            scores['one_each']=sum(r['one'] for r in rows)
            scores['hindsight_eight']=scores['no_query']+sum(sorted(
                (r['gain'] for r in rows),reverse=True)[:8])
            bank['policies'][policy]={'correct':scores,'selected_ids':choices,
                                      'effective_extra_candidates':sum(
                                          by_record[key]['extra_candidates']
                                          for key in selected),
                                      'selected_width_ids':sorted(selected)}
        banks.append(bank)
    result={'scope':'opened-bank joint width/query simulation; not prospective promotion evidence',
            'stage':name,'tasks':len(tasks),'banks':banks,
            'model_source_sha256':sha(SOURCE),
            'source_sha256':{n:sha(directory/n) for n in
                             ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
                              'predicted_probe_outputs.json','frozen_records.json',
                              'frozen_allocations.json','results.json')},
            'new_nonast_predicted_output_cells':sum(len(base[t['id']])*8 for t,r in zip(tasks,records)
                                                     if r['public_block']!=BLOCK_AST),
            'limits':['All non-AST predicted outputs and their cost are newly computed for this development simulation.',
                      'Both query models were frozen before these width-run tasks, but this comparison was designed after opening their labels.',
                      'Hindsight uses unavailable final labels.']}
    write_json(out,result)
    totals={p:{name:sum(b['policies'][p]['correct'][name] for b in banks)
               for name in banks[0]['policies'][p]['correct']} for p in POLICIES}
    print(json.dumps({'stage':name,'totals':totals,
                      'new_nonast_predicted_output_cells':result['new_nonast_predicted_output_cells']},indent=2))


if __name__=='__main__':stage(sys.argv[1])
