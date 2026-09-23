"""Opened-source parent states for a bounded rich-feature evaluator improver."""
from __future__ import annotations

import json

from rsi.common import ROOT,write_json
from rich_query_value_development import METHODS,load,fit,select,utility

OUT=ROOT/'analysis/rich-query-improver-development-20260918.json'
PARENTS=ROOT/'analysis/rich-query-improver-parent-models-20260918.json'


def tables():
    initial=load('meta',('admission','a','b'))
    added=load('stable',('a','b'))
    assert len(initial)==864 and len(added)==576
    assert set(r['id'] for r in initial).isdisjoint(r['id'] for r in added)
    scrambled=[dict(r) for r in added]
    for block in sorted({r['public_block'] for r in added}):
        indices=[i for i,r in enumerate(added) if r['public_block']==block]
        for target,donor in zip(indices,indices[-1:]+indices[:-1]):
            scrambled[target]={**scrambled[target],'gain':added[donor]['gain']}
    return {'initial':initial,'later':initial+added,
            'scrambled':initial+scrambled,'duplicate':initial+initial[:576]}


def cross_validation(rows):
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        held=list({r['id']:r for r in rows if r['seed']==seed}.values())
        source=[r for r in rows if r['seed']!=seed]
        assert len(held)==48
        scores={name:utility(held,select(held,fit(source,name))) for name in METHODS}
        banks.append({'seed':seed,'correct':scores})
    return banks


def train_state(rows):
    banks=cross_validation(rows)
    scores={name:sum(b['correct'][name] for b in banks) for name in METHODS}
    selected=max(METHODS,key=lambda name:(scores[name],-METHODS.index(name)))
    state={'source_rows':len(rows),'unique_source_tasks':len({r['id'] for r in rows}),
           'selected_method':selected,'source_cv_correct':scores,
           'model':fit(rows,selected),'source_task_ids':[r['id'] for r in rows]}
    return state,banks


def main():
    if OUT.exists() or PARENTS.exists():raise RuntimeError('development output exists')
    source=tables();states={};validation={}
    for name,rows in source.items():
        state,banks=train_state(rows)
        states[name]=state
        validation[name]={'source_rows':state['source_rows'],
                          'unique_source_tasks':state['unique_source_tasks'],
                          'selected_method':state['selected_method'],
                          'source_cv_correct':state['source_cv_correct'],
                          'by_bank':banks}
    write_json(PARENTS,states)
    write_json(OUT,{'scope':'opened parent development only',
                    'methods':METHODS,'parents':validation})
    print(json.dumps({name:{k:validation[name][k] for k in
                             ('source_rows','unique_source_tasks','selected_method','source_cv_correct')}
                      for name in states},indent=2))


if __name__=='__main__':main()
