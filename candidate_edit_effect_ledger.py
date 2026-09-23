"""Typed task-level effects for the audited candidate-reranker edit catalog."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from rsi.common import ROOT,write_json


RUN=ROOT/'runs/candidate-reranker-transfer-20260918'
OUT=ROOT/'analysis/candidate-edit-effect-ledger-20260918.json'
NAMES=('old','e0','e1','leaf7','scrambled')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    audit=json.loads((RUN/'audit.json').read_text());assert audit['passed']
    outcomes=json.loads((RUN/'results.json').read_text())['tasks']
    records=json.loads((RUN/'frozen_records.json').read_text())
    base=json.loads((RUN/'base_pools.json').read_text())
    wide=json.loads((RUN/'ast_wide_pools.json').read_text())
    assert len(outcomes)==len(records)==576
    rows=[]
    for outcome,record in zip(outcomes,records):
        key=outcome['id'];assert key==record['id']
        pool=wide.get(key,base[key]);assert len(pool)==len(record['orders']['old'])
        zero=outcome['zero'];one=outcome['one']
        effects={'e0_vs_old':zero['e0']-zero['old'],
                 'e1_vs_e0':zero['e1']-zero['e0'],
                 'e1_vs_old':zero['e1']-zero['old'],
                 **{f'query_gain_{name}':one[name]-zero[name] for name in NAMES}}
        rows.append({'id':key,'seed':outcome['seed'],'family':outcome['family'],
                     'public_block':outcome['public_block'],
                     'public_query_features':record['query_features'],
                     'pool_candidates':len(pool),
                     'top20_candidates_rescored':min(20,len(pool)),
                     'full_reachable':outcome['full_reachable'],
                     'top20_reachable':outcome['top20_reachable'],
                     'zero':zero,'one':one,'effects':effects,
                     'costs':{'candidate_rescores_per_model':min(20,len(pool)),
                              'predicted_output_cells':len(pool)*8,
                              'exact_output_calls_if_queried':1}})
    by_family=defaultdict(list)
    for row in rows:by_family[row['family']].append(row)
    names=tuple(rows[0]['effects'])
    def aggregate(group):
        return {'tasks':len(group),'correct':{name:sum(r['zero'][name] for r in group)
                                              for name in NAMES},
                'effects':{name:{'gain':sum(r['effects'][name]>0 for r in group),
                                 'harm':sum(r['effects'][name]<0 for r in group),
                                 'net':sum(r['effects'][name] for r in group)}
                           for name in names}}
    result={'scope':'opened target labels; typed verified effects for later improver development',
            'tasks':len(rows),'overall':aggregate(rows),
            'by_family':{family:aggregate(group) for family,group in by_family.items()},
            'rows':rows,
            'source_sha256':{filename:sha(RUN/filename) for filename in
                 ('audit.json','results.json','frozen_records.json','base_pools.json',
                  'ast_wide_pools.json','bank_manifest.json')},
            'limits':['Effect labels are observed only after opening the external oracle.',
                      'Per-model candidate rescoring and training source costs must be charged when comparing policies.',
                      'This ledger does not itself learn or validate an improver.']}
    write_json(OUT,result)
    print(json.dumps({'tasks':result['tasks'],'overall':result['overall'],
                      'by_family_effects':{k:v['effects']['e1_vs_old']
                                           for k,v in result['by_family'].items()}},indent=2))


if __name__=='__main__':main()
