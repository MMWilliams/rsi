"""Opened threshold screen for a task-regime model grounded in paired edit effects."""
from __future__ import annotations

import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from shifted_zero_query_reranker_development import MODELS
from zero_query_router_development import SOURCE, MIXED, rows_for, score
from zero_query_router_controls_development import fit
from cross_family_meta_improver_transfer import interval


OUT=ROOT/'analysis/zero-query-route-threshold-development-20260918.json'
THRESHOLDS=(.3,.4,.5,.6,.7,.8,.9,.95,.99)


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    models={name:joblib.load(MODELS/f'{name}_top100.joblib')
            for name in ('a','ab')}
    source=[r for path in SOURCE for r in rows_for(path,models)]
    mixed=rows_for(MIXED,models)
    seeds=sorted({r['seed'] for r in mixed})
    halves=[set(seeds[:12]),set(seeds[12:])]
    rows=[]
    for target_seeds in halves:
        train=[r for r in mixed if r['seed'] not in target_seeds]
        target=[r for r in mixed if r['seed'] in target_seeds]
        model=fit(source+train)
        p=model.predict_proba(np.asarray([r['features'] for r in target],
                                             np.float32))[:,1]
        shift=np.mean([r['effect'] for r in source+train
                       if r['domain']=='shifted'])
        familiar=np.mean([r['effect'] for r in source+train
                          if r['domain']=='familiar'])
        for row,prob in zip(target,p):
            rows.append({**row,'p':float(prob),
                         'expected_effect':float(prob*shift+(1-prob)*familiar),
                         'shift_prior':float(shift),
                         'familiar_prior':float(familiar)})
    rows.sort(key=lambda r:(r['seed'],r['id']))
    choices={f'p_{threshold}':np.asarray([r['p']>=threshold for r in rows])
             for threshold in THRESHOLDS}
    choices['prior_effect']=np.asarray([r['expected_effect']>0 for r in rows])
    choices['e0']=np.zeros(len(rows),bool)
    choices['ab']=np.ones(len(rows),bool)
    result=score(rows,choices)
    result['probability_summary']={domain:{
        'min':float(min(r['p'] for r in rows if r['domain']==domain)),
        'median':float(np.median([r['p'] for r in rows
                                  if r['domain']==domain])),
        'max':float(max(r['p'] for r in rows if r['domain']==domain))}
        for domain in ('familiar','shifted')}
    result['effect_priors']={domain:float(np.mean([r['effect'] for r in source
                             if r['domain']==domain]))
                             for domain in ('familiar','shifted')}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='banks'},indent=2))


if __name__=='__main__':
    main()
