"""Chronological opened-panel check of retaining, retraining and blending feedback."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from combined_ranker_query_development import PANELS as FIRST_FOUR,source_rows as four_rows,feature_for
from cross_family_meta_improver_development import fit_method,values


FIFTH=ROOT/'runs/combined-ranker-query-transfer-20260918'
OUT=ROOT/'analysis/feedback-batch-history-development-20260918.json'
WEIGHTS=(0.,.25,.5,.75,1.)


def all_rows():
    prior=four_rows();assert len(prior)==2304
    assert json.loads((FIFTH/'audit.json').read_text())['passed']
    records=json.loads((FIFTH/'frozen_records.json').read_text())
    matrix=json.loads((FIFTH/'predicted_probe_outputs.json').read_text())
    outcomes=json.loads((FIFTH/'results.json').read_text())['tasks']
    final=[]
    for record,outcome in zip(records,outcomes):
        assert record['id']==outcome['id']
        final.append({'id':record['id'],'seed':record['seed'],
            'public_block':record['public_block'],
            'features':feature_for(record,matrix[record['id']],'e0'),
            'zero':outcome['zero']['e0'],'one':outcome['one']['e0'],
            'gain':outcome['one']['e0']-outcome['zero']['e0']})
    all_=[{'id':r['id'],'seed':r['seed'],'public_block':r['public_block'],
           **r['e0']} for r in prior]+final
    assert len(all_)==2880 and len({r['id'] for r in all_})==2880
    return all_


def score_panel(rows,prediction):
    seeds=sorted({r['seed'] for r in rows});assert len(seeds)==12
    lookup={r['id']:float(v) for r,v in zip(rows,prediction)}
    scores=[]
    for seed in seeds:
        group=[r for r in rows if r['seed']==seed]
        assert len(group)==48
        choice={r['id'] for r in sorted(group,key=lambda r:(lookup[r['id']],r['id']),
                                         reverse=True)[:8]}
        scores.append(sum(r['one'] if r['id'] in choice else r['zero'] for r in group))
    truth=np.asarray([r['gain'] for r in rows])
    return {'correct':sum(scores),'by_bank':scores,
            'mse':float(np.mean((np.asarray(prediction)-truth)**2))}


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows=all_rows();panels=[]
    for panel in range(2,5):
        target=rows[panel*576:(panel+1)*576]
        checkpoints={}
        for n in range(2,panel+1):
            model=fit_method(rows[:n*576],'interaction_100')
            checkpoints[str(n)]=values(model,target)
        early=checkpoints['2'];latest=checkpoints[str(panel)]
        scores={name:score_panel(target,pred) for name,pred in checkpoints.items()}
        blends={str(w):score_panel(target,(1-w)*early+w*latest)
                for w in WEIGHTS}
        panels.append({'panel_index':panel+1,'source_panel_count':panel,
                       'scores':scores,'blends':blends})
    output={'scope':'chronological opened-panel development; no fresh claim',
        'panels':panels,'source_tasks_total':len(rows),
        'source_panel_names':[p.name for p in FIRST_FOUR]+[FIFTH.name]}
    write_json(OUT,output)
    print(json.dumps({'scope':output['scope'],'panels':[
        {'panel':p['panel_index'],
         'checkpoints':{k:{'correct':v['correct'],'mse':v['mse']}
                        for k,v in p['scores'].items()},
         'blends':{k:{'correct':v['correct'],'mse':v['mse']}
                   for k,v in p['blends'].items()}}
        for p in panels]},indent=2))


if __name__=='__main__':main()
