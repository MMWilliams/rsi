"""Development-only comparison of direct and factorized query-gain models."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import parent_tables,matrix,fit_method,values
from cross_family_meta_improver_transfer import stage_rows,interval
from cross_family_query_value_development import choose as fixed_choose

OUT=ROOT/'analysis/query-gain-hurdle-development-20260918.json'
STABLE=ROOT/'runs/stable-cross-family-improver-transfer-20260918'
LAMBDAS=(1.,10.,100.)
METHODS=('ridge_10','ridge_100',
         'logit_gain_1','logit_gain_10','logit_gain_100',
         'hurdle_1','hurdle_10','hurdle_100')


def target_rows():
    rows=[]
    for stage in ('a','b'):
        records=json.loads((STABLE/stage/'frozen_records.json').read_text())
        outcomes=json.loads((STABLE/stage/'results.json').read_text())['tasks']
        for r,o in zip(records,outcomes):
            assert r['id']==o['id']
            rows.append({'id':r['id'],'seed':r['seed'],'family':r['family'],
                         'public_block':r['public_block'],'features':r['features'],
                         'zero':int(o['zero']),'one':int(o['one']),
                         'gain':int(o['one'])-int(o['zero'])})
    assert len(rows)==576
    return rows


def normalize(rows,mean=None,scale=None):
    x=matrix(rows,'interaction')
    if mean is None:
        mean=x[:,1:].mean(axis=0);scale=np.maximum(x[:,1:].std(axis=0),.05)
    z=np.c_[np.ones(len(x)),(x[:,1:]-mean)/scale]
    return z,mean,scale


def logistic(z,y,lam):
    w=np.zeros(z.shape[1]);penalty=np.ones(len(w));penalty[0]=0
    for _ in range(40):
        p=1/(1+np.exp(-np.clip(z@w,-30,30)))
        weight=np.maximum(p*(1-p),1e-6)
        gradient=z.T@(p-y)+lam*penalty*w
        hessian=z.T@(z*weight[:,None])+lam*np.diag(penalty)
        step=np.linalg.solve(hessian,gradient)
        w-=step
        if float(np.max(np.abs(step)))<1e-7:break
    return w


def fit(rows,method):
    if method.startswith('ridge_'):
        return {'kind':'ridge','model':fit_method(rows,'interaction_'+method.split('_')[1])}
    kind,raw_lam=method.rsplit('_',1);lam=float(raw_lam)
    z,mean,scale=normalize(rows)
    if kind=='logit_gain':
        weights=[logistic(z,np.asarray([r['gain'] for r in rows],float),lam)]
    elif kind=='hurdle':
        wrong=np.asarray([1-r['zero'] for r in rows],float)
        weights=[logistic(z,wrong,lam),
                 logistic(z[wrong==1],np.asarray([r['one'] for r in rows if not r['zero']],float),lam)]
    else:raise ValueError(method)
    return {'kind':kind,'mean':mean.tolist(),'scale':scale.tolist(),
            'weights':[w.tolist() for w in weights]}


def predict(model,rows):
    if model['kind']=='ridge':return np.asarray(values(model['model'],rows))
    z,_,_=normalize(rows,np.asarray(model['mean']),np.asarray(model['scale']))
    probabilities=[1/(1+np.exp(-np.clip(z@np.asarray(w),-30,30)))
                   for w in model['weights']]
    return probabilities[0] if model['kind']=='logit_gain' else probabilities[0]*probabilities[1]


def chosen(group,model):
    scores=predict(model,group)
    order=sorted(zip(group,scores),key=lambda item:(float(item[1]),item[0]['id']),reverse=True)
    return {r['id'] for r,_ in order[:8]}


def correct(group,ids):
    assert len(ids)==8
    return sum(r['one'] if r['id'] in ids else r['zero'] for r in group)


def cross_validate(rows):
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        held=[r for r in rows if r['seed']==seed]
        source=[r for r in rows if r['seed']!=seed]
        assert len(held)==48
        scores={name:correct(held,chosen(held,fit(source,name))) for name in METHODS}
        scores['fixed_transform']=correct(held,fixed_choose(held,'transform_only'))
        banks.append({'seed':seed,'correct':scores})
    return banks


def main():
    if OUT.exists():raise RuntimeError('development output already exists')
    source=parent_tables()['initial']+stage_rows('admission')+stage_rows('a')+stage_rows('b')
    target=target_rows()
    assert len(source)==1440 and len({r['id'] for r in source})==1440
    assert set(r['id'] for r in source).isdisjoint(r['id'] for r in target)
    source_banks=cross_validate(source)
    source_scores={name:sum(b['correct'][name] for b in source_banks)
                   for name in (*METHODS,'fixed_transform')}
    chosen_method=max(METHODS,key=lambda name:(source_scores[name],-METHODS.index(name)))
    models={name:fit(source,name) for name in METHODS}
    target_banks=[]
    for seed in sorted({r['seed'] for r in target}):
        group=[r for r in target if r['seed']==seed]
        scores={name:correct(group,chosen(group,models[name])) for name in METHODS}
        scores['fixed_transform']=correct(group,fixed_choose(group,'transform_only'))
        target_banks.append({'seed':seed,'correct':scores})
    target_scores={name:sum(b['correct'][name] for b in target_banks)
                   for name in (*METHODS,'fixed_transform')}
    source_best_ridge=max(('ridge_10','ridge_100'),key=lambda name:source_scores[name])
    diff=[b['correct'][chosen_method]-b['correct'][source_best_ridge] for b in target_banks]
    result={'scope':'development only; stable target labels already opened by prior study',
            'source_tasks':len(source),'source_banks':len(source_banks),
            'target_tasks':len(target),'target_banks':len(target_banks),
            'methods':METHODS,'source_cv_correct':source_scores,
            'selected_from_source':chosen_method,
            'source_best_ridge':source_best_ridge,
            'target_correct':target_scores,
            'target_chosen_minus_ridge':{'by_bank':diff,'sum':sum(diff),
                                         'bank_bootstrap_95_sum':interval(diff)},
            'source_by_bank':source_banks,'target_by_bank':target_banks,
            'model_parameters':models,
            'limits':['This model screen cannot promote a method on opened target labels.',
                      'Equal new query calls do not equal historical acquisition or inference cost.']}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k not in
                      ('source_by_bank','target_by_bank','model_parameters')},indent=2))


if __name__=='__main__':main()
