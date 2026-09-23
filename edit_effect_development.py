"""Development-only realized effect table for one-task evaluator-training edits.

Each source episode uses 24 base feedback tasks, 48 candidate edit tasks, and
96 separate target tasks. The target examples were inspected in earlier work.
No result from this script is a fresh confirmation.
"""
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


OUT=ROOT/'analysis/edit-effect-development-v2.json'
SOURCE_A=ROOT/'analysis/mixed-evaluator-source.json'
TARGET_A=ROOT/'analysis/improver-acquisition-target-development.json'
RUN_B=ROOT/'runs/improver-acquisition-transfer-20260917'
BASE_TASKS=24
EDIT_TASKS=48
TARGET_TASKS=96


def load_a():
    source=json.loads(SOURCE_A.read_text(encoding='utf-8'))['tasks'][:BASE_TASKS+EDIT_TASKS]
    target=json.loads(TARGET_A.read_text(encoding='utf-8'))[:TARGET_TASKS]
    return source,target


def load_b():
    public=json.loads((RUN_B/'source_public_records.json').read_text(encoding='utf-8'))
    source_tasks=json.loads((RUN_B/'source_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((RUN_B/'candidate_pools.json').read_text(encoding='utf-8'))
    source=[]
    for task,row in zip(source_tasks,public):
        if len(source)==BASE_TASKS+EDIT_TASKS:break
        labels=[bool(evaluate_program(item['program'],task['hidden'][8:]))
                for item in pools[task['id']]]
        source.append({**row,'family':task['family'],'labels':labels})
    target_tasks=json.loads((RUN_B/'target_bank.json').read_text(encoding='utf-8'))
    target=[]
    for task in target_tasks[:TARGET_TASKS]:
        rows=pools[task['id']]
        features=representation({'id':task['id'],'visible':task['visible']},rows)
        target.append({'id':task['id'],'n':len(rows),
                       'programs':[r['program'] for r in rows],
                       'structural':features['structural'].tolist(),
                       'labels':[bool(evaluate_program(r['program'],task['hidden'][8:]))
                                 for r in rows]})
    return source,target


def public_features(row,base):
    x=np.asarray(row['structural'],dtype=float)
    p=1/(1+np.exp(-np.clip(x@base,-30,30)))
    top=np.partition(p,-2)[-2:] if len(p)>1 else np.r_[p,p]
    lens=np.asarray([len(z) for z in row['programs']],dtype=float)
    return [row['n']/256, x[0,137],float(np.mean(p)),float(np.max(p)),
            float(np.std(p)),float(np.mean(4*p*(1-p))),
            float(top[-1]-top[-2]),float(np.mean(np.std(x,axis=0))),
            float(np.mean(lens))/500,float(np.std(lens))/500]


def score(weights,target):
    accuracy=0;brier=0.;auc=0.;auc_tasks=0
    for task in target:
        if not task['n']:continue
        x=np.asarray(task['structural'],dtype=float)
        p=1/(1+np.exp(-np.clip(x@weights,-30,30)))
        i=choose(p,[{'program':z} for z in task['programs']])
        accuracy+=int(task['labels'][i])
        brier+=float(np.mean((p-np.asarray(task['labels'],dtype=float))**2))
        y=np.asarray(task['labels'],dtype=bool)
        if 0<sum(y)<len(y):
            order=np.argsort(p,kind='stable')
            sorted_p=p[order]
            ranks=np.empty(len(p),dtype=float)
            start=0
            while start<len(p):
                end=start+1
                while end<len(p) and sorted_p[end]==sorted_p[start]:end+=1
                ranks[order[start:end]]=(start+1+end)/2
                start=end
            positives=sum(y);negatives=len(y)-positives
            auc+=(sum(ranks[y])-positives*(positives+1)/2)/(positives*negatives)
            auc_tasks+=1
    return accuracy,brier/len(target),auc/max(1,auc_tasks),auc_tasks


def episode(name,source,target):
    assert len(source)==BASE_TASKS+EDIT_TASKS and len(target)==TARGET_TASKS
    base=train(source[:BASE_TASKS])
    baseline=score(base,target)
    effects=[]
    for row in source[BASE_TASKS:]:
        child=train([*source[:BASE_TASKS],row])
        actual=score(child,target)
        effects.append({'id':row['id'],'family':row['family'],'candidate_labels':row['n'],
                        'public_features':public_features(row,base),
                        'positive_fraction':sum(row['labels'])/row['n'],
                        'delta_correct':actual[0]-baseline[0],
                        'delta_brier':baseline[1]-actual[1],
                        'delta_auc':actual[2]-baseline[2]})
    return {'episode':name,'base_feedback_tasks':BASE_TASKS,'candidate_edits':len(effects),
            'target_tasks':len(target),'base_target_correct':baseline[0],
            'base_target_brier':baseline[1],'base_target_auc':baseline[2],
            'auc_evaluable_tasks':baseline[3],'effects':effects}


def fit_effect(rows,key):
    x=np.asarray([r['public_features'] for r in rows],dtype=float)
    y=np.asarray([r[key] for r in rows],dtype=float)
    scale=np.maximum(x.std(axis=0),.05)
    z=np.column_stack((x/scale,np.ones(len(x))))
    penalty=np.eye(z.shape[1])*4;penalty[-1,-1]=0
    w=np.linalg.solve(z.T@z+penalty,z.T@y)
    return scale,w


def transfer(train_rows,test_rows,key):
    scale,w=fit_effect(train_rows,key)
    x=np.asarray([r['public_features'] for r in test_rows],dtype=float)
    predicted=np.column_stack((x/scale,np.ones(len(x))))@w
    observed=np.asarray([r[key] for r in test_rows],dtype=float)
    ranked=sorted(range(len(test_rows)),key=lambda i:(-predicted[i],test_rows[i]['id']))
    best=ranked[:12]
    return {'target':key,'coefficient':w.tolist(),
            'prediction_correlation':float(np.corrcoef(predicted,observed)[0,1])
                if np.std(predicted)>0 and np.std(observed)>0 else None,
            'top12_observed_mean':float(np.mean(observed[best])),
            'all_observed_mean':float(np.mean(observed)),
            'top12_ids':[test_rows[i]['id'] for i in best],
            'top12_deltas':[float(observed[i]) for i in best]}


def main():
    seed_growth.structure=bool_safe_structure
    a=episode('A',*load_a())
    b=episode('B',*load_b())
    directions={}
    for key in ('delta_correct','delta_brier','delta_auc'):
        directions[key]={'A_to_B':transfer(a['effects'],b['effects'],key),
                         'B_to_A':transfer(b['effects'],a['effects'],key)}
    summary={'scope':'development only; exact one-task edit effects on inspected targets',
             'episodes':{row['episode']:{'base_target_correct':row['base_target_correct'],
                'positive_accuracy_edits':sum(e['delta_correct']>0 for e in row['effects']),
                'negative_accuracy_edits':sum(e['delta_correct']<0 for e in row['effects']),
                'mean_accuracy_effect':float(np.mean([e['delta_correct'] for e in row['effects']]))}
                for row in (a,b)},'effect_transfer':directions}
    write_json(OUT,{'summary':summary,'episodes':[a,b]})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
