"""Opened-bank screen of small mechanism quotas around the frozen evaluator."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import values
from posterior_query_value_development import read_panel,META,FOCUSED,MODEL


OUT=ROOT/'analysis/family-quota-development-20260918.json'


def evaluate(rows,block,quota):
    p={r['id']:float(v) for r,v in zip(rows,values(MODEL,rows))}
    groups=defaultdict(list)
    for row in rows:groups[row['seed']].append(row)
    banks=[]
    for seed,group in sorted(groups.items()):
        ordered=lambda members:sorted(members,key=lambda r:(p[r['id']],r['id']),reverse=True)
        mandatory=ordered([r for r in group if r['public_block']==block])[:quota]
        remainder=ordered([r for r in group if r not in mandatory])[:8-quota]
        selected={r['id'] for r in mandatory+remainder}
        banks.append({'seed':seed,'correct':sum(r['one'] if r['id'] in selected else r['zero']
                                               for r in group),
                      'selected_gain':sum(r['gain'] for r in group if r['id'] in selected),
                      'block_calls':sum(r['public_block']==block and r['id'] in selected
                                        for r in group)})
    return {'correct':sum(b['correct'] for b in banks),
            'selected_gain':sum(b['selected_gain'] for b in banks),
            'block_calls':sum(b['block_calls'] for b in banks),
            'by_bank':banks}


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    panels={name:read_panel(META/name) for name in ('admission','a','b')}
    panels['focused']=read_panel(FOCUSED)
    blocks={'transform':0x700,'ast':0x800,'novel':0x900,
            'stack':0xa00,'mutation':0xc00,'self_edit':0xd00}
    result={name:{f'{family}_{quota}':evaluate(rows,block,quota)
                  for family,block in blocks.items() for quota in (0,1,2)}
            for name,rows in panels.items()}
    write_json(OUT,{'scope':'opened-bank policy screen; no fresh promotion evidence',
                    'panels':result})
    print(json.dumps({name:{policy:score['correct'] for policy,score in panel.items()}
                      for name,panel in result.items()},indent=2))


if __name__=='__main__':main()
