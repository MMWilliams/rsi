"""Post hoc allocation headroom and value-prediction diagnostic."""
from __future__ import annotations

import json
from collections import Counter

import numpy as np

from rsi.common import ROOT, write_json
from ast_query_allocation_development import features,predict,allocate
from ast_query_allocation_transfer import DEST,model_data


OUT=ROOT/'analysis/ast-query-allocation-diagnostic.json'


def main():
    if OUT.exists():raise RuntimeError('diagnostic exists')
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_records.json').read_text(encoding='utf-8'))
    matrix=json.loads((DEST/'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    allocation=json.loads((DEST/'frozen_allocations.json').read_text(encoding='utf-8'))
    outcomes=json.loads((DEST/'results.json').read_text(encoding='utf-8'))['tasks']
    x=np.stack([features(t,{**r,'first_probe':{'top20_entropy':r['first_probe']}},matrix[t['id']])
                for t,r in zip(tasks,records)])
    p1,p2=predict(model_data(),x)
    truth=np.asarray([r['correct_by_calls'] for r in outcomes],dtype=int)
    u1=truth[:,1]-truth[:,0];u2=truth[:,2]-truth[:,1]
    by_id={r['id']:r for r in outcomes}
    hindsight=0;bank_rows=[]
    for seed in sorted({t['seed'] for t in tasks}):
        group=[r for r in outcomes if r['seed']==seed]
        gain1=np.asarray([r['correct_by_calls'][1]-r['correct_by_calls'][0] for r in group])
        gain2=np.asarray([r['correct_by_calls'][2]-r['correct_by_calls'][1] for r in group])
        best=allocate(gain1,gain2,8)
        best_score=sum(r['correct_by_calls'][a] for r,a in zip(group,best))
        hindsight+=best_score
        bank_rows.append({'seed':seed,'hindsight_best':best_score,
                          'learned':sum(by_id[key]['correct_by_calls'][a]
                                         for key,a in allocation[str(seed)]['learned'].items()),
                          'one_each':sum(r['correct_by_calls'][1] for r in group)})
    counts={name:dict(Counter(a for bank in allocation.values() for a in bank[name].values()))
            for name in next(iter(allocation.values()))}
    unreachable_queries={name:sum(a for bank in allocation.values()
                                  for key,a in bank[name].items() if not by_id[key]['reachable'])
                         for name in next(iter(allocation.values()))}
    summary={'scope':'post hoc inspected final labels; upper bound is not a policy',
             'tasks':len(tasks),'hindsight_best':hindsight,
             'actions':counts,'queries_on_unreachable_tasks':unreachable_queries,
             'marginal_1_positive':int(sum(u1>0)),'marginal_1_negative':int(sum(u1<0)),
             'marginal_2_positive':int(sum(u2>0)),'marginal_2_negative':int(sum(u2<0)),
             'value_correlation':{'first':float(np.corrcoef(p1,u1)[0,1]),
                                  'second':float(np.corrcoef(p2,u2)[0,1])},
             'by_bank':bank_rows}
    write_json(OUT,summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
