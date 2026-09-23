"""Development-only inherited edit-effect policy at matched candidate labels."""
import hashlib
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_evaluator_source import train
from mixed_probe_diagnostic import bool_safe_structure
import seed_growth
from edit_effect_development import (
    load_a,load_b,score,public_features,fit_effect,BASE_TASKS,EDIT_TASKS)


EFFECTS=ROOT/'analysis/edit-effect-development.json'
OUT=ROOT/'analysis/effect-policy-development.json'
BUDGET=7000
METHODS=('order','random','low_confidence','inherited_accuracy',
         'inherited_brier','scrambled_brier')


def reduced(row,count):
    if count==row['n']:return row
    copy=dict(row);copy['n']=count
    for key in ('programs','structural','labels'):copy[key]=row[key][:count]
    return copy


def pick_order(rows,base,method,evidence):
    if method=='order':return list(rows)
    if method=='random':
        return sorted(rows,key=lambda r:(
            -int.from_bytes(hashlib.sha256(('effect-random:'+r['id']).encode()).digest()[:8],
                            'little'),r['id']))
    features=np.asarray([public_features(r,base) for r in rows],dtype=float)
    if method=='low_confidence':
        values=-features[:,3]
    else:
        key='delta_correct' if method=='inherited_accuracy' else 'delta_brier'
        scale,w=fit_effect(evidence,key)
        if method=='scrambled_brier':
            rng=np.random.default_rng(902401)
            w=w.copy();w[:-1]=rng.permutation(w[:-1])
        values=np.column_stack((features/scale,np.ones(len(features))))@w
    return [r for _,r in sorted(zip(values,rows),key=lambda item:(-item[0],item[1]['id']))]


def run(name,source,target,evidence):
    base_rows=source[:BASE_TASKS]
    base=train(base_rows)
    candidates=source[BASE_TASKS:BASE_TASKS+EDIT_TASKS]
    assert len(candidates)==EDIT_TASKS
    results={}
    for method in METHODS:
        chosen=list(base_rows)
        spent=sum(r['n'] for r in chosen)
        added=[]
        for row in pick_order(candidates,base,method,evidence):
            if spent>=BUDGET:break
            count=min(row['n'],BUDGET-spent)
            chosen.append(reduced(row,count))
            spent+=count
            added.append({'id':row['id'],'labels':count})
        assert spent==BUDGET
        child=train(chosen)
        accuracy,brier=score(child,target)
        results[method]={'correct':accuracy,'brier':brier,
                         'base_labels':sum(r['n'] for r in base_rows),
                         'new_labels':sum(r['labels'] for r in added),
                         'new_tasks':len(added),'added':added}
    return {'episode':name,'results':results}


def main():
    seed_growth.structure=bool_safe_structure
    effects=json.loads(EFFECTS.read_text(encoding='utf-8'))['episodes']
    source_a,target_a=load_a()
    source_b,target_b=load_b()
    a=run('A',source_a,target_a,effects[1]['effects'])
    b=run('B',source_b,target_b,effects[0]['effects'])
    summary={'scope':'development only; source and target data previously inspected',
             'budget_candidate_labels':BUDGET,
             'scores':{method:{'A':a['results'][method]['correct'],
                               'B':b['results'][method]['correct'],
                               'total':a['results'][method]['correct']+
                                       b['results'][method]['correct'],
                               'brier_A':a['results'][method]['brier'],
                               'brier_B':b['results'][method]['brier']}
                       for method in METHODS}}
    write_json(OUT,{'summary':summary,'episodes':[a,b]})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
