"""Development-only mechanism and candidate-source headroom diagnostic."""
from __future__ import annotations

import json
import time
import hashlib
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,write_json
from seed_casebanks import FAMILIES,random_bank
from seed_source_search import read
from stitch_ten import source_candidates
from active_probe_diagnostic import initial_model,task_study,MODES
import seed_growth
from rsi.invented_space import _split_atoms
from rsi.semantic_invention import parse_span


SOURCE_BY_FAMILY={
    'transform_transition':('v65','v67'),
    'ast_transition':('v67','v73'),
    'novel_operator_transition':('v67','v69'),
    'stack_transition':('v67','v70'),
    'mutation_transition':('v70','v72'),
    'self_edit_transition':('v70','v73'),
}
SEED=902201
PER_FAMILY=8
CAP=128
VISIBLE=1


@lru_cache(maxsize=30000)
def bool_safe_structure(program):
    """Same archived feature map, with bool numeric nodes cast before np.sign."""
    parsed=[]
    if program.startswith('Concat('):
        for atom in _split_atoms(program[7:-1]):
            span=parse_span(atom)
            if span is not None: parsed.extend(span)
    features=np.zeros(128,dtype=float)
    def add(token,value=1.):
        h=hashlib.sha256(token.encode()).digest()
        features[int.from_bytes(h[:4],'little')%len(features)]+=value*(1 if h[4]%2 else -1)
    def visit(node,path):
        if isinstance(node,dict):
            add(path+':keys:'+','.join(sorted(k for k in node if k not in ('complexity','macro_id'))))
            for key,value in sorted(node.items()):
                if key not in ('complexity','macro_id'): visit(value,path+'/'+key)
        elif isinstance(node,list):
            for i,item in enumerate(node): visit(item,path+'/'+str(i))
        else:
            add(path+'='+str(node))
            if isinstance(node,(int,float)):
                number=int(node) if isinstance(node,bool) else node
                add(path+':numeric',float(np.sign(number)*np.log1p(abs(number))/5))
    visit(parsed,'root')
    return tuple(np.clip(features/4,-3,3))


def pool(task):
    public={'id':task['id'],'visible':task['visible']}
    unique={};elapsed={}
    for arm in SOURCE_BY_FAMILY[task['family']]:
        start=time.perf_counter()
        for row in source_candidates(public,arm,{},CAP):
            unique.setdefault(row['program'],row)
        elapsed[arm]=time.perf_counter()-start
    return task['id'],list(unique.values()),elapsed


def main():
    prior=ROOT/'runs/seed-low-9000'
    model=initial_model(prior,read(prior/'protected_banks.json'),
                        read(prior/'candidate_pools.json'))
    seed_growth.structure=bool_safe_structure
    tasks=random_bank(SEED,PER_FAMILY*len(FAMILIES),FAMILIES,visible=VISIBLE,hidden=23)
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=6) as executor:
        generated=list(executor.map(pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    studied=[task_study(task,pools[task['id']],model) for task in tasks]
    by_family={}
    for family in FAMILIES:
        group=[r for r in studied if r['family']==family]
        by_family[family]={'tasks':len(group),
            'mean_candidates':sum(r['candidates'] for r in group)/len(group),
            'reachable':sum(r['reachable'] for r in group),
            'baseline':sum(r['baseline'] for r in group),
            'discriminating':sum(max(r['probe_classes'],default=0)>1 for r in group),
            'oracle_best_one':sum(r['best_one_probe'] for r in group),
            'methods':{name:[sum(r['modes'][name][k] for r in group) for k in (0,1)]
                       for name in MODES}}
    summary={'scope':'development-only mechanism/candidate diagnostic',
             'seed':SEED,'per_family':PER_FAMILY,'candidate_cap_per_source':CAP,
             'visible_examples':VISIBLE,
             'sources':SOURCE_BY_FAMILY,'generation_and_study_wall_seconds':time.perf_counter()-start,
             'families':by_family}
    write_json(ROOT/'analysis/mixed-probe-diagnostic-visible1.json',
               {'summary':summary,'tasks':studied,'generation_times':
                {key:elapsed for key,_,elapsed in generated}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
