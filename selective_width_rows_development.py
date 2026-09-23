"""Opened task-level effects of widening dual-specialist ranking to 200."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import features
from dual_specialist_seed_evaluator import load_models
from specialist_applicability_development import pair_features
from expanded_shortlist_development import PANEL


OUT=ROOT/'analysis/selective-width-rows-development-20260918.json'


def rows_for(path,models):
    tasks,base,wide,_,records=load_panel(path)
    rows=[]
    for task,rec in zip(tasks,records):
        pool=wide.get(task['id'],base[task['id']])
        old=rec['orders']['old']
        n=min(200,len(old))
        x=features(task,pool,rec,n)
        p={name:model.predict_proba(x)[:,1]
           for name,model in models.items()}
        outcomes={};choices={};metadata={}
        for width in (100,150,200):
            m=min(width,n)
            head={name:max(range(m),key=lambda i:(float(prob[i]),-i))
                  for name,prob in p.items()}
            expert='shifted' if p['shifted'][head['shifted']]>p['familiar'][head['familiar']] else 'familiar'
            index=old[head[expert]]
            outcomes[str(width)]=int(bool(evaluate_program(pool[index]['program'],
                                                             task['hidden'][8:])))
            choices[str(width)]=index
            metadata[str(width)]={'expert':expert,
                'familiar_probability':float(p['familiar'][head['familiar']]),
                'shifted_probability':float(p['shifted'][head['shifted']])}
        if path.name=='dual-specialist-integration-transfer-20260918':
            assert choices['100']==rec['dual_choices']['confidence']
        score=np.asarray(rec['old_scores'],float)
        std=max(float(score.std()),.05)
        base100=metadata['100']
        public=pair_features(task['visible'][0])+[
            len(pool)/512.,len(old)/512.,std,
            base100['familiar_probability'],base100['shifted_probability'],
            base100['shifted_probability']-base100['familiar_probability'],
            float(base100['expert']=='shifted'),
            float(choices['100']==rec['orders']['e0'][0]),
            (score[choices['100']]-score[rec['orders']['e0'][0]])/std]
        rows.append({'id':task['id'],'seed':task['seed'],'panel':path.name,
            'domain':'shifted' if task['family']=='shifted_ast' else 'familiar',
            'public_features':public,'outcomes':outcomes,
            'effect_150':outcomes['150']-outcomes['100'],
            'effect_200':outcomes['200']-outcomes['100'],
            'extra_candidate_scores_150':2*(min(150,n)-min(100,n)),
            'extra_candidate_scores_200':2*(min(200,n)-min(100,n))})
    return rows


def main():
    if OUT.exists():raise RuntimeError('development exists')
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANEL)
    models=load_models()
    rows=[r for path in PANEL for r in rows_for(path,models)]
    result={'scope':'opened development only','rows':rows,
            'summary':{'tasks':len(rows),
                'zero_100':sum(r['outcomes']['100'] for r in rows),
                'zero_150':sum(r['outcomes']['150'] for r in rows),
                'zero_200':sum(r['outcomes']['200'] for r in rows),
                'positive_edit_200':sum(r['effect_200']>0 for r in rows),
                'negative_edit_200':sum(r['effect_200']<0 for r in rows),
                'positive_shifted':sum(r['effect_200']>0 and
                                       r['domain']=='shifted' for r in rows),
                'positive_familiar':sum(r['effect_200']>0 and
                                        r['domain']=='familiar' for r in rows)}}
    write_json(OUT,result)
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
