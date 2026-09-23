"""Opened matched-cost screen of feedback-driven shortlist-width edits."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier,HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT,write_json
from cross_family_meta_improver_transfer import interval


SOURCE=ROOT/'analysis/selective-width-rows-development-20260918.json'
OUT=ROOT/'analysis/selective-width-policy-development-20260918.json'
FIRST=('zero-query-mixed-integration-transfer-20260918',
       'three-action-improver-transfer-20260918')
TARGET='dual-specialist-integration-transfer-20260918'
CALLS_PER_BANK=4


def fit(rows):
    x=np.asarray([r['public_features'] for r in rows],np.float32)
    y=np.asarray([r['effect_200'] for r in rows],float)
    scaler=StandardScaler().fit(x)
    ridge=Ridge(alpha=30.).fit(scaler.transform(x),y)
    hgb=HistGradientBoostingRegressor(max_depth=2,max_iter=60,
        learning_rate=.05,min_samples_leaf=12,l2_regularization=5,
        random_state=221).fit(x,y)
    clf=lambda:HistGradientBoostingClassifier(max_depth=2,max_iter=60,
        learning_rate=.05,min_samples_leaf=12,l2_regularization=5,
        random_state=221)
    head100=clf().fit(x,np.asarray([r['outcomes']['100'] for r in rows],int))
    head200=clf().fit(x,np.asarray([r['outcomes']['200'] for r in rows],int))
    return scaler,ridge,hgb,head100,head200


def forecasts(model,rows):
    scaler,ridge,hgb,head100,head200=model
    x=np.asarray([r['public_features'] for r in rows],np.float32)
    return {'ridge':ridge.predict(scaler.transform(x)),
            'hgb':hgb.predict(x),
            'twohead':head200.predict_proba(x)[:,1]-
                      head100.predict_proba(x)[:,1]}


def select(rows,score):
    groups=defaultdict(list)
    for i,r in enumerate(rows):groups[r['seed']].append(i)
    chosen=set()
    for seed,indices in groups.items():
        chosen.update(sorted(indices,key=lambda i:(-float(score[i]),rows[i]['id']))
                      [:CALLS_PER_BANK])
    return chosen


def policy_results(rows,policies):
    groups=defaultdict(list)
    for i,r in enumerate(rows):groups[r['seed']].append(i)
    banks=[]
    for seed,indices in sorted(groups.items()):
        bank={'seed':seed}
        for name,chosen in policies.items():
            bank[name]=sum(rows[i]['outcomes']['200' if i in chosen else '100']
                           for i in indices)
            bank[name+'_extra_scores']=sum(rows[i]['extra_candidate_scores_200']
                                           for i in indices if i in chosen)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(
                    rows[i]['outcomes']['200' if i in chosen else '100']
                    for i in indices if rows[i]['domain']==domain)
        banks.append(bank)
    totals={k:sum(b[k] for b in banks) for k in banks[0] if k!='seed'}
    pairs=(('later_ridge','early_ridge'),('later_ridge','scrambled_ridge'),
           ('later_ridge','duplicate_ridge'),('later_ridge','shifted_priority'),
           ('later_ridge','uncertain'),('shifted_priority','random'))
    comparisons={f'{a}_minus_{b}':{'gain':sum(r[a]-r[b] for r in banks),
        'wins':sum(r[a]>r[b] for r in banks),
        'losses':sum(r[a]<r[b] for r in banks),
        'interval':interval([r[a]-r[b] for r in banks])}
        for a,b in pairs}
    return {'tasks':len(rows),'banks':banks,'totals':totals,
            'comparisons':comparisons}


def main():
    if OUT.exists():raise RuntimeError('development exists')
    source=json.loads(SOURCE.read_text())
    training=[r for r in source['rows'] if r['panel'] in FIRST]
    target=[r for r in source['rows'] if r['panel']==TARGET]
    assert len(training)==384 and len(target)==192
    early=fit(training)
    scores=forecasts(early,target)
    policies={'none':set(),'all200':set(range(len(target)))}
    for name,values in scores.items():
        policies['early_'+name]=select(target,values)
    p_shift=np.asarray([r['public_features'][-4] for r in target])
    p_conf=np.asarray([max(r['public_features'][-6],r['public_features'][-5])
                       for r in target])
    policies['shifted_priority']=select(target,p_shift)
    policies['uncertain']=select(target,-p_conf)
    rng=np.random.default_rng(904910)
    policies['random']=select(target,rng.random(len(target)))
    policies['oracle']=select(target,np.asarray([r['effect_200'] for r in target]))
    seeds=sorted({r['seed'] for r in target})
    halves=(set(seeds[:12]),set(seeds[12:]))
    predictions={name:np.zeros(len(target),float)
                 for name in ('later_ridge','scrambled_ridge','duplicate_ridge')}
    for held in halves:
        admit=[r for r in target if r['seed'] not in held]
        ids=[i for i,r in enumerate(target) if r['seed'] in held]
        rng2=np.random.default_rng(904911+min(held))
        scrambled=[]
        for seed in sorted({r['seed'] for r in admit}):
            group=[r for r in admit if r['seed']==seed]
            perm=rng2.permutation([r['effect_200'] for r in group])
            scrambled.extend([{**r,'effect_200':int(v)}
                              for r,v in zip(group,perm)])
        duplicate=[]
        for domain in ('familiar','shifted'):
            group=[r for r in training if r['domain']==domain]
            duplicate.extend([group[i] for i in rng2.choice(len(group),48,
                                                              replace=True)])
        conditions={'later_ridge':training+admit,
                    'scrambled_ridge':training+scrambled,
                    'duplicate_ridge':training+duplicate}
        held_rows=[target[i] for i in ids]
        for name,rows in conditions.items():
            values=forecasts(fit(rows),held_rows)['ridge']
            predictions[name][ids]=values
    for name,values in predictions.items():
        policies[name]=select(target,values)
    result=policy_results(target,policies)
    result['source']={'training_tasks':len(training),
        'target_tasks':len(target),'positive_training_edits':sum(
            r['effect_200']>0 for r in training),
        'negative_training_edits':sum(r['effect_200']<0 for r in training),
        'positive_target_edits':sum(r['effect_200']>0 for r in target),
        'negative_target_edits':sum(r['effect_200']<0 for r in target)}
    result['scope']='opened development only; fixed four widened tasks per bank'
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='banks'},indent=2))


if __name__=='__main__':main()
