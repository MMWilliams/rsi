"""Opened-bank comparison of query-gain regression and pairwise call ranking."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
import torch

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import source_rows,previous_panel,matrix,fit_method,values
from cross_family_meta_improver_transfer import stage_rows
from focused_feedback_development import fit_weighted


OUT=ROOT/'analysis/pairwise-query-ranking-development-20260918.json'
FOCUSED=ROOT/'runs/focused-feedback-transfer-20260918'
METHODS=('ridge10','ridge100','pair_all_001','pair_all_01',
         'pair_hard_001','pair_hard_01')


def focused_rows():
    records=json.loads((FOCUSED/'frozen_records.json').read_text())
    outcomes=json.loads((FOCUSED/'results.json').read_text())['tasks']
    assert len(records)==len(outcomes)==576
    return [{**{key:r[key] for key in ('id','seed','family','public_block','features')},
             'zero':int(o['zero']),'one':int(o['one']),
             'gain':int(o['one'])-int(o['zero'])} for r,o in zip(records,outcomes)]


def by_bank(rows):
    grouped=defaultdict(list)
    for i,row in enumerate(rows):grouped[row['seed']].append(i)
    assert all(len(indices)==48 for indices in grouped.values())
    return list(grouped.values())


def train_pairwise(rows,lam,hard,base_model):
    raw=matrix(rows,'interaction')[:,1:]
    mean=raw.mean(axis=0);scale=np.maximum(raw.std(axis=0),.05)
    x=(raw-mean)/scale
    base=values(base_model,rows)
    pairs=[]
    for indices in by_bank(rows):
        if hard:
            ordered=sorted(indices,key=lambda i:(base[i],rows[i]['id']),reverse=True)
            priority=set(ordered[:16])
            positive=[i for i in indices if rows[i]['gain']>0 and
                      (i in priority or any(rows[j]['gain']<=0 for j in ordered[:8]))]
            negative=[j for j in indices if rows[j]['gain']<=0 and j in priority]
        else:
            positive=[i for i in indices if rows[i]['gain']>0]
            negative=[j for j in indices if rows[j]['gain']<=0]
        pairs.extend((i,j) for i in positive for j in negative)
    assert pairs
    d=torch.as_tensor(np.asarray([x[i]-x[j] for i,j in pairs],np.float32))
    torch.set_num_threads(1);torch.manual_seed(0)
    weight=torch.nn.Parameter(torch.zeros(x.shape[1],dtype=torch.float32))
    optimizer=torch.optim.Adam([weight],lr=.05)
    for _ in range(300):
        optimizer.zero_grad()
        margin=d@weight
        loss=torch.nn.functional.softplus(-margin).mean()+lam*weight.square().sum()
        loss.backward();optimizer.step()
    return {'kind':'pairwise','mean':mean.tolist(),'scale':scale.tolist(),
            'weights':weight.detach().numpy().tolist(),
            'lambda':lam,'hard':hard,'pairs':len(pairs)}


def prediction(model,rows):
    if model['kind']!='pairwise':return values(model,rows)
    raw=matrix(rows,'interaction')[:,1:]
    return ((raw-np.asarray(model['mean']))/np.asarray(model['scale']))@np.asarray(model['weights'])


def evaluate(model,rows):
    p=prediction(model,rows)
    banks=[]
    for indices in by_bank(rows):
        chosen=set(sorted(indices,key=lambda i:(float(p[i]),rows[i]['id']),reverse=True)[:8])
        banks.append({'seed':rows[indices[0]]['seed'],
                      'correct':sum(rows[i]['one'] if i in chosen else rows[i]['zero'] for i in indices),
                      'gain':sum(rows[i]['gain'] for i in chosen),
                      'ast_calls':sum(rows[i]['public_block']==0x800 for i in chosen)})
    return {'correct':sum(b['correct'] for b in banks),
            'selected_gain':sum(b['gain'] for b in banks),
            'ast_calls':sum(b['ast_calls'] for b in banks),
            'by_bank':banks}


def models_for(train):
    base=fit_weighted(train[:576],[1]*576)
    result={'e0':base,'ridge10':fit_method(train,'interaction_10'),
            'ridge100':fit_method(train,'interaction_100')}
    for hard in (False,True):
        for lam,label in ((.001,'001'),(.01,'01')):
            name=f"pair_{'hard' if hard else 'all'}_{label}"
            result[name]=train_pairwise(train,lam,hard,base)
    return result


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    source=source_rows();admission=stage_rows('admission')
    validation=stage_rows('a')+stage_rows('b')
    focused=focused_rows()
    assert len(source)==576 and len(admission)==288 and len(validation)==len(focused)==576
    assert len({r['id'] for r in source+admission+validation+focused})==2016
    early=models_for(source+admission)
    late=models_for(source+admission+validation)
    stages={'earlier_validation':{name:evaluate(model,validation) for name,model in early.items()},
            'later_opened':{name:evaluate(model,focused) for name,model in late.items()}}
    result={'scope':'all validation labels previously opened; development only',
            'source_rows':len(source),'feedback_rows':len(admission),
            'validation_rows':len(validation),'later_training_rows':len(source+admission+validation),
            'later_panel_rows':len(focused),'stages':stages,
            'models':{'early':early,'late':late},
            'limits':['Pairwise gain labels require exact counterfactual one-query and no-query outcomes for all training tasks.',
                      'The methods and grids were selected after opening both validation sets.',
                      'Pairwise scores are ranks, not calibrated probabilities.']}
    write_json(OUT,result)
    print(json.dumps({stage:{name:{k:score[k] for k in ('correct','ast_calls')}
                             for name,score in policies.items()}
                      for stage,policies in stages.items()},indent=2))


if __name__=='__main__':main()
