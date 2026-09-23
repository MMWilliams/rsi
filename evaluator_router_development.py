"""Development-only cross-episode router for two complementary evaluators."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json


SOURCE=ROOT/'analysis/pairwise-complementarity-development.json'
OUT=ROOT/'analysis/evaluator-router-development.json'
A='E192_classification'
B='pairwise_random'


def features(row):
    a=row['selected'][A];b=row['selected'][B]
    return [row['n']/256,a['top_probability'],a['margin'],
            b['top_probability'],b['margin'],
            b['top_probability']-a['top_probability'],
            b['margin']-a['margin'],1.]


def fit(rows):
    decisive=[r for r in rows if r['selected'][A]['correct']!=r['selected'][B]['correct']]
    x=np.asarray([features(r) for r in decisive],dtype=float)
    y=np.asarray([1 if r['selected'][B]['correct'] else -1 for r in decisive],dtype=float)
    scale=np.maximum(x[:,:-1].std(axis=0),.05)
    z=np.column_stack((x[:,:-1]/scale,np.ones(len(x))))
    penalty=np.eye(z.shape[1])*3;penalty[-1,-1]=0
    w=np.linalg.solve(z.T@z+penalty,z.T@y)
    return scale,w,len(decisive)


def evaluate(train,test):
    scale,w,decisive=fit(train)
    decisions=[]
    for row in test:
        x=np.asarray(features(row),dtype=float)
        score=float(np.r_[x[:-1]/scale,1.]@w)
        choice=B if score>0 else A
        higher_margin=B if row['selected'][B]['margin']>row['selected'][A]['margin'] else A
        random=B if hashlib.sha256(('router:'+row['id']).encode()).digest()[0]<128 else A
        decisions.append({'id':row['id'],'chosen':choice,'score':score,
                          'learned_correct':row['selected'][choice]['correct'],
                          'margin_correct':row['selected'][higher_margin]['correct'],
                          'random_correct':row['selected'][random]['correct']})
    return {'source_decisive_tasks':decisive,'source_tasks':len(train),
            'target_tasks':len(test),'E192':sum(r['selected'][A]['correct'] for r in test),
            'pairwise':sum(r['selected'][B]['correct'] for r in test),
            'learned':sum(r['learned_correct'] for r in decisions),
            'higher_margin':sum(r['margin_correct'] for r in decisions),
            'random':sum(r['random_correct'] for r in decisions),
            'oracle_union':sum(r['selected'][A]['correct'] or r['selected'][B]['correct']
                               for r in test),
            'scale':scale.tolist(),'weights':w.tolist(),'decisions':decisions}


def main():
    rows=json.loads(SOURCE.read_text(encoding='utf-8'))['episodes']
    a=rows[0]['tasks'];b=rows[1]['tasks']
    ab=evaluate(a,b);ba=evaluate(b,a)
    summary={'scope':'development only; whole-episode transfer',
             'A_to_B':{k:v for k,v in ab.items() if k not in ('scale','weights','decisions')},
             'B_to_A':{k:v for k,v in ba.items() if k not in ('scale','weights','decisions')}}
    write_json(OUT,{'summary':summary,'A_to_B':ab,'B_to_A':ba})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
