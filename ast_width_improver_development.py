"""Opened-source ridge-10 parent states for four-slot AST width allocation."""
from __future__ import annotations

import json

from rsi.common import ROOT,write_json
from gated_ast_feedback import BLOCK_AST
from ast_width_value_development import load,fit,choose,score

OUT=ROOT/'analysis/ast-width-improver-development-20260918.json'
PARENTS=ROOT/'analysis/ast-width-improver-parent-models-20260918.json'
NAMES=('initial','later','scrambled','duplicate')
METHOD='ridge_10'


def tables():
    initial=load('meta',('admission','a','b'))
    added=load('stable',('a','b'))
    assert len(initial)==144 and len(added)==96
    assert all(r['public_block']==BLOCK_AST for r in initial+added)
    scrambled=[dict(r) for r in added]
    for target,donor in enumerate([len(added)-1]+list(range(len(added)-1))):
        scrambled[target]={**scrambled[target],
                           'width_one_effect':added[donor]['width_one_effect']}
    return {'initial':initial,'later':initial+added,
            'scrambled':initial+scrambled,'duplicate':initial+initial[:96]}


def train_state(rows):
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        held=list({r['id']:r for r in rows if r['seed']==seed}.values())
        other=[r for r in rows if r['seed']!=seed]
        assert len(held)==8
        scores={name:score(held,choose(held,name,fit(other,name)))
                for name in ('random','low_gap',METHOD)}
        banks.append({'seed':seed,'correct':scores})
    model=fit(rows,METHOD)
    return {'source_rows':len(rows),'unique_source_tasks':len({r['id'] for r in rows}),
            'method':METHOD,'source_cv_correct':{name:sum(b['correct'][name] for b in banks)
                                                 for name in ('random','low_gap',METHOD)},
            'model':model,'source_task_ids':[r['id'] for r in rows]},banks


def main():
    if OUT.exists() or PARENTS.exists():raise RuntimeError('development output exists')
    sources=tables();states={};validation={}
    for name,rows in sources.items():
        state,banks=train_state(rows)
        states[name]=state
        validation[name]={'source_rows':state['source_rows'],
                          'unique_source_tasks':state['unique_source_tasks'],
                          'source_cv_correct':state['source_cv_correct'],
                          'by_bank':banks}
    write_json(PARENTS,states)
    write_json(OUT,{'scope':'opened AST width-source development only',
                    'method':METHOD,'parents':validation})
    print(json.dumps({name:{k:validation[name][k] for k in
                             ('source_rows','unique_source_tasks','source_cv_correct')}
                      for name in states},indent=2))


if __name__=='__main__':main()
