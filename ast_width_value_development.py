"""Development-only public-feature selection of four AST width slots per bank."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from ast_query_allocation_development import fit as ridge_fit,predict as ridge_predict
from gated_ast_feedback import BLOCK_AST
from cross_family_meta_improver_transfer import interval

OUT=ROOT/'analysis/ast-width-value-development-20260918.json'
METHODS=('random','low_gap','high_entropy','ridge_1','ridge_10','ridge_100')


def load(name,stages):
    rows=[]
    for stage in stages:
        path=ROOT/f'analysis/ast-width-query-counterfactuals-{name}-{stage}-20260918.json'
        rows+=json.loads(path.read_text())['rows']
    return [r for r in rows if r['public_block']==BLOCK_AST]


def fit(rows,method):
    if not method.startswith('ridge_'):return None
    x=np.asarray([r['base_features'] for r in rows],float)
    y=np.asarray([r['width_one_effect'] for r in rows],float)
    params=ridge_fit(x,y,np.zeros(len(y)),float(method.split('_')[1]))
    return [v.tolist() for v in params]


def choose(group,method,model=None):
    assert len(group)==8
    if method=='random':
        scores=[hashlib.sha256((r['id']+':width4').encode()).digest() for r in group]
    elif method=='low_gap':scores=[-r['base_features'][2] for r in group]
    elif method=='high_entropy':scores=[r['base_features'][4] for r in group]
    else:
        x=np.asarray([r['base_features'] for r in group],float)
        scores=ridge_predict(tuple(np.asarray(v) for v in model),x)[0].tolist()
    order=sorted(zip(group,scores),key=lambda pair:(pair[1],pair[0]['id']),reverse=True)
    return {r['id'] for r,_ in order[:4]}


def score(group,selected):
    assert len(selected)==4
    return sum(r['wide_one'] if r['id'] in selected else r['base_one'] for r in group)


def cv(rows):
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        held=[r for r in rows if r['seed']==seed]
        train=[r for r in rows if r['seed']!=seed]
        assert len(held)==8
        results={method:score(held,choose(held,method,fit(train,method))) for method in METHODS}
        banks.append({'seed':seed,'base_one':sum(r['base_one'] for r in held),
                      'full_wide_one':sum(r['wide_one'] for r in held),
                      'correct':results})
    return banks


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    source=load('meta',('admission','a','b'))
    target=load('stable',('a','b'))
    assert len(source)==144 and len(target)==96
    source_banks=cv(source)
    source_scores={name:sum(b['correct'][name] for b in source_banks) for name in METHODS}
    selected=max(METHODS,key=lambda name:(source_scores[name],-METHODS.index(name)))
    models={name:fit(source,name) for name in METHODS}
    target_banks=[]
    for seed in sorted({r['seed'] for r in target}):
        group=[r for r in target if r['seed']==seed]
        outcomes={name:score(group,choose(group,name,models[name])) for name in METHODS}
        target_banks.append({'seed':seed,'base_one':sum(r['base_one'] for r in group),
                             'full_wide_one':sum(r['wide_one'] for r in group),
                             'correct':outcomes})
    target_scores={name:sum(b['correct'][name] for b in target_banks) for name in METHODS}
    diffs=[b['correct'][selected]-b['correct']['random'] for b in target_banks]
    result={'scope':'development only; opened source and target labels',
            'source_ast_tasks':len(source),'source_banks':len(source_banks),
            'target_ast_tasks':len(target),'target_banks':len(target_banks),
            'width_slots_per_bank':4,'query_calls_per_bank_in_this_diagnostic':8,
            'methods':METHODS,'source_cv_correct':source_scores,
            'selected_from_source':selected,'target_correct':target_scores,
            'target_base_one':sum(b['base_one'] for b in target_banks),
            'target_full_wide_one':sum(b['full_wide_one'] for b in target_banks),
            'target_selected_minus_random':{'by_bank':diffs,'sum':sum(diffs),
                                             'bank_bootstrap_95_sum':interval(diffs)},
            'source_by_bank':source_banks,'target_by_bank':target_banks,
            'models':models,
            'limits':['One query on each AST task consumes all eight bank calls.',
                      'This isolates search-width selection; it does not jointly optimize cross-family query calls.',
                      'Target labels are opened development evidence.']}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ('source_by_bank','target_by_bank','models')},indent=2))


if __name__=='__main__':main()
