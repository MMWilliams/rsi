"""Development-only evaluator training edits using verified candidate pairs."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import logistic,representation
from mixed_probe_diagnostic import bool_safe_structure
from edit_effect_development import score
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
TARGET_A=ROOT/'analysis/improver-acquisition-target-development.json'
RUN_B=ROOT/'runs/improver-acquisition-transfer-20260917'
OUT=ROOT/'analysis/pairwise-evaluator-development.json'
PAIRS_PER_SIDE=8


def target_b():
    tasks=json.loads((RUN_B/'target_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((RUN_B/'candidate_pools.json').read_text(encoding='utf-8'))
    result=[]
    for task in tasks:
        rows=pools[task['id']]
        x=representation({'id':task['id'],'visible':task['visible']},rows)['structural']
        result.append({'id':task['id'],'n':len(rows),
                       'programs':[r['program'] for r in rows],
                       'structural':x.tolist(),
                       'labels':[bool(evaluate_program(r['program'],task['hidden'][8:]))
                                 for r in rows]})
    return result


def pairs(source,model,hard):
    diffs=[];mass=[];used=0
    for row in source:
        x=np.asarray(row['structural'],dtype=float)
        y=np.asarray(row['labels'],dtype=bool)
        positive=np.flatnonzero(y);negative=np.flatnonzero(~y)
        if not len(positive) or not len(negative):continue
        if hard:
            p=1/(1+np.exp(-np.clip(x@model,-30,30)))
            positive=sorted(positive,key=lambda i:(p[i],i))[:PAIRS_PER_SIDE]
            negative=sorted(negative,key=lambda i:(-p[i],i))[:PAIRS_PER_SIDE]
        else:
            seed=int.from_bytes(hashlib.sha256(('pairs:'+row['id']).encode()).digest()[:8],
                                'little')
            rng=np.random.default_rng(seed)
            positive=rng.choice(positive,size=min(PAIRS_PER_SIDE,len(positive)),
                                replace=False).tolist()
            negative=rng.choice(negative,size=min(PAIRS_PER_SIDE,len(negative)),
                                replace=False).tolist()
        difference=(x[positive,None,:]-x[None,negative,:]).reshape(-1,x.shape[1])
        diffs.append(difference)
        mass.append(np.full(len(difference),1/len(difference)))
        used+=1
    x=np.concatenate(diffs)
    mass=np.concatenate(mass)
    return x,mass,used


def main():
    seed_growth.structure=bool_safe_structure
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    rows=source['tasks']
    e192=np.asarray(source['full_weights'],dtype=float)
    target_a=json.loads(TARGET_A.read_text(encoding='utf-8'))
    target_b_rows=target_b()
    models={'E192_classification':e192}
    pair_counts={}
    for name,hard in (('pairwise_random',False),('pairwise_hard',True)):
        x,mass,used=pairs(rows,e192,hard)
        w=logistic(x,np.ones(len(x)),mass)
        models[name]=w
        models['combined_'+name]=.5*e192+.5*w
        pair_counts[name]={'mixed_label_tasks':used,'pairs':len(x)}
    scores={}
    for name,w in models.items():
        a=score(w,target_a);b=score(w,target_b_rows)
        scores[name]={'A':{'correct':a[0],'brier':a[1],'auc':a[2]},
                      'B':{'correct':b[0],'brier':b[1],'auc':b[2]},
                      'combined_correct':a[0]+b[0]}
    summary={'scope':'development only; targets inspected before model design',
             'source_tasks':len(rows),'source_candidate_labels':sum(r['n'] for r in rows),
             'pairs_per_side':PAIRS_PER_SIDE,'pair_counts':pair_counts,'scores':scores}
    write_json(OUT,{'summary':summary,'weights':{k:v.tolist() for k,v in models.items()}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
