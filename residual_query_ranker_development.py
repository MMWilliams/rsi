"""Opened-bank test of a ridge-anchored correction at the eight-call boundary."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
import torch

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import source_rows,matrix,fit_method,values
from cross_family_meta_improver_transfer import stage_rows
from pairwise_query_ranking_development import focused_rows
from nonlinear_query_value_development import pair_run_rows


OUT=ROOT/'analysis/residual-query-ranker-development-20260918.json'
LAMBDAS=(.01,.1,1.)


def grouped(rows):
    groups=defaultdict(list)
    for i,row in enumerate(rows):groups[row['seed']].append(i)
    assert all(len(group)==48 for group in groups.values())
    return list(groups.values())


def fit_residual(rows,lam):
    ridge=fit_method(rows,'interaction_100')
    base=values(ridge,rows)
    raw=matrix(rows,'interaction')[:,1:]
    mean=raw.mean(axis=0);scale=np.maximum(raw.std(axis=0),.05)
    x=(raw-mean)/scale
    pairs=[]
    for group in grouped(rows):
        selected=set(sorted(group,key=lambda i:(float(base[i]),rows[i]['id']),
                            reverse=True)[:8])
        false=[i for i in selected if rows[i]['gain']<=0]
        missed=[i for i in group if rows[i]['gain']>0 and i not in selected]
        pairs.extend((i,j) for i in missed for j in false)
    assert pairs
    delta=torch.as_tensor(np.asarray([x[i]-x[j] for i,j in pairs],np.float32))
    base_delta=torch.as_tensor(np.asarray([base[i]-base[j] for i,j in pairs],np.float32))
    torch.set_num_threads(1);torch.manual_seed(0)
    weight=torch.nn.Parameter(torch.zeros(x.shape[1],dtype=torch.float32))
    optimizer=torch.optim.Adam([weight],lr=.02)
    for _ in range(300):
        optimizer.zero_grad()
        loss=(torch.nn.functional.softplus(-(base_delta+delta@weight)).mean()+
              lam*weight.square().sum())
        loss.backward();optimizer.step()
    return {'ridge':ridge,'mean':mean.tolist(),'scale':scale.tolist(),
            'weights':weight.detach().numpy().tolist(),'lambda':lam,
            'hard_pairs':len(pairs)}


def predict(model,rows):
    base=values(model['ridge'],rows)
    raw=matrix(rows,'interaction')[:,1:]
    z=(raw-np.asarray(model['mean']))/np.asarray(model['scale'])
    return base+z@np.asarray(model['weights'])


def evaluate(rows,scores):
    banks=[]
    for group in grouped(rows):
        selected=set(sorted(group,key=lambda i:(float(scores[i]),rows[i]['id']),
                            reverse=True)[:8])
        banks.append({'seed':rows[group[0]]['seed'],
                      'correct':sum(rows[i]['one'] if i in selected else rows[i]['zero']
                                    for i in group),
                      'ast_calls':sum(rows[i]['public_block']==0x800 for i in selected)})
    return {'correct':sum(b['correct'] for b in banks),
            'ast_calls':sum(b['ast_calls'] for b in banks),
            'by_bank':banks}


def panel(train,target):
    ridge=fit_method(train,'interaction_100')
    out={'ridge100':evaluate(target,values(ridge,target))}
    for lam in LAMBDAS:
        model=fit_residual(train,lam)
        out[f'residual_{lam}']={**evaluate(target,predict(model,target)),
                                'training_hard_pairs':model['hard_pairs']}
    return out


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    source=source_rows();admission=stage_rows('admission')
    added=admission+stage_rows('a')+stage_rows('b')
    result={'scope':'post hoc opened-bank development; no promotion evidence',
            'panels':{'meta_transfer':panel(source+admission,
                stage_rows('a')+stage_rows('b')),
              'focused_opened':panel(source+added,focused_rows()),
              'pairwise_opened':panel(source+added,pair_run_rows())},
            'limits':['Full task counterfactual labels are used to construct hard pairs.',
                      'All target labels had already been opened before this method screen.',
                      'Correction scores are not calibrated probabilities.']}
    write_json(OUT,result)
    print(json.dumps({panel:{name:{k:v[k] for k in ('correct','ast_calls')}
                             for name,v in models.items()}
                      for panel,models in result['panels'].items()},indent=2))


if __name__=='__main__':main()
