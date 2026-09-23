"""Development-only per-task component effects from opened cross-family banks."""
from __future__ import annotations

import json
import sys

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models,select as evaluator_select
from ast_probe_sensor_development import choose_probe
from cross_family_meta_improver_transfer import sha

RUNS={'meta':ROOT/'runs/cross-family-meta-improver-transfer-20260918',
      'stable':ROOT/'runs/stable-cross-family-improver-transfer-20260918'}


def reconstruct(run,stage):
    directory=RUNS[run]/stage
    out=ROOT/f'analysis/typed-edit-effects-{run}-{stage}-20260918.json'
    if out.exists():raise RuntimeError(f'{out} already exists')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    predictions=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert len(tasks)==len(records)==len(outcomes)==288
    models=evaluator_models();rows=[]
    for task,record,outcome in zip(tasks,records,outcomes):
        key=task['id'];ast=public_block(task)==BLOCK_AST
        assert key==record['id']==outcome['id']
        old=base[key];pool=wide.get(key,old);matrix=predictions[key]
        assert len(matrix)==len(pool)
        selected=evaluator_select(task,pool,models)
        fixed=selected[FIXED[public_block(task)]]
        sharp=selected['temp_0.25']
        score=lambda index,rows:bool(evaluate_program(rows[index]['program'],task['hidden'][8:]))
        fixed_wide=score(fixed,pool);sharp_wide=score(sharp,pool)
        if ast:
            selected_base=evaluator_select(task,old,models)[FIXED[public_block(task)]]
            fixed_base=score(selected_base,old)
            base_reachable=any(bool(evaluate_program(row['program'],task['hidden'][8:]))
                               for row in old)
        else:
            fixed_base=fixed_wide;base_reachable=bool(outcome['reachable'])
        first_minimax=choose_probe(key,matrix,record['order'],record['scores'],
                                   set(range(len(pool))),[],'minimax')
        matching={i for i in range(len(pool))
                  if matrix[i][first_minimax]==task['hidden'][first_minimax][1]}
        remaining=matching if matching else set(range(len(pool)))
        minimax=next(i for i in record['order'] if i in remaining)
        minimax_one=score(minimax,pool)
        assert bool(outcome['zero'])==score(record['order'][0],pool)
        assert bool(outcome['one'])==score(outcome['selected_after_query'],pool)
        assert bool(outcome['reachable']) or not outcome['one']
        assert not ast or len(pool)>=len(old)
        values={'fixed_base':int(fixed_base),'fixed_wide':int(fixed_wide),
                'sharp_wide':int(sharp_wide),'replay_wide':int(outcome['zero']),
                'top20_one':int(outcome['one']),'minimax_one':int(minimax_one)}
        effects={'search_plus_fixed':values['fixed_wide']-values['fixed_base'],
                 'sharp_vs_fixed':values['sharp_wide']-values['fixed_wide'],
                 'replay_vs_fixed':values['replay_wide']-values['fixed_wide'],
                 'top20_vs_replay':values['top20_one']-values['replay_wide'],
                 'minimax_vs_replay':values['minimax_one']-values['replay_wide']}
        rows.append({'id':key,'seed':task['seed'],'family':task['family'],
                     'public_block':public_block(task),'features':record['features'],
                     'base_reachable':int(base_reachable),
                     'wide_reachable':int(outcome['reachable']),
                     'outcomes':values,'effects':effects,
                     'costs':{'base_candidates':len(old),
                              'extra_wide_candidates':len(pool)-len(old) if ast else 0,
                              'predicted_output_cells':len(pool)*8,
                              'top20_or_minimax_true_output_calls':1}})
    names=tuple(rows[0]['outcomes']);types=tuple(rows[0]['effects'])
    def aggregate(group):
        return {'tasks':len(group),'base_reachable':sum(r['base_reachable'] for r in group),
                'wide_reachable':sum(r['wide_reachable'] for r in group),
                'correct':{name:sum(r['outcomes'][name] for r in group) for name in names},
                'edit_effects':{name:{'gain':sum(r['effects'][name]>0 for r in group),
                                      'harm':sum(r['effects'][name]<0 for r in group),
                                      'net':sum(r['effects'][name] for r in group)}
                                for name in types}}
    result={'scope':'opened development bank; reconstructed typed edit effects',
            'run':run,'stage':stage,
            'source_sha256':{name:sha(directory/name) for name in
                             ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
                              'predicted_probe_outputs.json','frozen_records.json','results.json')},
            'overall':aggregate(rows),
            'by_family':{f:aggregate([r for r in rows if r['family']==f])
                         for f in sorted({r['family'] for r in rows})},
            'rows':rows}
    write_json(out,result)
    print(json.dumps({'run':run,'stage':stage,'overall':result['overall']},indent=2))


if __name__=='__main__':reconstruct(sys.argv[1],sys.argv[2])
