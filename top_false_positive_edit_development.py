"""Development-only anchored training edit for top-ranked false positives."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_transfer import choose
from pairwise_evaluator_development import target_b
from edit_effect_development import score
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
TARGET_A=ROOT/'analysis/improver-acquisition-target-development.json'
OUT=ROOT/'analysis/top-false-positive-edit-development.json'
LAMBDAS=(.01,.1,1.)


def mistakes(rows,w):
    differences=[]
    for row in rows:
        x=np.asarray(row['structural'],dtype=float)
        y=np.asarray(row['labels'],dtype=bool)
        if not any(y):continue
        p=1/(1+np.exp(-np.clip(x@w,-30,30)))
        top=choose(p,[{'program':z} for z in row['programs']])
        if y[top]:continue
        positives=np.flatnonzero(y)
        best=max(positives,key=lambda i:(float(p[i]),
            -len(row['programs'][i]),row['programs'][i]))
        differences.append(x[best]-x[top])
    return np.asarray(differences)


def anchored_update(base,diff,penalty):
    w=base.copy()
    for _ in range(240):
        logits=np.clip(diff@w,-30,30)
        slope=1/(1+np.exp(logits))
        grad=-(diff.T@slope)/len(diff)+penalty*(w-base)
        w-=.2*grad
    return w


def source_score(w,rows):
    return sum(row['labels'][choose(
        1/(1+np.exp(-np.clip(np.asarray(row['structural'])@w,-30,30))),
        [{'program':z} for z in row['programs']])]
        for row in rows)


def main():
    seed_growth.structure=bool_safe_structure
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    rows=source['tasks'];base=np.asarray(source['full_weights'])
    diff=mistakes(rows,base)
    a=json.loads(TARGET_A.read_text(encoding='utf-8'))
    b=target_b()
    models={'E192':base}
    for penalty in LAMBDAS:
        models[f'anchor_{penalty}']=anchored_update(base,diff,penalty)
    scores={name:(score(w,a),score(w,b)) for name,w in models.items()}
    summary={'scope':'development only; target banks inspected',
             'source_mistakes_with_correct_candidate':len(diff),
             'source_tasks':len(rows),'source_candidate_labels':sum(r['n'] for r in rows),
             'models':{name:{'source_correct':source_score(w,rows),
                             'A_correct':scores[name][0][0],
                             'B_correct':scores[name][1][0],
                             'A_brier':scores[name][0][1],
                             'B_brier':scores[name][1][1],
                             'weight_shift_norm':float(np.linalg.norm(w-base))}
                       for name,w in models.items()}}
    write_json(OUT,{'summary':summary,'weights':{k:v.tolist() for k,v in models.items()}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
