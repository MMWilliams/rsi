"""Development-only cross-bank transfer of a soft top-candidate margin.

The smooth metric uses a fixed 0.1 probability margin temperature. Both
episodes and target labels were inspected earlier; this is not confirmation.
"""
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_source import train
from mixed_evaluator_transfer import choose
from edit_effect_development import load_a,load_b,BASE_TASKS,EDIT_TASKS
import seed_growth


OUT=ROOT/'analysis/top-margin-edit-development.json'
TEMPERATURE=.1


def score(w,tasks):
    correct=0;soft=0.
    for task in tasks:
        if not task['n']:continue
        x=np.asarray(task['structural'],dtype=float)
        p=1/(1+np.exp(-np.clip(x@w,-30,30)))
        y=np.asarray(task['labels'],dtype=bool)
        index=choose(p,[{'program':program} for program in task['programs']])
        correct+=bool(y[index])
        if not any(y):value=0.
        elif all(y):value=1.
        else:
            margin=float(np.max(p[y])-np.max(p[~y]))
            value=float(1/(1+np.exp(-np.clip(margin/TEMPERATURE,-30,30))))
        soft+=value
    return correct,soft/len(tasks)


def episode(name,source,current,other):
    base_rows=source[:BASE_TASKS]
    base=train(base_rows)
    current_base=score(base,current)
    other_base=score(base,other)
    edits=[]
    for task in source[BASE_TASKS:BASE_TASKS+EDIT_TASKS]:
        child=train([*base_rows,task])
        on_current=score(child,current)
        on_other=score(child,other)
        edits.append({'id':task['id'],'candidate_labels':task['n'],
                      'current_delta_correct':on_current[0]-current_base[0],
                      'other_delta_correct':on_other[0]-other_base[0],
                      'current_delta_soft':on_current[1]-current_base[1],
                      'other_delta_soft':on_other[1]-other_base[1]})
    result={}
    for prior_key,current_key in (
        ('other_delta_correct','current_delta_correct'),
        ('other_delta_soft','current_delta_soft'),
        ('other_delta_soft','current_delta_correct')):
        prior=np.asarray([r[prior_key] for r in edits],dtype=float)
        observed=np.asarray([r[current_key] for r in edits],dtype=float)
        order=sorted(range(len(edits)),key=lambda i:(-prior[i],edits[i]['id']))
        result[prior_key+'__to__'+current_key]={
            'correlation':float(np.corrcoef(prior,observed)[0,1])
                if np.std(prior)>0 and np.std(observed)>0 else None,
            'top12_current_mean':float(np.mean(observed[order[:12]])),
            'all_current_mean':float(np.mean(observed)),
            'positive_prior_count':int(sum(prior>0)),
            'positive_prior_current_mean':float(np.mean(observed[prior>0]))
                if any(prior>0) else None}
    return {'episode':name,'base_current':current_base,'base_other':other_base,
            'effects':edits,'transfer':result}


def main():
    seed_growth.structure=bool_safe_structure
    source_a,target_a=load_a()
    source_b,target_b=load_b()
    a=episode('A',source_a,target_a,target_b)
    b=episode('B',source_b,target_b,target_a)
    summary={'scope':'development only; fixed soft-margin temperature',
             'temperature':TEMPERATURE,'A':a['transfer'],'B':b['transfer']}
    write_json(OUT,{'summary':summary,'episodes':[a,b]})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
