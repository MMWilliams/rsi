"""Opened-bank screen of query value after the supported E0 reranker."""
from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import fit_method,values,select
from cross_family_meta_improver_transfer import interval


PANELS=(ROOT/'runs/candidate-reranker-transfer-20260918',
        ROOT/'runs/candidate-reranker-replication-20260918')
OUT=ROOT/'analysis/candidate-conditioned-query-development-20260918.json'
QUERY_MODEL=ROOT/'runs/focused-feedback-transfer-20260918/models.json'
METHODS=('old_family_100','conditioned_family_100',
         'conditioned_interaction_100','conditioned_family_10')


def features(record,matrix):
    scores=np.asarray(record['old_scores'],float)
    old=record['orders']['old'];new=record['orders']['e0']
    later=record['orders']['e1'];small=record['orders']['leaf7']
    head=new[:20];probe=record['probe'];outputs=[matrix[i][probe] for i in head]
    n=max(len(head),1);counts=Counter(outputs);shares=np.asarray(list(counts.values()),float)/n
    top=outputs[0];std=max(float(scores.std()),.05)
    all_agree=[]
    for j in range(8):
        all_agree.append(sum(matrix[i][j]==matrix[head[0]][j] for i in head)/n)
    distinct_rank=next((rank for rank,index in enumerate(head)
                        if matrix[index][probe]!=top),n)
    old_rank={idx:rank for rank,idx in enumerate(old)}
    extra=[old_rank[new[0]]/max(len(old),1),
           (scores[old[0]]-scores[new[0]])/std,
           (scores[new[0]]-scores[new[1]])/std if len(new)>1 else 0.,
           -sum(x*math.log(x) for x in shares),
           counts[top]/n,max(shares),len(counts)/n,
           distinct_rank/n,
           sum(all_agree)/len(all_agree),max(all_agree),
           float(new[0]==old[0]),float(new[0]==later[0]),
           float(new[0]==small[0]),
           float(matrix[new[0]][probe]==matrix[old[0]][probe])]
    return list(record['query_features'])+extra


def source_rows():
    rows=[];panel_counts={}
    for path in PANELS:
        assert json.loads((path/'audit.json').read_text())['passed']
        records=json.loads((path/'frozen_records.json').read_text())
        predicted=json.loads((path/'predicted_probe_outputs.json').read_text())
        outcomes=json.loads((path/'results.json').read_text())['tasks']
        assert len(records)==len(outcomes)==576
        for record,outcome in zip(records,outcomes):
            assert record['id']==outcome['id']
            rows.append({'id':record['id'],'seed':record['seed'],
                'family':record['family'],'public_block':record['public_block'],
                'old_features':record['query_features'],
                'conditioned_features':features(record,predicted[record['id']]),
                'zero':outcome['zero']['e0'],'one':outcome['one']['e0'],
                'gain':outcome['one']['e0']-outcome['zero']['e0']})
        panel_counts[path.name]=len(records)
    assert len(rows)==1152 and len({r['id'] for r in rows})==1152
    return rows,panel_counts


def model_rows(rows,method):
    field='old_features' if method=='old_family_100' else 'conditioned_features'
    return [{**r,'features':r[field]} for r in rows]


def fit(rows,method):
    name=method.removeprefix('old_').removeprefix('conditioned_')
    return fit_method(model_rows(rows,method),name)


def predict(model,rows,method):
    return values(model,model_rows(rows,method))


def selected(rows,scores):
    order=sorted(range(len(rows)),key=lambda i:(float(scores[i]),rows[i]['id']),
                 reverse=True)
    return {rows[i]['id'] for i in order[:8]}


def utility(rows,ids):
    return sum(r['one'] if r['id'] in ids else r['zero'] for r in rows)


def cross_validation(rows):
    seeds=sorted({r['seed'] for r in rows});assert len(seeds)==24
    old=json.loads(QUERY_MODEL.read_text())['e0']
    banks=[]
    for seed in seeds:
        target=[r for r in rows if r['seed']==seed]
        source=[r for r in rows if r['seed']!=seed]
        assert len(target)==48
        scores={}
        for method in METHODS:
            model=fit(source,method)
            p=predict(model,target,method)
            scores[method]={'correct':utility(target,selected(target,p)),
                            'mse':float(np.mean((p-np.asarray([r['gain'] for r in target]))**2))}
        p=values(old,model_rows(target,'old_family_100'))
        scores['incumbent']={'correct':utility(target,selected(target,p)),
            'mse':float(np.mean((p-np.asarray([r['gain'] for r in target]))**2))}
        banks.append({'seed':seed,'scores':scores})
    totals={name:{'correct':sum(r['scores'][name]['correct'] for r in banks),
                  'mean_mse':sum(r['scores'][name]['mse'] for r in banks)/len(banks)}
            for name in METHODS+('incumbent',)}
    for name in METHODS:
        diffs=[r['scores'][name]['correct']-r['scores']['incumbent']['correct']
               for r in banks]
        totals[name]['versus_incumbent']={'sum':sum(diffs),
            'positive_banks':sum(x>0 for x in diffs),'interval':interval(diffs)}
    return totals,banks


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows,panels=source_rows();totals,banks=cross_validation(rows)
    ordered=max(METHODS,key=lambda name:(totals[name]['correct'],
        -METHODS.index(name)))
    output={'scope':'development on two opened audited panels; no fresh claim',
        'panels':panels,'tasks':len(rows),'banks':len(banks),
        'feature_count':len(rows[0]['conditioned_features']),
        'methods':METHODS,'totals':totals,'selected_method':ordered,
        'by_bank':banks}
    write_json(OUT,output)
    print(json.dumps({k:v for k,v in output.items() if k!='by_bank'},indent=2))


if __name__=='__main__':main()
