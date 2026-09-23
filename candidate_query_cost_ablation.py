"""Opened-bank ablation of costly E1/7-leaf agreement query features."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from candidate_conditioned_query_development import source_rows,features,selected,utility
from cross_family_meta_improver_development import fit_method,values
from cross_family_meta_improver_transfer import interval


OUT=ROOT/'analysis/candidate-query-cost-ablation-20260918.json'
TARGET=ROOT/'runs/candidate-conditioned-query-transfer-20260918'


def cheap(vector):
    assert len(vector)==26
    return vector[:23]+vector[25:]


def as_model_rows(rows,kind):
    return [{**r,'features':(cheap(r['conditioned_features']) if kind=='cheap'
                              else r['conditioned_features'])} for r in rows]


def fit(rows,kind):
    return fit_method(as_model_rows(rows,kind),'interaction_100')


def predict(model,rows,kind):
    return values(model,as_model_rows(rows,kind))


def score_bank(rows,values_):
    return utility(rows,selected(rows,values_))


def target_rows():
    assert json.loads((TARGET/'audit.json').read_text())['passed']
    records=json.loads((TARGET/'frozen_records.json').read_text())
    matrix=json.loads((TARGET/'predicted_probe_outputs.json').read_text())
    outcomes=json.loads((TARGET/'results.json').read_text())['tasks']
    result=[]
    for record,outcome in zip(records,outcomes):
        assert record['id']==outcome['id']
        result.append({'id':record['id'],'seed':record['seed'],
            'public_block':record['public_block'],
            'conditioned_features':features(record,matrix[record['id']]),
            'zero':outcome['zero']['e0'],'one':outcome['one']['e0'],
            'gain':outcome['one']['e0']-outcome['zero']['e0']})
    return result


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    source,_=source_rows();seeds=sorted({r['seed'] for r in source})
    cv=[]
    for seed in seeds:
        train=[r for r in source if r['seed']!=seed]
        held=[r for r in source if r['seed']==seed]
        cv.append({'seed':seed,**{kind:score_bank(held,predict(fit(train,kind),held,kind))
                                  for kind in ('full','cheap')}})
    target=target_rows();models={kind:fit(source,kind) for kind in ('full','cheap')}
    scores={kind:predict(models[kind],target,kind) for kind in models}
    target_banks=[]
    for seed in sorted({r['seed'] for r in target}):
        ix=[i for i,r in enumerate(target) if r['seed']==seed]
        group=[target[i] for i in ix]
        target_banks.append({'seed':seed,**{kind:score_bank(group,scores[kind][ix])
            for kind in scores}})
    truth=np.asarray([r['gain'] for r in target])
    summary={'source_cv':{kind:sum(r[kind] for r in cv) for kind in models},
        'opened_third_panel':{kind:{'correct':sum(r[kind] for r in target_banks),
            'mse':float(np.mean((scores[kind]-truth)**2))} for kind in models}}
    diffs=[r['cheap']-r['full'] for r in target_banks]
    summary['opened_cheap_minus_full']={'sum':sum(diffs),
        'positive_banks':sum(x>0 for x in diffs),'interval':interval(diffs)}
    result={'scope':'development only; all labels on the third panel opened',
        'cheap_features':'drop E0/E1 and E0/7-leaf top-choice agreement',
        'cheap_feature_count':24,'full_feature_count':26,
        'saved_target_inference':'two model predict-proba passes on top-20 features',
        'summary':summary,'source_cv_by_bank':cv,'opened_target_by_bank':target_banks}
    write_json(OUT,result)
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
