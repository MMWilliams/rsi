"""Opened-bank model screen for first-output marginal-gain probability."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier,HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import source_rows,matrix,fit_method,values,BLOCKS
from cross_family_meta_improver_transfer import stage_rows
from pairwise_query_ranking_development import focused_rows,prediction,train_pairwise
from focused_feedback_development import fit_weighted


OUT=ROOT/'analysis/nonlinear-query-value-development-20260918.json'
PAIR_RUN=ROOT/'runs/pairwise-query-transfer-20260918'


def pair_run_rows():
    records=json.loads((PAIR_RUN/'frozen_records.json').read_text())
    outcomes=json.loads((PAIR_RUN/'results.json').read_text())['tasks']
    return [{**{key:r[key] for key in ('id','seed','family','public_block','features')},
             'zero':int(o['zero']),'one':int(o['one']),
             'gain':int(o['one'])-int(o['zero'])} for r,o in zip(records,outcomes)]


def tree_matrix(rows):
    base=np.asarray([r['features'] for r in rows],float)
    block=np.asarray([[float(r['public_block']==b) for b in BLOCKS] for r in rows])
    return np.c_[base,block]


def candidates():
    return {
        'logistic_c0.1':lambda:make_pipeline(StandardScaler(),LogisticRegression(
            C=.1,max_iter=2000,random_state=0)),
        'logistic_c1':lambda:make_pipeline(StandardScaler(),LogisticRegression(
            C=1.,max_iter=2000,random_state=0)),
        'hgb_leaf5':lambda:HistGradientBoostingClassifier(max_leaf_nodes=5,
            min_samples_leaf=30,learning_rate=.05,max_iter=100,l2_regularization=1.,
            random_state=0),
        'hgb_leaf9':lambda:HistGradientBoostingClassifier(max_leaf_nodes=9,
            min_samples_leaf=30,learning_rate=.05,max_iter=100,l2_regularization=1.,
            random_state=0),
        'extra_depth3':lambda:ExtraTreesClassifier(n_estimators=200,max_depth=3,
            min_samples_leaf=15,max_features=.8,n_jobs=1,random_state=0),
        'extra_depth5':lambda:ExtraTreesClassifier(n_estimators=200,max_depth=5,
            min_samples_leaf=15,max_features=.8,n_jobs=1,random_state=0),
    }


def evaluate(rows,pred):
    truth=np.asarray([r['gain'] for r in rows],float)
    by_seed=defaultdict(list)
    for i,r in enumerate(rows):by_seed[r['seed']].append(i)
    banks=[]
    for seed,indices in sorted(by_seed.items()):
        assert len(indices)==48
        selected=set(sorted(indices,key=lambda i:(float(pred[i]),rows[i]['id']),
                            reverse=True)[:8])
        banks.append({'seed':seed,
                      'correct':sum(rows[i]['one'] if i in selected else rows[i]['zero']
                                    for i in indices),
                      'selected_gain':sum(rows[i]['gain'] for i in selected),
                      'ast_calls':sum(rows[i]['public_block']==0x800 for i in selected)})
    return {'correct':sum(b['correct'] for b in banks),
            'selected_gain':sum(b['selected_gain'] for b in banks),
            'ast_calls':sum(b['ast_calls'] for b in banks),
            'brier':float(np.mean((pred-truth)**2)),
            'by_bank':banks}


def screen(train,target):
    y=np.asarray([r['gain'] for r in train],int)
    out={}
    for name,constructor in candidates().items():
        model=constructor()
        if name.startswith('logistic'):
            x_train=matrix(train,'interaction');x_target=matrix(target,'interaction')
        else:x_train=tree_matrix(train);x_target=tree_matrix(target)
        model.fit(x_train,y)
        out[name]=evaluate(target,model.predict_proba(x_target)[:,1])
    out['ridge10']=evaluate(target,values(fit_method(train,'interaction_10'),target))
    out['ridge100']=evaluate(target,values(fit_method(train,'interaction_100'),target))
    base=fit_weighted(train[:576],[1]*576)
    pair=train_pairwise(train,.001,False,base)
    out['pairwise001']=evaluate(target,prediction(pair,target))
    out['e0']=evaluate(target,values(base,target))
    return out


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    source=source_rows();admission=stage_rows('admission')
    added=admission+stage_rows('a')+stage_rows('b')
    early=screen(source+admission,stage_rows('a')+stage_rows('b'))
    focused=screen(source+added,focused_rows())
    pair=screen(source+added,pair_run_rows())
    panels={'meta_transfer':early,'focused_opened':focused,'pairwise_opened':pair}
    result={'scope':'all target banks already opened; method screen only',
            'source_rows':len(source),'early_feedback_rows':len(admission),
            'later_feedback_rows':len(added),
            'sklearn_version':__import__('sklearn').__version__,
            'panels':panels,
            'limits':['No fresh promotion claim from these panels.',
                      'All training gain labels require one-query counterfactuals from an exact research oracle.',
                      'The pairwise ranking score is uncalibrated, so its Brier number is not interpretable.']}
    write_json(OUT,result)
    print(json.dumps({panel:{name:{key:score[key] for key in ('correct','ast_calls','brier')}
                             for name,score in methods.items()}
                      for panel,methods in panels.items()},indent=2))


if __name__=='__main__':main()
