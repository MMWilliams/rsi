"""Development-only pairwise learning to rank unlabeled oracle probes."""
import hashlib
import json
from pathlib import Path

import numpy as np

from rsi.common import ROOT,write_json


SOURCE=ROOT/'analysis/probe-policy-development-v4.json'


def fit(train):
    diffs=[]; mass=[]
    for task in train:
        if not task['features']: continue
        x=np.asarray(task['features'],dtype=float)
        good=[i for i,v in enumerate(task['outcomes']) if v]
        bad=[i for i,v in enumerate(task['outcomes']) if not v]
        if not good or not bad: continue
        for i in good:
            for j in bad:
                diffs.append(x[i]-x[j]); mass.append(1/(len(good)*len(bad)))
    diffs=np.asarray(diffs);mass=np.asarray(mass);mass/=mass.sum()
    scale=np.maximum(diffs.std(axis=0),.05)
    z=diffs/scale
    w=np.zeros(z.shape[1])
    for _ in range(700):
        logits=np.clip(z@w,-20,20)
        slope=1/(1+np.exp(logits))
        gradient=-(z.T@(slope*mass))+.02*w
        w-=.25*gradient
    return scale,w


def main():
    rows=json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    folds=[[],[],[],[]]
    for task in rows:
        fold=int.from_bytes(hashlib.sha256(task['id'].encode()).digest()[:2],'little')%4
        folds[fold].append(task)
    decisions={}; models=[]
    for index in range(4):
        model=fit([task for k,group in enumerate(folds) if k!=index for task in group])
        scale,w=model
        for task in folds[index]:
            if not task['features']: continue
            x=np.asarray(task['features'],dtype=float)
            decision=int(np.argmax((x-x.mean(axis=0))/scale@w))
            decisions[task['id']]=decision
        models.append({'fold':index,'scale':scale.tolist(),'weights':w.tolist()})
    summary={'scope':'development only; four whole-task folds; pairwise feedback from old oracle labels',
             'tasks':len(rows),'reachable':sum(r['reachable'] for r in rows),
             'baseline':sum(r['baseline'] for r in rows),
             'minimax':sum(r['outcomes'][max(range(8),key=lambda j:(r['features'][j][2],-j))]
                           for r in rows if r['features']),
             'pairwise_learned':sum(r['outcomes'][decisions[r['id']]] for r in rows if r['features'])}
    write_json(ROOT/'analysis/probe-pairwise-development-v4.json',{'summary':summary,'models':models,
                                                                 'decisions':decisions})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
