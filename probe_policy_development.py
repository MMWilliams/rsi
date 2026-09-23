"""Whole-task cross-validation of a learned probe selector (development only)."""
from __future__ import annotations

import hashlib
import json
import math
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from seed_growth import representation,predict,pick
from active_probe_diagnostic import initial_model,program_output,choose_probe
from active_probe_sparse_pilot import larger_pool


SOURCE_SEED=209501
COUNT=384


def task_data(task,rows,model):
    public={'id':task['id'],'visible':task['visible']}
    record={'id':task['id'],'public':public,'rows':rows,'features':representation(public,rows)}
    scores=predict(model,record)['ensemble']
    if not rows: return {'id':task['id'],'n':0,'reachable':False,'baseline':False,'features':[],
                         'outcomes':[],'entropy':0,'random':0,'oracle':False,'sequential':{}}
    n=len(rows); order=sorted(range(n),key=lambda i:(-scores[i],len(rows[i]['program']),rows[i]['program']))
    top=order[0]; correct=[evaluate_program(row['program'],task['hidden'][8:]) for row in rows]
    probes=task['hidden'][:8]
    outputs=[[program_output(row['program'],pair[0]) for pair in probes] for row in rows]
    public_chars={c for text,_ in task['visible'] for c in text}
    raw=np.asarray(scores,dtype=float)
    weights=np.exp((raw-raw.max())/.1); weights/=weights.sum()
    features=[]; outcomes=[]; entropies=[]
    for j,pair in enumerate(probes):
        groups=defaultdict(list)
        for i in range(n): groups[outputs[i][j]].append(i)
        proportions=[len(v)/n for v in groups.values()]
        mass=[sum(weights[v]) for v in groups.values()]
        expected_max=sum(max(weights[i] for i in indices) for indices in groups.values())
        entropy=-sum(p*math.log(p) for p in proportions)
        wentropy=-sum(p*math.log(p) for p in mass)
        topclass=groups[outputs[top][j]]
        candidate=np.asarray([i for i in range(n) if outputs[i][j]==pair[1]],dtype=int)
        selected=next((i for i in order if i in set(candidate)),top)
        outcomes.append(bool(correct[selected]))
        entropies.append(entropy)
        value=[entropy,wentropy,1-max(proportions),1-max(mass),
               len(groups)/max(1,n),1-len(topclass)/n,1-sum(weights[topclass]),
               sum(outputs[i][j] is None for i in range(n))/n,
               float(np.std([len(v) if v is not None else 0 for v in (outputs[i][j] for i in range(n))]))/10,
               float(np.mean([len(v) if v is not None else 0 for v in (outputs[i][j] for i in range(n))]))/10,
               expected_max,1-sum(p*p for p in mass),
               float(outputs[order[0]][j]!=outputs[order[1]][j]) if n>1 else 0.,
               len(set(pair[0])-public_chars)/max(1,len(set(pair[0]))),len(pair[0])/10]
        features.append(value)
    random_choice=min(range(8),key=lambda j:hashlib.sha256((task['id']+':random:'+str(j)).encode()).digest())
    entropy_choice=max(range(8),key=lambda j:(entropies[j],-j))
    sequential={}
    for mode in ('random','entropy','weighted_entropy','minimax'):
        remaining=list(range(n)); used=[]; curve=[]
        for _ in range(2):
            j=choose_probe(task['id'],outputs,remaining,used,scores,mode)
            used.append(j)
            matched=[i for i in remaining if outputs[i][j]==probes[j][1]]
            if matched: remaining=matched
            selected=next((i for i in order if i in set(remaining)),top)
            curve.append(bool(correct[selected]))
        sequential[mode]=curve
    return {'id':task['id'],'n':n,'reachable':any(correct),'baseline':bool(correct[top]),
            'features':features,'outcomes':outcomes,'entropy':entropy_choice,
            'random':random_choice,'oracle':any(outcomes),'sequential':sequential}


def fit(train):
    x=[];y=[]
    for task in train:
        if not task['features']: continue
        values=np.asarray(task['features'],dtype=float)
        rewards=np.asarray(task['outcomes'],dtype=float)
        x.extend(values-values.mean(axis=0)); y.extend(rewards-rewards.mean())
    x=np.asarray(x);y=np.asarray(y)
    scale=np.maximum(x.std(axis=0),.05)
    z=x/scale
    w=np.linalg.solve(z.T@z+np.eye(z.shape[1])*10,z.T@y)
    return scale,w


def main():
    prior=ROOT/'runs/seed-low-9000'
    model=initial_model(prior,read(prior/'protected_banks.json'),read(prior/'candidate_pools.json'))
    tasks=random_bank(SOURCE_SEED,COUNT,('ast_transition',),visible=2,hidden=22)
    started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(larger_pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    rows=[task_data(task,pools[task['id']],model) for task in tasks]
    groups=[[],[],[],[]]
    for task in rows:
        fold=int.from_bytes(hashlib.sha256(task['id'].encode()).digest()[:2],'little')%4
        groups[fold].append(task)
    fold_scores=[]; predictions={}
    for index in range(4):
        trainrows=[task for j,g in enumerate(groups) if j!=index for task in g]
        scale,w=fit(trainrows)
        for task in groups[index]:
            if not task['features']: continue
            x=np.asarray(task['features'],dtype=float)
            x=(x-x.mean(axis=0))/scale
            predictions[task['id']]=int(np.argmax(x@w))
        fold_scores.append({'fold':index,'n':len(groups[index]),'coefficients':w.tolist(),
                            'scale':scale.tolist()})
    def score(key):
        return sum(task['outcomes'][predictions[task['id']] if key=='learned' else task[key]]
                   for task in rows if task['features'])
    summary={'scope':'development only; four whole-task folds; source task labels visible during fit in other folds',
             'seed':SOURCE_SEED,'tasks':len(rows),'reachable':sum(r['reachable'] for r in rows),
             'baseline':sum(r['baseline'] for r in rows),'oracle_best_one':sum(r['oracle'] for r in rows),
             'random_one':score('random'),'entropy_one':score('entropy'),'learned_one':score('learned'),
             'sequential':{mode:{'one':sum(r['sequential'][mode][0] for r in rows if r['features']),
                                  'two':sum(r['sequential'][mode][1] for r in rows if r['features'])}
                           for mode in ('random','entropy','weighted_entropy','minimax')},
             'candidate_generation_parallel_wall_seconds':time.perf_counter()-started,
             'fold_sizes':[len(g) for g in groups]}
    write_json(ROOT/'analysis/probe-policy-development-v4.json',{'summary':summary,'fold_models':fold_scores,
                                                               'tasks':rows,'learned_selections':predictions})
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
