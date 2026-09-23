"""Development-only improver comparison with exactly matched candidate labels."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_evaluator_source import train
from mixed_evaluator_transfer import choose
from improver_acquisition_development import priority,probabilities


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
TARGET=ROOT/'analysis/improver-acquisition-target-development.json'
OUT=ROOT/'analysis/improver-label-budget-development.json'
BUDGET=7000
METHODS=('order','random','small_pool','low_confidence','balanced_low_confidence',
         'uncertainty','low_margin',
         'iterative_low_confidence','iterative_uncertainty')


def partial(row,count):
    if count==row['n']:return row
    copy=dict(row)
    copy['n']=count
    for key in ('programs','structural','labels'):
        copy[key]=row[key][:count]
    return copy


def order_by(rows,w,method):
    if method=='order':return list(rows)
    return sorted(rows,key=lambda r:(-priority(r,w,method),r['id']))


def acquire(rows,initial,method):
    if method=='balanced_low_confidence':
        groups={}
        for row in rows:
            block=round(row['structural'][0][137]*4096)
            groups.setdefault(block,[]).append(row)
        assert len(groups)==3
        selected=[]
        for block,band in zip(sorted(groups),(BUDGET//3,BUDGET//3,BUDGET-2*(BUDGET//3))):
            used=0
            for row in order_by(groups[block],initial,'low_confidence'):
                if used==band:break
                count=min(row['n'],band-used)
                selected.append(partial(row,count));used+=count
            assert used==band
        return selected,train(selected)
    if method.startswith('iterative_'):
        tactic=method.removeprefix('iterative_')
        bands=(BUDGET//3,BUDGET//3,BUDGET-2*(BUDGET//3))
    else:
        tactic=method;bands=(BUDGET,)
    remaining=list(rows);chosen=[];state=initial
    for band in bands:
        picked=0
        for row in order_by(remaining,state,tactic):
            room=band-picked
            if not room:break
            count=min(row['n'],room)
            chosen.append(partial(row,count))
            picked+=count
            remaining=[r for r in remaining if r['id']!=row['id']]
        assert picked==band
        state=train(chosen)
    assert sum(r['n'] for r in chosen)==BUDGET
    return chosen,state


def main():
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    target=json.loads(TARGET.read_text(encoding='utf-8'))
    rows=source['tasks'];initial=np.asarray(source['initial_weights'])
    results={}
    for method in METHODS:
        chosen,w=acquire(rows,initial,method)
        decision={}
        for task in target:
            scores=probabilities(task,w)
            index=choose(scores,[{'program':p} for p in task['programs']])
            decision[task['id']]=bool(task['labels'][index])
        results[method]={'correct':sum(decision.values()),
                         'source_tasks':len(chosen),'partial_tasks':sum(r['n']<
                             next(s['n'] for s in rows if s['id']==r['id']) for r in chosen),
                         'selected_ids':[r['id'] for r in chosen],
                         'by_bank':{str(seed):sum(decision[t['id']] for t in target
                            if t['seed']==seed) for seed in sorted({t['seed'] for t in target})},
                         'weights':w.tolist()}
    summary={'scope':'development only; source and target labels previously inspected',
             'source_tasks_available':len(rows),'candidate_label_budget_per_method':BUDGET,
             'target_tasks':len(target),'results':{m:{k:v for k,v in results[m].items()
                                  if k!='weights'} for m in METHODS}}
    write_json(OUT,{'summary':summary,'policies':results})
    print(json.dumps({m:{'correct':results[m]['correct'],
                         'source_tasks':results[m]['source_tasks'],
                         'partial_tasks':results[m]['partial_tasks']}
                      for m in METHODS},indent=2))


if __name__=='__main__':main()
