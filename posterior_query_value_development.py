"""Opened-bank screen of candidate-posterior query-value surrogates.

The sensor answer is never used as a feature. A candidate's predicted answer is
grouped with other candidates; only frozen scores and predicted outputs enter.
All panels here have already been opened, so results are development evidence.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import values


OUT=ROOT/'analysis/posterior-query-value-development-20260918.json'
META=ROOT/'runs/cross-family-meta-improver-transfer-20260918'
FOCUSED=ROOT/'runs/focused-feedback-transfer-20260918'
MODEL=json.loads((FOCUSED/'models.json').read_text())['e0']
KS=(20,64)
TAUS=(.25,.5,1.,2.)


def read_panel(directory):
    records=json.loads((directory/'frozen_records.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert len(records)==len(outcomes)
    rows=[]
    for r,o in zip(records,outcomes):
        assert r['id']==o['id']
        rows.append({'id':r['id'],'seed':r['seed'],'family':r['family'],
                     'public_block':r['public_block'],'features':r['features'],
                     'zero':int(o['zero']),'one':int(o['one']),
                     'gain':int(o['one'])-int(o['zero']),
                     'scores':r['scores'],'order':r['order'],
                     'first_probe':r['first_probe'],
                     'predicted':predicted[r['id']]})
    return rows


def proxy(row,k,tau):
    order=row['order'][:k]
    scores=np.asarray(row['scores'],float)
    spread=max(float(scores.std()),.05)
    top=float(scores[order[0]])
    weights=np.exp(np.clip((scores[order]-top)/(spread*tau),-50,0))
    maxima={}
    first=row['first_probe'];matrix=row['predicted']
    for index,weight in zip(order,weights):
        answer=matrix[index][first]
        maxima[answer]=max(maxima.get(answer,0.),float(weight))
    return (sum(maxima.values())-1.)/max(float(weights.sum()),1e-12)


def bank_scores(rows,priority):
    groups=defaultdict(list)
    for r in rows:groups[r['seed']].append(r)
    by_bank=[]
    for seed,group in sorted(groups.items()):
        assert len(group)==48
        selected={r['id'] for r in sorted(group,key=lambda r:(priority[r['id']],r['id']),
                                            reverse=True)[:8]}
        by_bank.append({'seed':seed,'correct':sum(r['one'] if r['id'] in selected else r['zero']
                                                 for r in group),
                        'selected_gain':sum(r['gain'] for r in group if r['id'] in selected),
                        'ast_calls':sum(r['public_block']==0x800 and r['id'] in selected
                                        for r in group)})
    return {'correct':sum(b['correct'] for b in by_bank),
            'selected_gain':sum(b['selected_gain'] for b in by_bank),
            'ast_calls':sum(b['ast_calls'] for b in by_bank),
            'by_bank':by_bank}


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    panels={name:read_panel(META/name) for name in ('admission','a','b')}
    panels['focused']=read_panel(FOCUSED)
    summary={}
    for name,rows in panels.items():
        base=values(MODEL,rows)
        priorities={'e0':{r['id']:float(v) for r,v in zip(rows,base)}}
        for k in KS:
            for tau in TAUS:
                key=f'posterior_k{k}_tau{tau}'
                priorities[key]={r['id']:proxy(r,k,tau) for r in rows}
        summary[name]={mode:bank_scores(rows,p) for mode,p in priorities.items()}
    result={'scope':'opened-bank development only','panels':summary,
            'formula':'sum of maximal candidate posterior mass per predicted answer minus global top posterior mass; softmax over top-k frozen ranker scores',
            'limits':['All panel oracle labels were opened before this screen.',
                      'Proxy assumes one correct program among the top-k; it is not a calibrated probability of true query gain.',
                      'Candidate-level score computation and predicted outputs add cost.']}
    write_json(OUT,result)
    print(json.dumps({name:{mode:{key:val[key] for key in ('correct','ast_calls')}
                            for mode,val in panel.items()} for name,panel in summary.items()},indent=2))


if __name__=='__main__':main()
