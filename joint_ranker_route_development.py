"""Opened-bank screen of public task-level ranker edit selection."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from candidate_conditioned_query_development import features as query_features
from cross_family_meta_improver_development import fit_method,values
from cross_family_meta_improver_transfer import interval


PANELS=(ROOT/'runs/candidate-reranker-transfer-20260918',
        ROOT/'runs/candidate-reranker-replication-20260918',
        ROOT/'runs/candidate-conditioned-query-transfer-20260918',
        ROOT/'runs/candidate-query-cost-transfer-20260918')
OUT=ROOT/'analysis/joint-ranker-route-development-20260918.json'
NAMES=('old','e0','e1')
METHODS=('family_mean','family_100','interaction_100')


def public_features(record,matrix):
    base=query_features(record,matrix)
    old=record['orders']['old'];e0=record['orders']['e0']
    e1=record['orders']['e1'];scores=np.asarray(record['old_scores'],float)
    std=max(float(scores.std()),.05)
    old_rank={idx:i for i,idx in enumerate(old)}
    probe=record['probe']
    extra=[old_rank[e1[0]]/len(old),
           (scores[old[0]]-scores[e1[0]])/std,
           float(e1[0]==old[0]),
           float(matrix[e0[0]][probe]==matrix[e1[0]][probe]),
           sum(matrix[e0[0]][j]==matrix[e1[0]][j] for j in range(8))/8]
    return base+extra


def source_rows():
    rows=[];counts={}
    for panel in PANELS:
        assert json.loads((panel/'audit.json').read_text())['passed']
        records=json.loads((panel/'frozen_records.json').read_text())
        matrix=json.loads((panel/'predicted_probe_outputs.json').read_text())
        outcomes=json.loads((panel/'results.json').read_text())['tasks']
        assert len(records)==len(outcomes)==576
        for record,outcome in zip(records,outcomes):
            assert record['id']==outcome['id']
            rows.append({'id':record['id'],'seed':record['seed'],
                'family':record['family'],'public_block':record['public_block'],
                'features':public_features(record,matrix[record['id']]),
                'zero':{name:outcome['zero'][name] for name in NAMES}})
        counts[panel.name]=len(records)
    assert len(rows)==2304 and len({r['id'] for r in rows})==2304
    return rows,counts


def training_rows(rows,name):
    return [{**r,'gain':r['zero'][name]-r['zero']['e1']} for r in rows]


def route(train,target,method):
    predictions={'e1':np.zeros(len(target))}
    for name in ('old','e0'):
        model=fit_method(training_rows(train,name),method)
        predictions[name]=values(model,target)
    choices=[]
    for i in range(len(target)):
        choices.append(max(NAMES,key=lambda name:(float(predictions[name][i]),
                                           -NAMES.index(name))))
    return choices


def evaluate(rows,choices):
    return sum(r['zero'][choice] for r,choice in zip(rows,choices))


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows,panels=source_rows();seeds=sorted({r['seed'] for r in rows})
    assert len(seeds)==48
    banks=[]
    for seed in seeds:
        train=[r for r in rows if r['seed']!=seed]
        target=[r for r in rows if r['seed']==seed]
        bank={'seed':seed,'e1':evaluate(target,['e1']*48),
              'e0':evaluate(target,['e0']*48),
              'old':evaluate(target,['old']*48),
              'hindsight_task':sum(max(r['zero'].values()) for r in target)}
        for method in METHODS:
            bank[method]=evaluate(target,route(train,target,method))
        banks.append(bank)
    totals={name:sum(r[name] for r in banks) for name in
            ('e1','e0','old','hindsight_task')+METHODS}
    comparisons={name:{'gain_vs_e1':totals[name]-totals['e1'],
        'positive_banks':sum(r[name]>r['e1'] for r in banks),
        'interval':interval([r[name]-r['e1'] for r in banks])}
        for name in METHODS}
    result={'scope':'opened source cross-validation only, no fresh gate',
        'panels':panels,'tasks':len(rows),'banks':len(seeds),
        'feature_count':len(rows[0]['features']),
        'totals':totals,'comparisons':comparisons,'by_bank':banks}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='by_bank'},indent=2))


if __name__=='__main__':main()
