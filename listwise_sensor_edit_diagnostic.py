"""Opened-bank factorial diagnostic for ranker, width and one external output."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from ast_probe_sensor_transfer import predicted_outputs
from dual_specialist_seed_evaluator import load_models
from wide_candidate_reranker_development import features
from task_listwise_top200_transfer import models_for, predict_listwise
from specialist_applicability_development import pair_features
from cross_family_meta_improver_transfer import interval


SOURCE=ROOT/'runs/task-listwise-top200-replication-20260918'
OUT=ROOT/'analysis/listwise-sensor-edit-diagnostic-20260918.json'


def matrix_for(tasks,wide,records):
    public=[]
    for task,rec in zip(tasks,records):
        old=rec['orders']['old'][:200]
        pool=wide[task['id']]
        public.append(({'id':task['id'],
                        'probe_inputs':[x for x,_ in task['hidden'][:8]]},
                       [pool[i] for i in old]))
    with ProcessPoolExecutor(max_workers=8) as executor:
        return dict(executor.map(predicted_outputs,public))


def main():
    if OUT.exists():raise RuntimeError('diagnostic already exists')
    assert json.loads((SOURCE/'audit.json').read_text())['passed']
    tasks=json.loads((SOURCE/'sealed_bank.json').read_text())
    wide=json.loads((SOURCE/'ast_wide_pools.json').read_text())
    records=json.loads((SOURCE/'frozen_records.json').read_text())
    choices=json.loads((SOURCE/'public_choices.json').read_text())
    prior=json.loads((SOURCE/'results.json').read_text())['tasks']
    matrix=matrix_for(tasks,wide,records)
    specialists=load_models()
    listwise=models_for()['later_listwise']
    rows=[];cells=0
    for task,rec,old_choice,saved in zip(tasks,records,choices,prior):
        key=task['id'];pool=wide[key]
        indices=rec['orders']['old'][:200]
        n=len(indices)
        x=features(task,pool,rec,n)
        pf=specialists['familiar'].predict_proba(x)[:,1]
        ps=specialists['shifted'].predict_proba(x)[:,1]
        scores=np.asarray(rec['old_scores'],float)
        std=max(float(scores.std()),.05)
        meta=np.stack((pf,ps,np.maximum(pf,ps),np.abs(pf-ps),pf*ps,
            (scores[indices]-scores[indices[0]])/std,
            np.arange(n)/100.),axis=1).astype(np.float32)
        logit=predict_listwise(listwise,np.c_[x,meta].astype(np.float32))
        probe=rec['probe'];truth=rec['probe_output']
        assert truth==task['hidden'][probe][1]
        outputs=matrix[key]
        assert len(outputs)==n
        cells+=n*8
        survivors=[i for i in range(n) if outputs[i][probe]==truth]
        if not survivors:survivors=list(range(n))
        best=lambda p,ids:max(ids,key=lambda i:(float(p[i]),-i))
        def dual(ids):
            f=best(pf,ids);s=best(ps,ids)
            return s if ps[s]>pf[f] else f
        select={'dual0':dual(list(range(n))),
                'listwise0':best(logit,list(range(n))),
                'dual1':dual(survivors),
                'listwise1':best(logit,survivors)}
        assert indices[select['dual0']]==old_choice['choices']['dual200']
        assert indices[select['listwise0']]==old_choice['choices']['later_listwise']
        labels={name:int(bool(evaluate_program(pool[indices[i]]['program'],
                                                task['hidden'][8:])))
                for name,i in select.items()}
        assert labels['dual0']==saved['labels']['dual200']
        assert labels['listwise0']==saved['labels']['later_listwise']
        top_logit=sorted((float(v) for v in logit),reverse=True)
        f=best(pf,list(range(n)));s=best(ps,list(range(n)))
        partitions=Counter(str(outputs[i][probe]) for i in range(n))
        probs=np.asarray(list(partitions.values()),float)/n
        public=pair_features(task['visible'][0])+[
            n/200.,len(pool)/512.,std,
            float(pf[f]),float(ps[s]),float(ps[s]-pf[f]),
            float(logit.max()),float(logit.std()),
            float(top_logit[0]-top_logit[1]) if n>1 else 0.,
            float(select['dual0']==select['listwise0']),
            float(-(probs*np.log(np.maximum(probs,1e-12))).sum()),
            len(partitions)/n]
        rows.append({'id':key,'seed':task['seed'],
                     'domain':saved['domain'],'public_features':public,
                     'probe':probe,'survivors':len(survivors),
                     'labels':labels,
                     'dual_query_effect':labels['dual1']-labels['dual0'],
                     'listwise_query_effect':labels['listwise1']-labels['listwise0']})
    by_bank=defaultdict(list)
    for row in rows:by_bank[row['seed']].append(row)
    banks=[]
    for seed,group in sorted(by_bank.items()):
        banks.append({'seed':seed,**{name:sum(r['labels'][name] for r in group)
                                    for name in ('dual0','dual1','listwise0','listwise1')}})
    totals={name:sum(b[name] for b in banks) for name in
            ('dual0','dual1','listwise0','listwise1')}
    effects={}
    for key in ('dual_query_effect','listwise_query_effect'):
        d=[sum(r[key] for r in group) for group in by_bank.values()]
        effects[key]={'net':sum(d),
            'positive_tasks':sum(r[key]>0 for r in rows),
            'negative_tasks':sum(r[key]<0 for r in rows),
            'positive_banks':sum(v>0 for v in d),
            'negative_banks':sum(v<0 for v in d),
            'interval':interval(d)}
    result={'scope':'opened post-audit diagnostic, not fresh promotion',
            'tasks':len(rows),'predicted_output_cells':cells,
            'external_output_calls_if_all_queried':len(rows),
            'totals':totals,'effects':effects,'banks':banks,'rows':rows}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('banks','rows')},
                     indent=2))


if __name__=='__main__':main()
