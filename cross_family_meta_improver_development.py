"""Bounded improver: select a cross-family evaluator training rule from verified effects."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from gated_ast_feedback import public_block
from ast_query_allocation_development import fit,predict
from cross_family_query_value_development import rows_for
from cross_family_query_transfer import DEST as PREVIOUS


OUT=ROOT/'analysis/cross-family-meta-improver-development.json'
PARENTS=ROOT/'analysis/cross-family-meta-improver-parent-models.json'
BLOCKS=(0x700,0x800,0x900,0xA00,0xC00,0xD00)
METHODS=('interaction_100','interaction_10','family_100','family_10',
         'basic_10','family_mean')
SOURCE_TASKS=(ROOT/'runs/full-mixed-ast-sensor-20260918/sealed_bank.json',
              ROOT/'runs/cross-component-mixed-transfer-20260918/sealed_bank.json')


def source_rows():
    rows=rows_for();lookup={}
    for path in SOURCE_TASKS:
        for task in json.loads(path.read_text()):
            assert task['id'] not in lookup
            lookup[task['id']]=public_block(task)
    assert len(lookup)==576
    return [{**r,'public_block':lookup[r['id']]} for r in rows]


def previous_panel(panel):
    directory=PREVIOUS/panel
    records=json.loads((directory/'frozen_records.json').read_text())
    results=json.loads((directory/'results.json').read_text())['tasks']
    assert all(r['id']==o['id'] for r,o in zip(records,results))
    return [{**{k:r[k] for k in ('id','seed','family','features','public_block')},
             'zero':int(o['zero']),'one':int(o['one']),
             'gain':int(o['one'])-int(o['zero'])} for r,o in zip(records,results)]


def matrix(rows,kind):
    base=np.asarray([r['features'] for r in rows],float)
    onehot=np.asarray([[float(r['public_block']==block) for block in BLOCKS]
                       for r in rows])
    if kind=='basic':return base
    if kind=='family':return np.c_[base,onehot]
    if kind=='interaction':
        cross=np.einsum('ni,nj->nij',onehot,base[:,2:10]).reshape(len(rows),-1)
        return np.c_[base,onehot,cross]
    raise ValueError(kind)


def fit_method(rows,name):
    if name=='family_mean':
        rates={str(block):(sum(r['gain'] for r in rows if r['public_block']==block)+1)/
                          (sum(r['public_block']==block for r in rows)+2)
               for block in BLOCKS}
        return {'kind':'family_mean','rates':rates}
    kind,penalty=name.rsplit('_',1)
    y=np.asarray([r['gain'] for r in rows],float)
    params=fit(matrix(rows,kind),y,np.zeros(len(y)),float(penalty))
    return {'kind':kind,'penalty':float(penalty),
            'params':[v.tolist() for v in params]}


def values(model,rows):
    if model['kind']=='family_mean':
        return np.asarray([model['rates'][str(r['public_block'])] for r in rows])
    params=tuple(np.asarray(v,float) for v in model['params'])
    return predict(params,matrix(rows,model['kind']))[0]


def select(group,model):
    scores=values(model,group)
    order=sorted(zip(group,scores),key=lambda pair:(float(pair[1]),pair[0]['id']),
                 reverse=True)
    return {r['id'] for r,_ in order[:8]}


def utility(group,ids):
    assert len(ids)==8
    return sum(r['one'] if r['id'] in ids else r['zero'] for r in group)


def cross_validation(rows):
    seeds=sorted({r['seed'] for r in rows})
    scores={name:0 for name in METHODS};by_bank=[]
    for seed in seeds:
        held=list({r['id']:r for r in rows if r['seed']==seed}.values())
        other=[r for r in rows if r['seed']!=seed]
        assert len(held)==48
        bank={name:utility(held,select(held,fit_method(other,name)))
              for name in METHODS}
        by_bank.append({'seed':seed,'correct':bank})
        for name in METHODS:scores[name]+=bank[name]
    return scores,by_bank


def train_state(rows):
    scores,banks=cross_validation(rows)
    # Catalog order is a frozen tie-break; no target labels are used.
    selected=max(METHODS,key=lambda name:(scores[name],-METHODS.index(name)))
    return {'source_tasks':len(rows),'selected_method':selected,
            'source_cv_correct':scores,
            'model':fit_method(rows,selected),
            'source_task_ids':[r['id'] for r in rows]},banks


def parent_tables():
    source=source_rows();added=previous_panel('a')
    assert len(source)==576 and len(added)==288
    scrambled=[dict(r) for r in added]
    for block in BLOCKS:
        idx=[i for i,r in enumerate(added) if r['public_block']==block]
        for target,donor in zip(idx,idx[-1:]+idx[:-1]):
            scrambled[target]={**scrambled[target],'gain':added[donor]['gain']}
    return {'initial':source,'later':source+added,
            'scrambled':source+scrambled,'duplicate':source+source[:288]}


def main():
    if OUT.exists() or PARENTS.exists():raise RuntimeError('development output exists')
    tables=parent_tables();models={};validation={}
    for name,rows in tables.items():
        state,banks=train_state(rows)
        models[name]=state
        validation[name]={'source_tasks':len(rows),
                          'selected_method':state['selected_method'],
                          'source_cv_correct':state['source_cv_correct'],
                          'by_bank':banks}
    write_json(PARENTS,models)
    write_json(OUT,{'scope':'inspected parent development only',
                    'parents':validation,
                    'parent_models_sha256':hashlib.sha256(PARENTS.read_bytes()).hexdigest()})
    print(json.dumps({name:{key:validation[name][key] for key in
                             ('source_tasks','selected_method','source_cv_correct')}
                      for name in tables},indent=2))


if __name__=='__main__':main()
