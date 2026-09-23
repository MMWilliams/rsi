"""Opened-bank one-output sensor counterfactuals on a common mixed pool."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from ast_probe_sensor_development import MODES,choose_probe
from posterior_query_value_development import proxy


RUN=ROOT/'runs/focused-feedback-transfer-20260918'
OUT=ROOT/'analysis/probe-counterfactual-development-20260918.json'
EXTRA=('posterior_k20_tau0.25','posterior_k64_tau0.25')


def posterior_probe(record,matrix,k,tau):
    scores=np.asarray(record['scores'],float);order=record['order'][:k]
    spread=max(float(scores.std()),.05);top=float(scores[order[0]])
    weights=np.exp(np.clip((scores[order]-top)/(spread*tau),-50,0))
    options=[]
    for j in range(8):
        maxima={}
        for index,weight in zip(order,weights):
            answer=matrix[index][j]
            maxima[answer]=max(maxima.get(answer,0.),float(weight))
        value=(sum(maxima.values())-1.)/max(float(weights.sum()),1e-12)
        options.append((value,-j,j))
    return max(options)[2]


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    tasks=json.loads((RUN/'sealed_bank.json').read_text())
    base=json.loads((RUN/'base_pools.json').read_text())
    wide=json.loads((RUN/'ast_wide_pools.json').read_text())
    predicted=json.loads((RUN/'predicted_probe_outputs.json').read_text())
    records=json.loads((RUN/'frozen_records.json').read_text())
    outcomes=json.loads((RUN/'results.json').read_text())['tasks']
    choices=json.loads((RUN/'frozen_allocations.json').read_text())
    assert len(tasks)==len(records)==len(outcomes)==576
    detail=[];unique_evaluations=0
    for task,record,outcome in zip(tasks,records,outcomes):
        key=task['id'];assert key==record['id']==outcome['id']
        pool=wide.get(key,base[key]);matrix=predicted[key];order=record['order']
        selected=[]
        for j in range(8):
            matching={i for i in range(len(pool)) if matrix[i][j]==task['hidden'][j][1]}
            remaining=matching if matching else set(range(len(pool)))
            selected.append(next(i for i in order if i in remaining))
        labels={i:int(bool(evaluate_program(pool[i]['program'],task['hidden'][8:])))
                for i in set(selected)}
        unique_evaluations+=len(labels)
        correct=[labels[i] for i in selected]
        assert correct[record['first_probe']]==outcome['one']
        indices={mode:choose_probe(key,matrix,order,record['scores'],
                                   set(range(len(pool))),[],mode) for mode in MODES}
        indices['posterior_k20_tau0.25']=posterior_probe(record,matrix,20,.25)
        indices['posterior_k64_tau0.25']=posterior_probe(record,matrix,64,.25)
        assert indices['top20_entropy']==record['first_probe']
        detail.append({'id':key,'seed':task['seed'],'family':task['family'],
                       'zero':outcome['zero'],'probe_correct':correct,
                       'selected_indices':selected,'probe_choices':indices,
                       'oracle_best_probe':max(correct)})
    modes=(*MODES,*EXTRA)
    by_seed=defaultdict(list)
    for row in detail:by_seed[row['seed']].append(row)
    banks=[]
    for seed,group in sorted(by_seed.items()):
        ids=set(choices[str(seed)]['e0']);assert len(ids)==8
        correct={mode:sum(r['probe_correct'][r['probe_choices'][mode]]
                          if r['id'] in ids else r['zero'] for r in group) for mode in modes}
        correct['oracle_probe_same_calls']=sum(r['oracle_best_probe'] if r['id'] in ids
                                                else r['zero'] for r in group)
        correct['oracle_joint_eight']=sum(r['zero'] for r in group)+sum(sorted(
            (r['oracle_best_probe']-r['zero'] for r in group),reverse=True)[:8])
        banks.append({'seed':seed,'correct':correct})
    totals={mode:sum(b['correct'][mode] for b in banks) for mode in banks[0]['correct']}
    result={'scope':'opened-bank sensor development only','tasks':len(detail),
            'unique_selected_candidate_labels_checked':unique_evaluations,
            'e0_query_calls':96,'totals':totals,'banks':banks,'tasks_detail':detail,
            'limits':['All oracle answers and final labels were previously opened.',
                      'Oracle-best probe and joint actions use hidden outcomes and are not deployable.',
                      'The fixed E0 allocator was trained for the top20-entropy sensor.']}
    write_json(OUT,result)
    print(json.dumps({key:result[key] for key in ('tasks',
                      'unique_selected_candidate_labels_checked','totals')},indent=2))


if __name__=='__main__':main()
