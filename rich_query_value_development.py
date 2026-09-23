"""Development-only screen of richer public query-value features."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from ast_query_allocation_development import fit as ridge_fit,predict as ridge_predict
from cross_family_meta_improver_development import BLOCKS
from cross_family_meta_improver_transfer import interval

OUT=ROOT/'analysis/rich-query-value-development-20260918.json'
KINDS=('base_interaction','rich_basic','rich_block','rich_interaction')
LAMBDAS=(10.,100.,1000.)
METHODS=tuple(f'{kind}:{int(lam)}' for kind in KINDS for lam in LAMBDAS)


def load(name,stages):
    rows=[]
    for stage in stages:
        path=ROOT/f'analysis/rich-query-features-{name}-{stage}-20260918.json'
        rows+=json.loads(path.read_text())['rows']
    return rows


def matrix(rows,kind):
    base=np.asarray([r['base_features'] for r in rows],float)
    block=np.asarray([[float(r['public_block']==b) for b in BLOCKS] for r in rows])
    if kind=='base_interaction':
        extra=np.einsum('ni,nj->nij',block,base[:,2:10]).reshape(len(rows),-1)
        return np.c_[base,block,extra]
    rich=np.asarray([r['rich_features'] for r in rows],float)
    if kind=='rich_basic':return np.c_[base,rich]
    if kind=='rich_block':return np.c_[base,rich,block]
    if kind=='rich_interaction':
        chosen=np.c_[base[:,2:10],rich[:,1:8],rich[:,10:14]]
        extra=np.einsum('ni,nj->nij',block,chosen).reshape(len(rows),-1)
        return np.c_[base,rich,block,extra]
    raise ValueError(kind)


def fit(rows,method):
    kind,raw_penalty=method.split(':')
    y=np.asarray([r['gain'] for r in rows],float)
    mean,scale,w1,_=ridge_fit(matrix(rows,kind),y,np.zeros(len(y)),float(raw_penalty))
    return {'kind':kind,'penalty':float(raw_penalty),
            'mean':mean.tolist(),'scale':scale.tolist(),'weights':w1.tolist()}


def predict(model,rows):
    x=matrix(rows,model['kind'])
    mean=np.asarray(model['mean']);scale=np.asarray(model['scale'])
    weights=np.asarray(model['weights'])
    z=np.c_[np.ones(len(x)),(x[:,1:]-mean)/scale]
    return z@weights


def select(group,model):
    scores=predict(model,group)
    order=sorted(zip(group,scores),key=lambda item:(float(item[1]),item[0]['id']),reverse=True)
    return {r['id'] for r,_ in order[:8]}


def utility(group,ids):
    assert len(group)==48 and len(ids)==8
    return sum(r['one'] if r['id'] in ids else r['zero'] for r in group)


def cv(rows):
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        held=[r for r in rows if r['seed']==seed]
        source=[r for r in rows if r['seed']!=seed]
        assert len(held)==48
        scores={name:utility(held,select(held,fit(source,name))) for name in METHODS}
        banks.append({'seed':seed,'correct':scores})
    return banks


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    source=load('meta',('admission','a','b'))
    target=load('stable',('a','b'))
    assert len(source)==864 and len(target)==576
    assert set(r['id'] for r in source).isdisjoint(r['id'] for r in target)
    source_banks=cv(source)
    source_scores={name:sum(b['correct'][name] for b in source_banks) for name in METHODS}
    selected=max(METHODS,key=lambda name:(source_scores[name],-METHODS.index(name)))
    models={name:fit(source,name) for name in METHODS}
    target_banks=[]
    for seed in sorted({r['seed'] for r in target}):
        held=[r for r in target if r['seed']==seed]
        scores={name:utility(held,select(held,models[name])) for name in METHODS}
        target_banks.append({'seed':seed,'correct':scores})
    target_scores={name:sum(b['correct'][name] for b in target_banks) for name in METHODS}
    ridge=max((name for name in METHODS if name.startswith('base_interaction')),
              key=lambda name:source_scores[name])
    diffs=[b['correct'][selected]-b['correct'][ridge] for b in target_banks]
    result={'scope':'development only; stable target labels already opened in prior study',
            'source_tasks':len(source),'source_banks':len(source_banks),
            'target_tasks':len(target),'target_banks':len(target_banks),
            'methods':METHODS,'source_cv_correct':source_scores,
            'selected_from_source':selected,'source_best_base':ridge,
            'target_correct':target_scores,
            'target_selected_minus_base':{'by_bank':diffs,'sum':sum(diffs),
                                          'bank_bootstrap_95_sum':interval(diffs)},
            'source_by_bank':source_banks,'target_by_bank':target_banks,
            'models':models,
            'limits':['Target labels are opened development evidence, not promotion evidence.',
                      'Feature extraction requires prediction of eight outputs for every candidate.']}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ('models','source_by_bank','target_by_bank')},indent=2))


if __name__=='__main__':main()
