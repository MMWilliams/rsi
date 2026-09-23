"""Opened-bank screen of ridge/pairwise evaluator combination at eight calls."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import source_rows,fit_method,values
from cross_family_meta_improver_transfer import stage_rows
from focused_feedback_development import fit_weighted
from pairwise_query_ranking_development import train_pairwise,prediction,focused_rows


OUT=ROOT/'analysis/query-rank-fusion-development-20260918.json'
PAIR_RUN=ROOT/'runs/pairwise-query-transfer-20260918'


def pair_run_rows():
    records=json.loads((PAIR_RUN/'frozen_records.json').read_text())
    outcomes=json.loads((PAIR_RUN/'results.json').read_text())['tasks']
    return [{**{key:r[key] for key in ('id','seed','family','public_block','features')},
             'zero':int(o['zero']),'one':int(o['one']),
             'gain':int(o['one'])-int(o['zero'])} for r,o in zip(records,outcomes)]


def rank_scores(group,scores):
    order=sorted(range(len(group)),key=lambda i:(float(scores[i]),group[i]['id']),reverse=True)
    result=np.zeros(len(group),float)
    for rank,i in enumerate(order):result[i]=(len(group)-rank)/len(group)
    return result


def policies(group,ridge,pair):
    n=len(group);assert n==48
    ri=rank_scores(group,ridge);pa=rank_scores(group,pair)
    by_id=lambda ids:{group[i]['id'] for i in ids}
    top=lambda score,count:sorted(range(n),key=lambda i:(float(score[i]),group[i]['id']),
                                  reverse=True)[:count]
    result={'ridge':by_id(top(ridge,8)),'pair':by_id(top(pair,8))}
    for alpha in (.25,.5,.75):
        result[f'rank_blend_{alpha}']=by_id(top((1-alpha)*ri+alpha*pa,8))
    for count in (1,2):
        first=top(pair,count);remaining=[i for i in top(ridge,n) if i not in first][:8-count]
        result[f'pair_top_{count}_ridge_rest']=by_id(first+remaining)
        self_edit=[i for i in top(pair,n) if group[i]['public_block']==0xd00][:count]
        remaining=[i for i in top(ridge,n) if i not in self_edit][:8-len(self_edit)]
        result[f'self_edit_{count}_ridge_rest']=by_id(self_edit+remaining)
    assert all(len(ids)==8 for ids in result.values())
    return result


def evaluate(rows,ridge_model,pair_model):
    groups=defaultdict(list)
    for r in rows:groups[r['seed']].append(r)
    banks=[]
    for seed,group in sorted(groups.items()):
        ridge=values(ridge_model,group);pair=prediction(pair_model,group)
        choices=policies(group,ridge,pair)
        banks.append({'seed':seed,'correct':{name:sum(r['one'] if r['id'] in ids
                                                    else r['zero'] for r in group)
                                              for name,ids in choices.items()}})
    totals={name:sum(b['correct'][name] for b in banks) for name in banks[0]['correct']}
    return {'correct':totals,'banks':banks}


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    source=source_rows();admission=stage_rows('admission')
    added=admission+stage_rows('a')+stage_rows('b')
    base=fit_weighted(source,[1]*len(source))
    early_pair=train_pairwise(source+admission,.001,False,base)
    late_pair=train_pairwise(source+added,.001,False,base)
    panels={'meta_transfer':evaluate(stage_rows('a')+stage_rows('b'),
        fit_method(source+admission,'interaction_100'),early_pair),
        'focused_opened':evaluate(focused_rows(),
        fit_method(source+added,'interaction_100'),late_pair),
        'pairwise_opened':evaluate(pair_run_rows(),
        fit_method(source+added,'interaction_100'),late_pair)}
    write_json(OUT,{'scope':'opened-bank development only; all labels inspected',
                    'panels':panels,
                    'limits':['Ridge and pairwise share the same query budget but both training costs must be charged.',
                              'This combination screen is post hoc and needs fresh confirmation.']})
    print(json.dumps({name:data['correct'] for name,data in panels.items()},indent=2))


if __name__=='__main__':main()
