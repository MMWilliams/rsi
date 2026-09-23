"""Development-only equal-label-budget source task acquisition tactics."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import representation
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_source import train
from mixed_evaluator_transfer import choose
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
TRANSFER=ROOT/'runs/mixed-evaluator-transfer-20260917'
OUT=ROOT/'analysis/improver-acquisition-development-v2.json'
TARGET_CACHE=ROOT/'analysis/improver-acquisition-target-development.json'
BUDGET=48


def probabilities(row,w):
    x=np.asarray(row['structural'],dtype=float)
    return 1/(1+np.exp(-np.clip(x@w,-30,30)))


def priority(row,w,method):
    p=probabilities(row,w)
    if method=='small_pool':return -float(row['n'])
    if method=='random':
        return int.from_bytes(hashlib.sha256(('acquire:'+row['id']).encode()).digest()[:8],
                              'little')/2**64
    if method=='uncertainty':return float(np.mean(4*p*(1-p)))
    if method=='low_confidence':return -float(np.max(p))
    if method=='low_margin':
        top=np.partition(p,-2)[-2:]
        return -float(top[-1]-top[-2])
    if method=='diversity':
        return float(np.mean(np.std(np.asarray(row['structural']),axis=0)))
    if method=='disagreement':
        top=choose(p,[{'program':z} for z in row['programs']])
        shortest=min(range(row['n']),key=lambda i:(len(row['programs'][i]),
                                                 row['programs'][i]))
        return float(top!=shortest)+float(np.mean(4*p*(1-p)))/10
    raise KeyError(method)


def select(source,initial,method):
    if method=='order':return source[:BUDGET]
    if method.startswith('iterative_'):
        tactic=method.removeprefix('iterative_')
        selected=[];remaining=list(source);current=initial
        for _ in range(3):
            batch=sorted(remaining,key=lambda r:(-priority(r,current,tactic),r['id']))[:16]
            selected+=batch
            chosen={r['id'] for r in batch}
            remaining=[r for r in remaining if r['id'] not in chosen]
            current=train(selected)
        return selected
    if method.startswith('two_stage_'):
        first=source[:BUDGET//2]
        interim=train(first)
        remaining=source[BUDGET//2:]
        tactic=method.removeprefix('two_stage_')
        second=sorted(remaining,key=lambda r:(-priority(r,interim,tactic),r['id']))[:BUDGET//2]
        return first+second
    return sorted(source,key=lambda r:(-priority(r,initial,method),r['id']))[:BUDGET]


def main():
    seed_growth.structure=bool_safe_structure
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    rows=source['tasks'];initial=np.asarray(source['initial_weights'])
    tasks=json.loads((TRANSFER/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((TRANSFER/'candidate_pools.json').read_text(encoding='utf-8'))
    if TARGET_CACHE.exists():
        target=json.loads(TARGET_CACHE.read_text(encoding='utf-8'))
    else:
        target=[]
        for task in tasks:
            cand=pools[task['id']]
            features=representation({'id':task['id'],'visible':task['visible']},cand)
            labels=[bool(evaluate_program(row['program'],task['final'])) for row in cand]
            target.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                           'n':len(cand),'programs':[r['program'] for r in cand],
                           'structural':features['structural'].tolist(),
                           'labels':labels})
        write_json(TARGET_CACHE,target)
    methods=('order','random','uncertainty','low_confidence','low_margin',
             'diversity','disagreement','two_stage_uncertainty',
             'two_stage_low_confidence','two_stage_low_margin',
             'iterative_uncertainty','iterative_low_confidence',
             'iterative_low_margin')
    results={}
    for method in methods:
        selected=select(rows,initial,method)
        w=train(selected)
        decisions={}
        for task in target:
            p=probabilities(task,w)
            i=choose(p,[{'program':z} for z in task['programs']])
            decisions[task['id']]=bool(task['labels'][i])
        results[method]={'selected_ids':[r['id'] for r in selected],
                         'source_family_counts':{f:sum(r['family']==f for r in selected)
                            for f in ('stack_transition','mutation_transition','self_edit_transition')},
                         'correct':sum(decisions.values()),
                         'by_bank':{str(seed):sum(decisions[t['id']] for t in target if t['seed']==seed)
                                    for seed in sorted({t['seed'] for t in target})},
                         'weights':w.tolist()}
    summary={'scope':'development only; target banks already inspected',
             'source_tasks':len(rows),'budget_tasks':BUDGET,
             'source_labels_per_method':{name:sum(r['n'] for r in rows
                 if r['id'] in set(results[name]['selected_ids'])) for name in methods},
             'target_tasks':len(target),'reachable':sum(any(t['labels']) for t in target),
             'methods':{name:{k:v for k,v in results[name].items() if k!='weights'}
                        for name in methods}}
    write_json(OUT,{'summary':summary,'policies':results})
    print(json.dumps({'scope':summary['scope'],'target_tasks':len(target),
                      'scores':{name:results[name]['correct'] for name in methods},
                      'source_labels':summary['source_labels_per_method']},indent=2))


if __name__=='__main__':main()
