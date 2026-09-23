"""Frozen one-query evaluator transfer. Run prepare, then score, then audit."""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from seed_growth import representation, predict
from active_probe_diagnostic import initial_model, program_output, choose_probe
from active_probe_sparse_pilot import larger_pool
from probe_pairwise_development import fit as pairwise_fit
from probe_policy_development import fit as ridge_fit


SOURCE=ROOT/'analysis/probe-policy-development-v4.json'
DEST=ROOT/'runs/active-evaluator-transfer-20260917'
SEEDS=tuple(range(902117,902123))
PER_BANK=64


def unlabeled(task, rows, model):
    """Only public examples and probe INPUTS enter this function."""
    public={'id':task['id'],'visible':task['visible']}
    if not rows:
        return {'id':task['id'],'n':0,'choices':{},'candidate_digest':digest(rows),
                'predicted_probe_outputs':[],'ranking':[],'scores':[]}
    rec={'id':task['id'],'public':public,'rows':rows,
         'features':representation(public,rows)}
    scores=np.asarray(predict(model,rec)['ensemble'],dtype=float)
    order=sorted(range(len(rows)),key=lambda i:(-scores[i],len(rows[i]['program']),rows[i]['program']))
    inputs=task['probe_inputs']
    outputs=[[program_output(row['program'],inp) for inp in inputs] for row in rows]
    n=len(rows); raw=scores
    weights=np.exp((raw-raw.max())/.1);weights/=weights.sum()
    public_chars={c for text,_ in task['visible'] for c in text}
    features=[]
    for j,inp in enumerate(inputs):
        groups=defaultdict(list)
        for i in range(n): groups[outputs[i][j]].append(i)
        proportions=[len(v)/n for v in groups.values()]
        mass=[sum(weights[v]) for v in groups.values()]
        expected_max=sum(max(weights[i] for i in indices) for indices in groups.values())
        entropy=-sum(p*math.log(p) for p in proportions)
        wentropy=-sum(p*math.log(p) for p in mass)
        topclass=groups[outputs[order[0]][j]]
        values=[outputs[i][j] for i in range(n)]
        features.append([entropy,wentropy,1-max(proportions),1-max(mass),
                         len(groups)/max(1,n),1-len(topclass)/n,1-sum(weights[topclass]),
                         sum(v is None for v in values)/n,
                         float(np.std([len(v) if v is not None else 0 for v in values]))/10,
                         float(np.mean([len(v) if v is not None else 0 for v in values]))/10,
                         expected_max,1-sum(p*p for p in mass),
                         float(outputs[order[0]][j]!=outputs[order[1]][j]) if n>1 else 0.,
                         len(set(inp)-public_chars)/max(1,len(set(inp))),len(inp)/10])
    return {'id':task['id'],'n':n,'candidate_digest':digest(rows),
            'predicted_probe_outputs':outputs,'ranking':order,'scores':scores.tolist(),
            'features':features}


def freeze_choices(record,models):
    if not record['n']: return record
    x=np.asarray(record['features'],dtype=float)
    choices={}
    for name,(scale,w) in models.items():
        choices[name]=int(np.argmax((x-x.mean(axis=0))/scale@w))
    choices['minimax']=max(range(8),key=lambda j:(x[j,2],-j))
    choices['entropy']=max(range(8),key=lambda j:(x[j,0],-j))
    choices['random']=min(range(8),key=lambda j:hashlib.sha256(
        (record['id']+':random:'+str(j)).encode()).digest())
    choices['weighted_first']=choose_probe(record['id'],record['predicted_probe_outputs'],
                                            list(range(record['n'])),[],record['scores'],
                                            'weighted_entropy')
    record['choices']=choices
    del record['features']
    return record


def prepare():
    if DEST.exists(): raise RuntimeError('transfer directory already exists')
    DEST.mkdir(parents=True)
    source_bytes=SOURCE.read_bytes()
    source=json.loads(source_bytes)['tasks']
    models={'pairwise':pairwise_fit(source),'ridge':ridge_fit(source)}
    prior=ROOT/'runs/seed-low-9000'
    model=initial_model(prior,read(prior/'protected_banks.json'),
                        read(prior/'candidate_pools.json'))
    tasks=[]
    for seed in SEEDS:
        for task in random_bank(seed,PER_BANK,('ast_transition',),visible=2,hidden=22):
            tasks.append({'id':task['id'],'seed':seed,'visible':task['visible'],
                          'probe_inputs':[p[0] for p in task['hidden'][:8]],
                          'probe_outputs':[p[1] for p in task['hidden'][:8]],
                          'final':task['hidden'][8:]})
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(larger_pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[freeze_choices(unlabeled(task,pools[task['id']],model),models)
             for task in tasks]
    manifest={'protocol':'EXPERIMENT-active-evaluator-transfer.md',
              'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
              'runner_sha256':hashlib.sha256(
                  (ROOT/'active_evaluator_transfer.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,'candidate_generation_wall_seconds':
              time.perf_counter()-start,'initial_ranker':'seed-low-9000 I0',
              'models':{name:{'scale':m[0].tolist(),'weights':m[1].tolist()}
                        for name,m in models.items()}}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_decisions.json',records)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),'candidate_generation_wall_seconds':
                      manifest['candidate_generation_wall_seconds'],'directory':str(DEST)},indent=2))


def score_one(task,record,rows):
    assert record['candidate_digest']==digest(rows)
    if not rows:
        return {'id':task['id'],'seed':task['seed'],'reachable':False,
                'correct':{name:False for name in ('baseline','pairwise','ridge','minimax',
                                                   'entropy','random','weighted_two')}}
    outputs=record['predicted_probe_outputs'];order=record['ranking']
    scores=record['scores'];truth=task['probe_outputs']
    correct=[evaluate_program(row['program'],task['final']) for row in rows]
    result={'baseline':bool(correct[order[0]])}
    for name in ('pairwise','ridge','minimax','entropy','random'):
        j=record['choices'][name]
        remaining={i for i in range(len(rows)) if outputs[i][j]==truth[j]}
        selection=next((i for i in order if i in remaining),order[0])
        result[name]=bool(correct[selection])
    j=record['choices']['weighted_first']
    remaining=[i for i in range(len(rows)) if outputs[i][j]==truth[j]]
    if not remaining: remaining=list(range(len(rows)))
    second=choose_probe(task['id'],outputs,remaining,[j],scores,'weighted_entropy')
    matched={i for i in remaining if outputs[i][second]==truth[second]}
    if matched: remaining=list(matched)
    selection=next((i for i in order if i in set(remaining)),order[0])
    result['weighted_two']=bool(correct[selection])
    return {'id':task['id'],'seed':task['seed'],'reachable':any(correct),
            'candidates':len(rows),'correct':result,
            'query_choices':{**record['choices'],'weighted_second':second}}


def score():
    if (DEST/'results.json').exists(): raise RuntimeError('results already exist')
    tasks=read(DEST/'sealed_bank.json'); pools=read(DEST/'candidate_pools.json')
    records=read(DEST/'frozen_decisions.json'); manifest=read(DEST/'manifest.json')
    assert len(tasks)==len(records)==PER_BANK*len(SEEDS)
    assert tuple(manifest['seeds'])==SEEDS
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==manifest['source_sha256']
    assert hashlib.sha256((ROOT/'active_evaluator_transfer.py').read_bytes()).hexdigest()==manifest['runner_sha256']
    rows=[score_one(t,r,pools[t['id']]) for t,r in zip(tasks,records)]
    methods=list(rows[0]['correct'])
    by_bank=[]
    for seed in SEEDS:
        group=[row for row in rows if row['seed']==seed]
        by_bank.append({'seed':seed,'reachable':sum(r['reachable'] for r in group),
                        **{name:sum(r['correct'][name] for r in group) for name in methods}})
    summary={'scope':'fresh AST confirmation; decisions frozen before outputs opened',
             'tasks':len(rows),'reachable':sum(r['reachable'] for r in rows),
             'oracle_output_queries':{name:len(rows)*(2 if name=='weighted_two' else
                                    0 if name=='baseline' else 1) for name in methods},
             'results':{name:sum(r['correct'][name] for r in rows) for name in methods},
             'pairwise_minus_minimax_by_bank':[r['pairwise']-r['minimax'] for r in by_bank],
             'pairwise_only':sum(r['correct']['pairwise'] and not r['correct']['minimax'] for r in rows),
             'minimax_only':sum(r['correct']['minimax'] and not r['correct']['pairwise'] for r in rows),
             'by_bank':by_bank}
    write_json(DEST/'results.json',{'summary':summary,'tasks':rows})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score}[sys.argv[1]]()
