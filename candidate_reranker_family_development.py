"""Opened-bank public-family gate screen for the frozen candidate rerankers."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT,write_json
from candidate_reranker_transfer import DEST,CACHE,K,model_path


OUT=ROOT/'analysis/candidate-reranker-family-development-20260918.json'


def cached_panel(name,model):
    raw=np.load(CACHE/f'{name}.npz');x=raw['x'];y=raw['y']
    detail=json.loads((CACHE/f'{name}.json').read_text())['tasks_detail']
    probabilities=model.predict_proba(x)[:,1]
    rows=[];offset=0
    for task in detail:
        n=task['candidate_count'];p=probabilities[offset:offset+n]
        choice=int(np.argmax(p+np.linspace(1e-12,0,n)))
        rows.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                     'old':task['baseline_correct'],
                     'new':int(y[offset+choice])})
        offset+=n
    assert offset==len(y)
    return rows


def fresh_panel():
    data=json.loads((DEST/'results.json').read_text())['tasks']
    return [{'id':r['id'],'seed':r['seed'],'family':r['family'],
             'old':r['zero']['old'],'new':r['zero']['e1'],
             'old_eight':r['one']['old'],'new_eight':r['one']['e1']}
            for r in data]


def aggregate(rows):
    families=defaultdict(list)
    for row in rows:families[row['family']].append(row)
    by_family={family:{'tasks':len(group),
                       'old':sum(r['old'] for r in group),
                       'new':sum(r['new'] for r in group),
                       'effect':sum(r['new']-r['old'] for r in group)}
               for family,group in families.items()}
    gate=sum(r['old'] if r['family']=='self_edit_transition' else r['new'] for r in rows)
    return {'tasks':len(rows),'old':sum(r['old'] for r in rows),
            'new':sum(r['new'] for r in rows),'self_edit_gate':gate,
            'by_family':by_family}


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    model=joblib.load(model_path('e1'))
    panels={name:aggregate(cached_panel(name,model)) for name in ('focused','pairwise')}
    panels['fresh_opened']=aggregate(fresh_panel())
    result={'scope':'all panels opened; family gate is post hoc development',
            'panels':panels,
            'limits':['E1 was trained on meta admission/A/B only; these three panels are disjoint from training.',
                      'The self-edit gate was chosen after seeing these labels and needs fresh confirmation.']}
    write_json(OUT,result)
    print(json.dumps({name:{key:panel[key] for key in ('old','new','self_edit_gate','by_family')}
                      for name,panel in panels.items()},indent=2))


if __name__=='__main__':main()
