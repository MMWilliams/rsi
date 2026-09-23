"""Inspected-bank training-rule screen for a fixed eight-query mixed budget."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from seed_casebanks import FAMILIES
from ast_query_allocation_development import fit,predict


OUT=ROOT/'analysis/cross-family-query-value-development.json'
SOURCES=(ROOT/'analysis/cross-family-probe-prior-development.json',
         ROOT/'analysis/cross-family-probe-development.json')
METHODS=('family_mean','basic_10','family_10','family_100',
         'interaction_10','interaction_100')
CONTROLS=('ast_only','transform_only','mutation_only','transform_mutation',
          'balanced','random')


def rows_for():
    result=[]
    for path in SOURCES:
        raw=json.loads(path.read_text())
        assert raw['tasks']==288
        result.extend(raw['tasks_detail'])
    assert len(result)==576 and len({r['id'] for r in result})==576
    return result


def matrix(rows,kind):
    base=np.asarray([r['features'] for r in rows],float)
    family=np.asarray([[float(r['family']==f) for f in FAMILIES] for r in rows])
    if kind=='basic':return base
    if kind=='family':return np.c_[base,family]
    if kind=='interaction':
        # Family-specific public uncertainty, output diversity and score-gap effects.
        interactions=np.einsum('ni,nj->nij',family,base[:,2:10]).reshape(len(rows),-1)
        return np.c_[base,family,interactions]
    raise ValueError(kind)


def predict_values(source,target,method):
    if method=='family_mean':
        counts={f:(sum(r['gain'] for r in source if r['family']==f),
                   sum(r['family']==f for r in source)) for f in FAMILIES}
        return np.asarray([(counts[r['family']][0]+1)/(counts[r['family']][1]+2)
                           for r in target])
    kind,penalty=method.rsplit('_',1)
    x=matrix(source,kind); y=np.asarray([r['gain'] for r in source],float)
    model=fit(x,y,np.zeros(len(y)),float(penalty))
    return predict(model,matrix(target,kind))[0]


def choose(group,mode,values=None):
    if mode=='ast_only':return {r['id'] for r in group if r['family']=='ast_transition'}
    if mode=='transform_only':return {r['id'] for r in group if r['family']=='transform_transition'}
    if mode=='mutation_only':return {r['id'] for r in group if r['family']=='mutation_transition'}
    if mode=='transform_mutation':
        result=set()
        for family in ('transform_transition','mutation_transition'):
            sub=sorted((r for r in group if r['family']==family),key=lambda r:
                       hashlib.sha256((r['id']+':family').encode()).digest())
            result.update(r['id'] for r in sub[:4])
        return result
    if mode=='balanced':
        counts={'transform_transition':2,'mutation_transition':2,
                'ast_transition':1,'novel_operator_transition':1,
                'stack_transition':1,'self_edit_transition':1}
        result=set()
        for family,count in counts.items():
            sub=sorted((r for r in group if r['family']==family),key=lambda r:
                       hashlib.sha256((r['id']+':balanced').encode()).digest())
            result.update(r['id'] for r in sub[:count])
        return result
    if mode=='random':
        sub=sorted(group,key=lambda r:hashlib.sha256((r['id']+':random').encode()).digest(),
                   reverse=True)
    else:
        assert values is not None
        sub=sorted(zip(group,values),key=lambda pair:(float(pair[1]),pair[0]['id']),
                   reverse=True)
        return {r['id'] for r,_ in sub[:8]}
    return {r['id'] for r in sub[:8]}


def utility(group,selected):
    assert len(selected)==8
    return sum(r['one'] if r['id'] in selected else r['zero'] for r in group)


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows=rows_for();seeds=sorted({r['seed'] for r in rows})
    assert len(seeds)==12
    banks=[]
    for seed in seeds:
        held=[r for r in rows if r['seed']==seed]
        source=[r for r in rows if r['seed']!=seed]
        assert len(held)==48
        scores={name:utility(held,choose(held,name)) for name in CONTROLS}
        for method in METHODS:
            values=predict_values(source,held,method)
            scores[method]=utility(held,choose(held,method,values))
        banks.append({'seed':seed,'no_query':sum(r['zero'] for r in held),
                      'correct':scores})
    summary={'scope':'inspected 12-bank development only','tasks':len(rows),
             'banks':len(seeds),'calls_per_bank':8,
             'correct':{name:sum(b['correct'][name] for b in banks)
                        for name in (*CONTROLS,*METHODS)},
             'by_bank':banks}
    write_json(OUT,summary)
    print(json.dumps({'tasks':summary['tasks'],'banks':summary['banks'],
                      'correct':summary['correct']},indent=2))


if __name__=='__main__':main()
