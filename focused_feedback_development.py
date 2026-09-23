"""Opened-bank screen of decision-focused verified feedback weights."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import source_rows,matrix,select,values
from cross_family_meta_improver_transfer import stage_rows


OUT=ROOT/'analysis/focused-feedback-development-20260918.json'
PENALTY=100.
VARIANTS=('uniform','new2','new4','positive4','mistake4','missed_gain4')


def fit_weighted(rows,weights):
    x=matrix(rows,'interaction');y=np.asarray([r['gain'] for r in rows],float)
    mean=x[:,1:].mean(axis=0);scale=np.maximum(x[:,1:].std(axis=0),.05)
    z=np.c_[np.ones(len(x)),(x[:,1:]-mean)/scale]
    penalty=np.eye(z.shape[1]);penalty[0,0]=0
    w=np.asarray(weights,float)
    coefficients=np.linalg.solve(z.T@(w[:,None]*z)+PENALTY*penalty,
                                 z.T@(w*y))
    # The shared prediction function expects two heads; query value uses head 0.
    return {'kind':'interaction','penalty':PENALTY,
            'params':[mean.tolist(),scale.tolist(),coefficients.tolist(),
                      np.zeros_like(coefficients).tolist()]}


def grouped(rows):
    result=defaultdict(list)
    for row in rows:result[row['seed']].append(row)
    assert all(len(group)==48 for group in result.values())
    return [result[seed] for seed in sorted(result)]


def score(model,groups):
    all_rows=[r for group in groups for r in group]
    pred=values(model,all_rows)
    truth=np.asarray([r['gain'] for r in all_rows],float)
    return {'correct':sum(sum(r['one'] if r['id'] in select(group,model)
                              else r['zero'] for r in group) for group in groups),
            'forecast_mse':float(np.mean((pred-truth)**2)),
            'by_bank':[sum(r['one'] if r['id'] in select(group,model)
                           else r['zero'] for r in group) for group in groups]}


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    source=source_rows();feedback=stage_rows('admission')
    assert len(source)==576 and len(feedback)==288
    baseline=fit_weighted(source,[1]*len(source))
    missed=set();mistakes=set()
    for group in grouped(feedback):
        chosen=select(group,baseline)
        missed.update(r['id'] for r in group if r['gain']>0 and r['id'] not in chosen)
        mistakes.update(r['id'] for r in group if r['gain']<=0 and r['id'] in chosen)
    models={'e0':baseline}
    for name in VARIANTS:
        weight=[]
        for row in feedback:
            if name=='uniform':v=1
            elif name=='new2':v=2
            elif name=='new4':v=4
            elif name=='positive4':v=4 if row['gain']>0 else 1
            elif name=='mistake4':v=4 if row['id'] in mistakes else 1
            elif name=='missed_gain4':v=4 if row['id'] in missed else 1
            weight.append(v)
        models[name]=fit_weighted(source+feedback,[1]*len(source)+weight)
    panels={'a':grouped(stage_rows('a')),'b':grouped(stage_rows('b'))}
    results={panel:{name:score(model,groups) for name,model in models.items()}
             for panel,groups in panels.items()}
    summary={'scope':'post hoc development on opened admission, A and B panels',
             'method':'interaction ridge 100, feedback example weights',
             'source_rows':len(source),'feedback_rows':len(feedback),
             'missed_positive_feedback':len(missed),
             'selected_zero_gain_feedback':len(mistakes),
             'panels':{panel:{name:{'correct':r['correct'],'forecast_mse':r['forecast_mse']}
                              for name,r in result.items()} for panel,result in results.items()}}
    write_json(OUT,{'summary':summary,'results':results,
                    'limits':['The validation and transfer panels were already opened before this screen.',
                              'Full counterfactual gain on all feedback tasks is a research-oracle expense.',
                              'Weights were researcher specified, not improver generated.']})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
