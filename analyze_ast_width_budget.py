"""Development-only exact hindsight bounds for AST width and first-query budgets."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from rsi.common import ROOT,write_json
from gated_ast_feedback import BLOCK_AST
from cross_family_meta_improver_transfer import interval

OUT=ROOT/'analysis/ast-width-budget-development-20260918.json'
PANELS=(('meta','admission'),('meta','a'),('meta','b'),('stable','a'),('stable','b'))


def best_queries(rows,wide_ids,budget=8):
    zero=sum(r['wide_zero'] if r['id'] in wide_ids else r['base_zero'] for r in rows)
    gains=sorted(((r['wide_one']-r['wide_zero']) if r['id'] in wide_ids
                  else (r['base_one']-r['base_zero'])) for r in rows)
    return zero+sum(gains[-budget:])


def exact_joint(rows,width_budget=4,query_budget=8):
    states={(0,0):0}
    for row in rows:
        ast=row['public_block']==BLOCK_AST
        actions=((0,0,row['base_zero']),(0,1,row['base_one']))
        if ast:actions+=((1,0,row['wide_zero']),(1,1,row['wide_one']))
        nxt={}
        for (w,q),score in states.items():
            for add_w,add_q,value in actions:
                key=(w+add_w,q+add_q)
                if key[0]>width_budget or key[1]>query_budget:continue
                nxt[key]=max(nxt.get(key,-10**9),score+value)
        states=nxt
    return states[(width_budget,query_budget)]


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    rows=[]
    for name,stage in PANELS:
        path=ROOT/f'analysis/ast-width-query-counterfactuals-{name}-{stage}-20260918.json'
        rows+=json.loads(path.read_text())['rows']
    assert len(rows)==1440 and len({r['id'] for r in rows})==1440
    grouped=defaultdict(list)
    for r in rows:grouped[r['seed']].append(r)
    assert len(grouped)==30 and all(len(v)==48 for v in grouped.values())
    banks=[]
    for seed,group in sorted(grouped.items()):
        ast=[r for r in group if r['public_block']==BLOCK_AST]
        assert len(ast)==8
        random_ids={r['id'] for r in sorted(ast,key=lambda r:
            hashlib.sha256((r['id']+':width4').encode()).digest())[:4]}
        all_ids={r['id'] for r in ast}
        bank={'seed':seed,'base_oracle_q8':best_queries(group,set()),
              'random_width4_oracle_q8':best_queries(group,random_ids),
              'joint_oracle_width4_q8':exact_joint(group),
              'full_width_oracle_q8':best_queries(group,all_ids),
              'base_zero':sum(r['base_zero'] for r in group),
              'full_width_zero':sum(r['wide_zero'] for r in group),
              'full_width_one_all':sum(r['wide_one'] for r in group),
              'random_width4_extra_candidates':sum(r['extra_candidates'] for r in ast
                                                    if r['id'] in random_ids),
              'full_width_extra_candidates':sum(r['extra_candidates'] for r in ast)}
        assert bank['joint_oracle_width4_q8']>=bank['random_width4_oracle_q8']
        banks.append(bank)
    fields=tuple(k for k in banks[0] if k!='seed')
    totals={k:sum(b[k] for b in banks) for k in fields}
    differences=[b['joint_oracle_width4_q8']-b['random_width4_oracle_q8'] for b in banks]
    result={'scope':'opened development hindsight; no deployable width policy',
            'tasks':len(rows),'banks':len(banks),'ast_width_slots_per_bank':4,
            'true_query_calls_per_bank':8,'totals':totals,'by_bank':banks,
            'oracle_minus_random_width4':{'sum':sum(differences),
                                          'positive_banks':sum(d>0 for d in differences),
                                          'bank_bootstrap_95_sum':interval(differences)},
            'limits':['Joint and query oracles use unavailable final labels.',
                      'Exactly four widened AST tasks have variable candidate counts.',
                      'All potential wide pools were generated for this offline diagnostic.']}
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k!='by_bank'},indent=2))


if __name__=='__main__':main()
