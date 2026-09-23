"""Development-only whole-task CV for allocating a fixed probe-query budget."""
import hashlib
import json
from pathlib import Path

import numpy as np

from rsi.common import ROOT,write_json


SOURCE=ROOT/'analysis/probe-policy-development-v3.json'
FRACTION=1/3


def ridge(train):
    x=[]; y=[]
    for task in train:
        if not task['features']: continue
        for feature,outcome in zip(task['features'],task['outcomes']):
            x.append([*feature,task['n']/128,1.])
            y.append(float(outcome)-float(task['baseline']))
    x=np.asarray(x);y=np.asarray(y)
    scale=np.maximum(x[:,:-1].std(axis=0),.05)
    z=np.column_stack((x[:,:-1]/scale,np.ones(len(x))))
    penalty=np.eye(z.shape[1])*10; penalty[-1,-1]=0
    w=np.linalg.solve(z.T@z+penalty,z.T@y)
    return scale,w


def candidates(task,model):
    x=np.asarray([[*feature,task['n']/128] for feature in task['features']])
    scale,w=model
    scores=np.column_stack((x/scale,np.ones(len(x))))@w
    learned=int(np.argmax(scores))
    entropy=max(range(8),key=lambda j:(task['features'][j][0],-j))
    minimax=max(range(8),key=lambda j:(task['features'][j][2],-j))
    weighted=max(range(8),key=lambda j:(task['features'][j][1],-j))
    randomprobe=min(range(8),key=lambda j:hashlib.sha256((task['id']+':random:'+str(j)).encode()).digest())
    randompriority=int.from_bytes(hashlib.sha256((task['id']+':task').encode()).digest()[:8],'little')/2**64
    return {'learned':(learned,float(scores[learned])),
            'entropy':(entropy,task['features'][entropy][0]),
            'minimax':(minimax,task['features'][minimax][2]),
            'weighted_entropy':(weighted,task['features'][weighted][1]),
            'random':(randomprobe,randompriority)}


def main():
    rows=json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    folds=[[],[],[],[]]
    for task in rows:
        fold=int.from_bytes(hashlib.sha256(task['id'].encode()).digest()[:2],'little')%4
        folds[fold].append(task)
    methods=('learned','entropy','minimax','weighted_entropy','random')
    results=[]
    for fold in range(4):
        train=[task for k,group in enumerate(folds) if k!=fold for task in group]
        test=folds[fold]
        model=ridge(train)
        options={task['id']:candidates(task,model) for task in test if task['features']}
        budget=round(len(test)*FRACTION)
        baseline=sum(task['baseline'] for task in test)
        scores={}
        for method in methods:
            selected=sorted((task for task in test if task['id'] in options),
                            key=lambda task:(-options[task['id']][method][1],task['id']))[:budget]
            gains=sum(int(task['outcomes'][options[task['id']][method][0]])-int(task['baseline'])
                      for task in selected)
            scores[method]={'correct':baseline+gains,'gain':gains,
                            'selected_ids':[task['id'] for task in selected]}
        best_gains=sorted((max(int(value)-int(task['baseline']) for value in task['outcomes'])
                           for task in test if task['features']),reverse=True)
        results.append({'fold':fold,'n':len(test),'budget':budget,'baseline':baseline,
                        'oracle_budget_upper':baseline+sum(best_gains[:budget]),'methods':scores,
                        'coefficients':model[1].tolist(),'scale':model[0].tolist()})
    summary={'scope':'development only; four whole-task folds; one query on one third of tasks',
             'tasks':len(rows),'queries':sum(row['budget'] for row in results),
             'baseline':sum(row['baseline'] for row in results),
             'reachable':sum(task['reachable'] for task in rows),
             'oracle_budget_upper':sum(row['oracle_budget_upper'] for row in results),
             'methods':{method:sum(row['methods'][method]['correct'] for row in results)
                        for method in methods}}
    write_json(ROOT/'analysis/probe-budget-policy-development.json',{'summary':summary,'folds':results})
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
