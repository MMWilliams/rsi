"""Development-only value model and fixed-budget AST query allocation."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from rsi.common import ROOT, write_json


SOURCE = ROOT / 'runs/ast-probe-sensor-transfer-20260918'
OUT = ROOT / 'analysis/ast-query-allocation-development.json'
LAMBDAS = (.1, 1., 10., 100.)


def features(task, record, matrix):
    scores = np.asarray(record['scores'], dtype=float)
    order = record['order']; top = order[:20]
    std = max(float(scores.std()), .05)
    probe = record['first_probe']['top20_entropy']
    values = [matrix[i][probe] for i in top]
    counts = {}
    for value in values: counts[value] = counts.get(value, 0) + 1
    mass = np.asarray(list(counts.values()), dtype=float) / len(top)
    entropy = -sum(p * math.log(p) for p in mass)
    entropies = []
    for j in range(8):
        counts_j = {}
        for i in top:
            value = matrix[i][j]
            counts_j[value] = counts_j.get(value, 0) + 1
        probabilities = np.asarray(list(counts_j.values()), dtype=float) / len(top)
        entropies.append(-sum(p * math.log(p) for p in probabilities))
    text, output = task['visible'][0]
    return np.asarray([1., len(scores)/600,
                       (scores[order[0]]-scores[order[1]])/std,
                       (scores[order[0]]-np.median(scores))/std,
                       entropy, max(entropies), float(np.mean(entropies)),
                       len(counts)/20, 1-max(mass),
                       1-counts[values[0]]/20,
                       len(text)/12, len(output)/max(1,len(text))], dtype=float)


def fit(x, y1, y2, lam):
    mean = x[:,1:].mean(axis=0); scale = np.maximum(x[:,1:].std(axis=0), .05)
    z = np.c_[np.ones(len(x)), (x[:,1:]-mean)/scale]
    penalty = np.eye(z.shape[1]); penalty[0,0] = 0
    w1 = np.linalg.solve(z.T@z + lam*penalty, z.T@y1)
    w2 = np.linalg.solve(z.T@z + lam*penalty, z.T@y2)
    return mean, scale, w1, w2


def predict(model, x):
    mean, scale, w1, w2 = model
    z = np.c_[np.ones(len(x)), (x[:,1:]-mean)/scale]
    return z@w1, z@w2


def allocate(u1, u2, budget):
    """Exact multiple-choice knapsack with actions 0, 1 or 2 calls per task."""
    n = len(u1)
    previous = {0: (0., ())}
    for i in range(n):
        current = {}
        for spent,(value, actions) in previous.items():
            for action,gain in ((0,0.),(1,float(u1[i])),(2,float(u1[i]+u2[i]))):
                new_spent = spent + action
                if new_spent > budget: continue
                candidate = (value+gain, actions+(action,))
                if new_spent not in current or candidate[0] > current[new_spent][0]:
                    current[new_spent] = candidate
        previous = current
    return list(previous[budget][1])


def fixed(task_ids, x, budget, mode):
    assert budget == len(task_ids)
    if mode == 'one_each': return [1]*len(task_ids)
    if mode == 'random':
        scores = [hashlib.sha256(f'{key}:allocate'.encode()).digest() for key in task_ids]
    elif mode == 'entropy': scores = x[:,4].tolist()
    elif mode == 'disagreement': scores = x[:,9].tolist()
    else: raise ValueError(mode)
    order = sorted(range(len(task_ids)), key=lambda i: (scores[i], task_ids[i]), reverse=True)
    selected = set(order[:budget//2])
    return [2 if i in selected else 0 for i in range(len(task_ids))]


def utility(actions, base, one, two):
    return int(sum((base[i],one[i],two[i])[a] for i,a in enumerate(actions)))


def source_data():
    tasks = json.loads((SOURCE/'sealed_bank.json').read_text(encoding='utf-8'))
    records = json.loads((SOURCE/'frozen_records.json').read_text(encoding='utf-8'))
    matrix = json.loads((SOURCE/'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    results = json.loads((SOURCE/'results.json').read_text(encoding='utf-8'))['tasks']
    assert all(t['id']==r['id']==o['id'] for t,r,o in zip(tasks,records,results))
    x = np.stack([features(t,r,matrix[t['id']]) for t,r in zip(tasks,records)])
    base = np.asarray([int(r['correct']['baseline']) for r in results])
    one = np.asarray([int(r['correct']['top20_entropy_1']) for r in results])
    two = np.asarray([int(r['correct']['top20_entropy_2']) for r in results])
    return tasks,x,base,one,two


def main():
    if OUT.exists(): raise RuntimeError('development result exists')
    tasks,x,base,one,two = source_data()
    seeds = sorted({task['seed'] for task in tasks})
    comparisons = {}
    for lam in LAMBDAS:
        episodes=[]
        for seed in seeds:
            held = np.asarray([task['seed']==seed for task in tasks])
            source = ~held
            model = fit(x[source],one[source]-base[source],two[source]-one[source],lam)
            p1,p2 = predict(model,x[held])
            action = allocate(p1,p2,int(held.sum()))
            ids=[task['id'] for task in tasks if task['seed']==seed]
            episodes.append({'seed':seed,'learned':utility(action,base[held],one[held],two[held]),
                             **{name:utility(fixed(ids,x[held],len(ids),name),
                                             base[held],one[held],two[held])
                                for name in ('one_each','random','entropy','disagreement')},
                             'actions':action})
        comparisons[str(lam)]={'correct':{name:sum(e[name] for e in episodes)
                                            for name in ('learned','one_each','random','entropy','disagreement')},
                               'by_bank':episodes}
    chosen=max(LAMBDAS,key=lambda lam:(comparisons[str(lam)]['correct']['learned'],lam))
    model=fit(x,one-base,two-one,chosen)
    output={'scope':'development only; 96 source tasks already inspected',
            'tasks':len(tasks),'banks':len(seeds),'candidate_labels_source':
            json.loads((SOURCE/'manifest.json').read_text(encoding='utf-8'))['candidate_count'],
            'lambdas':LAMBDAS,'cross_validation':comparisons,
            'chosen_lambda':chosen,
            'feature_count':x.shape[1],
            'model':{'mean':model[0].tolist(),'scale':model[1].tolist(),
                     'w1':model[2].tolist(),'w2':model[3].tolist()}}
    write_json(OUT,output)
    print(json.dumps({k:v for k,v in output.items() if k not in ('model','cross_validation')}
                     | {'cross_validation':{k:v['correct'] for k,v in comparisons.items()}},indent=2))


if __name__=='__main__':main()
