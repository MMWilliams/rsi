"""Development-only query policy comparison across three reachable mechanisms."""
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,write_json
from seed_casebanks import random_bank
from seed_source_search import read
from active_probe_diagnostic import initial_model
from probe_policy_development import task_data,fit as ridge_fit
from probe_pairwise_development import fit as pairwise_fit
from mixed_probe_diagnostic import pool,bool_safe_structure
import seed_growth


SEED=902202
FAMILIES=('stack_transition','mutation_transition','self_edit_transition')
PER_FAMILY=64


def main():
    prior=ROOT/'runs/seed-low-9000'
    model=initial_model(prior,read(prior/'protected_banks.json'),
                        read(prior/'candidate_pools.json'))
    seed_growth.structure=bool_safe_structure
    tasks=random_bank(SEED,PER_FAMILY*len(FAMILIES),FAMILIES,visible=1,hidden=23)
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    rows=[]
    for task in tasks:
        row=task_data(task,pools[task['id']],model)
        row['family']=task['family']
        rows.append(row)
    folds=[[],[],[],[]]
    for row in rows:
        index=int.from_bytes(hashlib.sha256(row['id'].encode()).digest()[:2],'little')%4
        folds[index].append(row)
    decisions={'ridge':{},'pairwise':{}}
    for index in range(4):
        train=[row for k,fold in enumerate(folds) if k!=index for row in fold]
        models={'ridge':ridge_fit(train),'pairwise':pairwise_fit(train)}
        for row in folds[index]:
            if not row['features']:continue
            x=np.asarray(row['features'],dtype=float)
            for name,(scale,w) in models.items():
                decisions[name][row['id']]=int(np.argmax((x-x.mean(axis=0))/scale@w))
    def one(row,name):
        if not row['features']:return False
        if name in decisions:j=decisions[name][row['id']]
        elif name=='minimax':j=max(range(8),key=lambda k:(row['features'][k][2],-k))
        elif name=='weighted_entropy':j=max(range(8),key=lambda k:(row['features'][k][1],-k))
        elif name=='entropy':j=row['entropy']
        elif name=='random':j=row['random']
        return bool(row['outcomes'][j])
    names=('ridge','pairwise','minimax','weighted_entropy','entropy','random')
    def subset(group):
        return {'tasks':len(group),'reachable':sum(r['reachable'] for r in group),
                'baseline':sum(r['baseline'] for r in group),
                'oracle_best_one':sum(r['oracle'] for r in group),
                'one_query':{name:sum(one(r,name) for r in group) for name in names},
                'two_query':{mode:sum(r['sequential'][mode][1] for r in group)
                             for mode in ('random','entropy','weighted_entropy','minimax')}}
    summary={'scope':'development-only; four whole-task folds',
             'seed':SEED,'families':FAMILIES,'visible_examples':1,
             'candidate_cap_per_source':128,
             'generation_and_study_wall_seconds':time.perf_counter()-start,
             'overall':subset(rows),
             'by_family':{family:subset([r for r in rows if r['family']==family])
                          for family in FAMILIES}}
    write_json(ROOT/'analysis/mixed-probe-policy-development.json',
               {'summary':summary,'tasks':rows,'decisions':decisions})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
