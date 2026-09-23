"""Development-only structural evaluator training on three sparse task families."""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,write_json,digest
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from seed_growth import representation,logistic
from active_probe_diagnostic import initial_model
from mixed_probe_diagnostic import pool,bool_safe_structure
import seed_growth


SEED=902202
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
COUNT=192
OUT=ROOT/'analysis/mixed-evaluator-source.json'


def choose(scores,rows):
    return max(range(len(rows)),key=lambda i:(float(scores[i]),
               -len(rows[i]['program']),rows[i]['program'])) if rows else None


def train(rows):
    x=np.concatenate([np.asarray(r['structural'],dtype=float) for r in rows if r['n']])
    y=np.concatenate([np.asarray(r['labels'],dtype=float) for r in rows if r['n']])
    mass=np.concatenate([np.full(r['n'],1/r['n']) for r in rows if r['n']])
    return logistic(x,y,mass)


def main():
    seed_growth.structure=bool_safe_structure
    tasks=random_bank(SEED,COUNT,FAMILIES,visible=1,hidden=23)
    prior=ROOT/'runs/seed-low-9000'
    initial=initial_model(prior,read(prior/'protected_banks.json'),
                          read(prior/'candidate_pools.json'))
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[]
    for task in tasks:
        rows=pools[task['id']]
        public={'id':task['id'],'visible':task['visible']}
        feats=representation(public,rows)
        labels=[bool(evaluate_program(r['program'],task['hidden'][8:])) for r in rows]
        records.append({'id':task['id'],'family':task['family'],'n':len(rows),
                        'programs':[r['program'] for r in rows],
                        'structural':feats['structural'].tolist(),
                        'labels':labels,'pool_sha256':digest(rows)})
    folds=[[],[],[],[]]
    for row in records:
        fold=int.from_bytes(hashlib.sha256(row['id'].encode()).digest()[:2],'little')%4
        folds[fold].append(row)
    selected={}
    for fold in range(4):
        model=train([r for k,g in enumerate(folds) if k!=fold for r in g])
        for row in folds[fold]:
            x=np.asarray(row['structural'],dtype=float)
            if not row['n']:continue
            score=1/(1+np.exp(-np.clip(x@model,-30,30)))
            index=choose(score,[{'program':p} for p in row['programs']])
            selected[row['id']]=index
    full=train(records)
    old=initial['structural']
    def aggregate(group):
        return {'n':len(group),'reachable':sum(any(r['labels']) for r in group),
                'initial_structural':sum(r['labels'][choose(
                    1/(1+np.exp(-np.clip(np.asarray(r['structural'])@old,-30,30))),
                    [{'program':p} for p in r['programs']])]
                    for r in group if r['n']),
                'crossfit_new_structural':sum(r['labels'][selected[r['id']]]
                    for r in group if r['n'])}
    summary={'scope':'development only; four whole-task folds; candidate labels from 15 final examples',
             'seed':SEED,'families':FAMILIES,'visible_examples':1,
             'candidate_cap_per_source':128,
             'candidate_generation_and_label_wall_seconds':time.perf_counter()-start,
             'candidate_count':sum(r['n'] for r in records),
             'overall':aggregate(records),
             'by_family':{family:aggregate([r for r in records if r['family']==family])
                          for family in FAMILIES}}
    write_json(OUT,{'summary':summary,'initial_weights':old.tolist(),
                    'full_weights':full.tolist(),'tasks':records,
                    'crossfit_selection':selected})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
