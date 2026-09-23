"""Opened matched-call screen of feedback-trained external-output allocation."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval


SOURCE=ROOT/'analysis/listwise-sensor-edit-source-20260918.json'
TARGET=ROOT/'analysis/listwise-sensor-edit-diagnostic-20260918.json'
OUT=ROOT/'analysis/listwise-sensor-allocator-development-20260918.json'
CALLS=4


def fit(rows,kind):
    x=np.asarray([r['public_features'] for r in rows],np.float32)
    y=np.asarray([r['listwise_query_effect']>0 for r in rows],int)
    assert set(y)=={0,1}
    if kind=='hgb':
        model=HistGradientBoostingClassifier(max_depth=2,max_iter=60,
            learning_rate=.05,min_samples_leaf=12,l2_regularization=5,
            random_state=905601)
    else:
        model=make_pipeline(StandardScaler(),LogisticRegression(
            C=.1,max_iter=1000,class_weight='balanced',random_state=905601))
    return model.fit(x,y)


def predict(model,rows):
    x=np.asarray([r['public_features'] for r in rows],np.float32)
    return model.predict_proba(x)[:,1]


def select(rows,priority):
    groups=defaultdict(list)
    for i,r in enumerate(rows):groups[r['seed']].append(i)
    return sorted(i for indices in groups.values()
                  for i in sorted(indices,key=lambda j:(-float(priority[j]),
                                                         rows[j]['id']))[:CALLS])


def summarize(rows,policies):
    by_bank=defaultdict(list)
    for i,r in enumerate(rows):by_bank[r['seed']].append(i)
    banks=[]
    for seed,ids in sorted(by_bank.items()):
        bank={'seed':seed}
        for name,selection in policies.items():
            chosen=set(selection)
            bank[name]=sum(rows[i]['labels']['listwise1' if i in chosen
                                                  else 'listwise0'] for i in ids)
            bank[name+'_captured']=sum(rows[i]['listwise_query_effect']>0
                                       for i in ids if i in chosen)
        banks.append(bank)
    totals={key:sum(b[key] for b in banks) for key in banks[0]
            if key!='seed'}
    comparisons={}
    for name in policies:
        if name in ('none','oracle','all_query'):continue
        for baseline in ('low_margin','probe_entropy','random','early_hgb'):
            if name==baseline:continue
            d=[b[name]-b[baseline] for b in banks]
            comparisons[f'{name}_minus_{baseline}']={
                'gain':sum(d),'positive_banks':sum(v>0 for v in d),
                'negative_banks':sum(v<0 for v in d),'interval':interval(d)}
    return {'tasks':len(rows),'calls_budgeted':len(by_bank)*CALLS,
            'totals':totals,'comparisons':comparisons,'banks':banks}


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    source=json.loads(SOURCE.read_text())['rows']
    target=json.loads(TARGET.read_text())['rows']
    assert len(source)==192 and len(target)==384
    assert len({r['seed'] for r in target})==48
    early={kind:fit(source,kind) for kind in ('hgb','logistic')}
    policies={'none':[],'all_query':list(range(len(target)))}
    for kind,model in early.items():
        policies['early_'+kind]=select(target,predict(model,target))
    feature=np.asarray([r['public_features'] for r in target],float)
    policies['low_margin']=select(target,-feature[:,-4])
    policies['probe_entropy']=select(target,feature[:,-2])
    policies['disagreement']=select(target,1-feature[:,-3])
    policies['random']=select(target,np.random.default_rng(905602).random(len(target)))
    policies['oracle']=select(target,np.asarray([
        r['listwise_query_effect'] for r in target]))
    seeds=sorted({r['seed'] for r in target})
    halves=(set(seeds[:24]),set(seeds[24:]))
    forecasts={name:np.zeros(len(target),float) for name in
               ('later_hgb','later_logistic','scrambled_hgb','duplicate_hgb')}
    for held in halves:
        admitted=[r for r in target if r['seed'] not in held]
        ids=[i for i,r in enumerate(target) if r['seed'] in held]
        held_rows=[target[i] for i in ids]
        rng=np.random.default_rng(905603+min(held))
        scrambled=[]
        for seed in sorted({r['seed'] for r in admitted}):
            group=[r for r in admitted if r['seed']==seed]
            perm=rng.permutation([r['listwise_query_effect'] for r in group])
            scrambled.extend([{**r,'listwise_query_effect':int(effect)}
                              for r,effect in zip(group,perm)])
        duplicate=[source[i] for i in rng.choice(len(source),len(admitted),
                                                 replace=True)]
        models={'later_hgb':fit(source+admitted,'hgb'),
                'later_logistic':fit(source+admitted,'logistic'),
                'scrambled_hgb':fit(source+scrambled,'hgb'),
                'duplicate_hgb':fit(source+duplicate,'hgb')}
        for name,model in models.items():
            forecasts[name][ids]=predict(model,held_rows)
    for name,priority in forecasts.items():
        policies[name]=select(target,priority)
    result=summarize(target,policies)
    result['scope']='opened cross-fit development only'
    result['source']={'early_tasks':len(source),
        'added_tasks_per_half':len(target)//2,
        'early_positive_edits':sum(r['listwise_query_effect']>0 for r in source),
        'target_positive_edits':sum(r['listwise_query_effect']>0 for r in target)}
    result['allocations']={name:[target[i]['id'] for i in ids]
                           for name,ids in policies.items()}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ('banks','allocations')},indent=2))


if __name__=='__main__':main()
