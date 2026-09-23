"""Public candidate-consensus features for inspected query-gain development."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter

import numpy as np

from rsi.common import ROOT,write_json
from cross_family_meta_improver_transfer import sha

RUNS={'meta':ROOT/'runs/cross-family-meta-improver-transfer-20260918',
      'stable':ROOT/'runs/stable-cross-family-improver-transfer-20260918'}
FEATURES=('first_probe_position','top_same_5','top_same_10','top_same_20',
          'top_same_50','top_weighted_support_20','top_full_signature_20',
          'rival_score_gap','score_gap_5','score_gap_10',
          'mean_top_support_8','min_top_support_8','max_top_support_8',
          'source_same_20','source_diversity_20',
          'top_complexity_relative','complexity_variation_20')


def row_features(record,pool,matrix):
    order=record['order'];scores=np.asarray(record['scores'],float)
    top=order[0];first=record['first_probe'];top20=order[:20]
    std=max(float(scores.std()),.05)
    wanted=matrix[top][first]
    same=lambda n:sum(matrix[i][first]==wanted for i in order[:min(n,len(order))])/min(n,len(order))
    local=np.asarray([scores[i] for i in top20],float)
    weights=np.exp(np.clip((local-local.max())/std,-30,0));weights/=weights.sum()
    weighted=sum(float(w) for i,w in zip(top20,weights) if matrix[i][first]==wanted)
    signature=tuple(matrix[top]);signature_support=sum(tuple(matrix[i])==signature for i in top20)/len(top20)
    rival=next((i for i in order if matrix[i][first]!=wanted),None)
    rival_gap=(scores[top]-scores[rival])/std if rival is not None else 10.
    positions=[sum(matrix[i][j]==matrix[top][j] for i in top20)/len(top20) for j in range(8)]
    sources=[pool[i].get('source','') for i in top20]
    complexities=np.asarray([float(pool[i].get('complexity',len(pool[i]['program'])))
                             for i in top20])
    source_counts=Counter(sources)
    vals=(first/7,same(5),same(10),same(20),same(50),weighted,
          signature_support,rival_gap,
          (scores[top]-scores[order[min(4,len(order)-1)]])/std,
          (scores[top]-scores[order[min(9,len(order)-1)]])/std,
          float(np.mean(positions)),float(min(positions)),float(max(positions)),
          source_counts[sources[0]]/len(top20),len(source_counts)/max(1,len(top20)),
          float(complexities[0]/max(complexities.mean(),1)),
          float(complexities.std()/max(complexities.mean(),1)))
    assert len(vals)==len(FEATURES) and all(math.isfinite(float(v)) for v in vals)
    return [float(v) for v in vals]


def extract(name,stage):
    directory=RUNS[name]/stage
    out=ROOT/f'analysis/rich-query-features-{name}-{stage}-20260918.json'
    if out.exists():raise RuntimeError(f'{out} exists')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    matrix=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert len(tasks)==len(records)==len(outcomes)==288
    rows=[]
    for task,record,outcome in zip(tasks,records,outcomes):
        key=task['id'];pool=wide.get(key,base[key])
        assert key==record['id']==outcome['id']
        rows.append({'id':key,'seed':record['seed'],'public_block':record['public_block'],
                     'family':record['family'],'base_features':record['features'],
                     'rich_features':row_features(record,pool,matrix[key]),
                     'zero':int(outcome['zero']),'one':int(outcome['one']),
                     'gain':int(outcome['one'])-int(outcome['zero'])})
    result={'scope':'opened-bank public candidate and predicted-output features',
            'run':name,'stage':stage,'feature_names':FEATURES,
            'source_sha256':{n:sha(directory/n) for n in
                             ('sealed_bank.json','base_pools.json','ast_wide_pools.json',
                              'predicted_probe_outputs.json','frozen_records.json','results.json')},
            'rows':rows}
    write_json(out,result)
    print(json.dumps({'run':name,'stage':stage,'rows':len(rows),'features':len(FEATURES)},indent=2))


if __name__=='__main__':extract(sys.argv[1],sys.argv[2])
