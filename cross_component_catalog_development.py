"""Inspected full-mixed development matrix for ranker, AST and sensor edits."""
from __future__ import annotations

import json

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_replay_integration import models,select
from full_mixed_ast_sensor import DEST as SOURCE
from seed_casebanks import FAMILIES


OUT=ROOT/'analysis/cross-component-catalog-development.json'
NAMES=('fixed_map','sharp_global','ast_ranker','sharp_ast_ranker',
       'top20_one','sharp_top20_one','minimax_one','sharp_minimax_one',
       'learned_eight','sharp_learned_eight')


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    tasks=json.loads((SOURCE/'sealed_bank.json').read_text())
    base=json.loads((SOURCE/'base_pools.json').read_text())
    decisions=json.loads((SOURCE/'frozen_decisions.json').read_text())
    old=json.loads((SOURCE/'results.json').read_text())['tasks']
    assert all(t['id']==d['id']==r['id'] for t,d,r in zip(tasks,decisions,old))
    data=models(); outcomes=[];checked=0
    for task,decision,prior in zip(tasks,decisions,old):
        key=task['id']; block=decision['public_block']
        if task['family']=='ast_transition':
            c=prior['correct']
            results={'fixed_map':c['fixed_map'],'sharp_global':c['fixed_map'],
                     'ast_ranker':c['ast_ranker'],'sharp_ast_ranker':c['ast_ranker'],
                     'top20_one':c['top20_one'],'sharp_top20_one':c['top20_one'],
                     'minimax_one':c['minimax_one'],'sharp_minimax_one':c['minimax_one'],
                     'learned_eight':c['learned_eight'],
                     'sharp_learned_eight':c['learned_eight']}
        else:
            rows=base[key]
            choice=select(task,rows,data)
            labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
            checked+=len(labels)
            sharp=bool(labels[choice['temp_0.25']])
            fixed=prior['correct']['fixed_map']
            assert bool(labels[decision['fixed_choice']])==fixed
            results={name:(sharp if name.startswith('sharp') else fixed)
                     for name in NAMES}
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'correct':results})
    by_bank=[{'seed':seed,'correct':{name:sum(r['correct'][name] for r in outcomes
                                               if r['seed']==seed) for name in NAMES}}
             for seed in sorted({t['seed'] for t in tasks})]
    summary={'scope':'inspected full-mixed bank development only',
             'tasks':len(tasks),'candidate_labels_rechecked':checked,
             'correct':{name:sum(r['correct'][name] for r in outcomes) for name in NAMES},
             'by_family':{family:{name:sum(r['correct'][name] for r in outcomes
                                             if r['family']==family) for name in NAMES}
                          for family in FAMILIES},
             'by_bank':by_bank}
    write_json(OUT,{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
