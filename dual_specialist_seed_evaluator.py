"""Scoped zero-query evaluator for the tested familiar/shifted AST contract.

The caller supplies a public task, a verified candidate pool, and a public
old-ranker record. No oracle output, hidden examples, family or generator
metadata is read here. Applicability outside the tested contract is the
caller's responsibility.
"""
from __future__ import annotations

import joblib
import numpy as np

from rsi.common import ROOT
from wide_candidate_reranker_development import features


FAMILIAR=ROOT/'analysis/familiar-ast-zero-query-models-20260918/early.joblib'
SHIFTED=ROOT/'analysis/shifted-zero-query-reranker-models-20260918/ab_top100.joblib'


def load_models():
    return {'familiar':joblib.load(FAMILIAR),
            'shifted':joblib.load(SHIFTED)}


def select(public_task,pool,public_record,models):
    old=public_record['orders']['old']
    n=min(100,len(old))
    if n==0:
        raise ValueError('candidate pool is empty')
    x=features(public_task,pool,public_record,n)
    choices={}
    for name in ('familiar','shifted'):
        p=models[name].predict_proba(np.asarray(x,np.float32))[:,1]
        rank=max(range(n),key=lambda i:(float(p[i]),-i))
        choices[name]={'index':old[rank], 'probability':float(p[rank]),
                       'old_rank':rank}
    expert=('shifted' if choices['shifted']['probability']>
            choices['familiar']['probability'] else 'familiar')
    index=choices[expert]['index']
    return {'index':index,'program':pool[index]['program'],'expert':expert,
            'choices':choices,'candidate_scores':2*n}
