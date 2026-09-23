"""Opened screen of a single evaluator trained on familiar and shifted labels."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import (source_arrays as familiar_arrays,
                                                  features, MODELS as FAMILIAR_MODELS)
from shifted_zero_query_reranker_development import (source_arrays as shifted_arrays,
    A, B, MODELS as SHIFTED_MODELS)
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval


MIXED = ROOT/'runs/specialist-applicability-transfer-20260918'
SHIFTED = ROOT/'runs/zero-query-shifted-feedback-transfer-20260918'
FAMILIAR = ROOT/'runs/combined-ranker-query-transfer-20260918'
OUT = ROOT/'analysis/pooled-zero-query-reranker-development-20260918.json'
MODELS = ROOT/'analysis/pooled-zero-query-reranker-models-20260918'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def train():
    familiar_x,familiar_y,_,count=familiar_arrays()
    a=shifted_arrays(A)
    b=shifted_arrays(B)
    shifted_x=np.r_[a['x'],b['x']]
    shifted_y=np.r_[a['y'],b['y']]
    x=np.r_[familiar_x,shifted_x]
    y=np.r_[familiar_y,shifted_y]
    weights=np.r_[np.ones(len(familiar_y)),np.full(len(shifted_y),3.)]
    models={'pooled_equal':model_for(15).fit(x,y),
            'pooled_shifted3':model_for(15).fit(x,y,sample_weight=weights)}
    return models,{'familiar_labels':count,'shifted_labels':len(shifted_y),
                   'familiar_positives':int(familiar_y.sum()),
                   'shifted_positives':int(shifted_y.sum())}


def score_panel(path,models):
    tasks,base,wide,_,records=load_panel(path)
    familiar=joblib.load(FAMILIAR_MODELS/'top50.joblib')
    shifted=joblib.load(SHIFTED_MODELS/'ab_top100.joblib')
    all_models={**models,'familiar_top50':familiar,'shifted_top100':shifted}
    rows=[]
    for task,rec in zip(tasks,records):
        if task['family'] not in ('ast_transition','shifted_ast'):
            continue
        pool=wide.get(task['id'],base[task['id']])
        old=rec['orders']['old']
        n=min(100,len(old))
        x=features(task,pool,rec,n)
        chosen={'e0':rec['orders']['e0'][0]}
        for name,model in all_models.items():
            width=min(50,n) if name=='familiar_top50' else n
            p=model.predict_proba(x[:width])[:,1]
            pick=max(range(width),key=lambda i:(float(p[i]),-i))
            chosen[name]=old[pick]
        labels={name:int(bool(evaluate_program(pool[i]['program'],
                                               task['hidden'][8:])))
                for name,i in chosen.items()}
        rows.append({'seed':task['seed'],'domain':'shifted' if
                     task['family']=='shifted_ast' else 'familiar',
                     'labels':labels})
    banks=[]
    names=tuple(rows[0]['labels'])
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        bank={'seed':seed}
        for name in names:
            bank[name]=sum(r['labels'][name] for r in group)
            bank[name+'_shifted']=sum(r['labels'][name] for r in group
                                      if r['domain']=='shifted')
            bank[name+'_familiar']=sum(r['labels'][name] for r in group
                                       if r['domain']=='familiar')
        banks.append(bank)
    totals={k:sum(b[k] for b in banks) for k in banks[0] if k!='seed'}
    pairs=(('pooled_equal','shifted_top100'),
           ('pooled_shifted3','shifted_top100'),
           ('pooled_shifted3','pooled_equal'))
    comparison={f'{a}_minus_{b}':{'gain':sum(bank[a]-bank[b] for bank in banks),
        'wins':sum(bank[a]>bank[b] for bank in banks),
        'losses':sum(bank[a]<bank[b] for bank in banks),
        'interval':interval([bank[a]-bank[b] for bank in banks])}
        for a,b in pairs}
    return {'tasks':len(rows),'totals':totals,'comparisons':comparison,
            'banks':banks}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development output exists')
    models,source=train()
    MODELS.mkdir(parents=True)
    for name,model in models.items():
        joblib.dump(model,MODELS/f'{name}.joblib',compress=3)
    targets={path.name:score_panel(path,models)
             for path in (MIXED,SHIFTED,FAMILIAR)}
    result={'scope':'opened development only','source':source,
            'model_sha256':{name:sha(MODELS/f'{name}.joblib')
                            for name in models},'targets':targets}
    write_json(OUT,result)
    print(json.dumps({'scope':result['scope'],'source':source,
        'targets':{name:{k:v for k,v in panel.items() if k!='banks'}
                   for name,panel in targets.items()}},indent=2))


if __name__=='__main__':
    main()
