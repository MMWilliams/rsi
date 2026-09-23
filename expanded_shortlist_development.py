"""Opened width screen for the validated dual-specialist evaluator."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from post_query_candidate_development import load_panel
from wide_candidate_reranker_development import features
from dual_specialist_seed_evaluator import load_models
from cross_family_meta_improver_transfer import interval


PANEL=(ROOT/'runs/zero-query-mixed-integration-transfer-20260918',
       ROOT/'runs/three-action-improver-transfer-20260918',
       ROOT/'runs/dual-specialist-integration-transfer-20260918')
OUT=ROOT/'analysis/expanded-shortlist-development-20260918.json'
WIDTHS=(100,150,200,300,'full')


def panel_rows(path,models):
    tasks,base,wide,_,records=load_panel(path)
    rows=[];score_counts={str(w):0 for w in WIDTHS}
    for task,rec in zip(tasks,records):
        pool=wide.get(task['id'],base[task['id']])
        old=rec['orders']['old']
        x=features(task,pool,rec,len(old))
        p={name:model.predict_proba(x)[:,1]
           for name,model in models.items()}
        choices={};outcomes={}
        for width in WIDTHS:
            n=len(old) if width=='full' else min(width,len(old))
            best={name:max(range(n),key=lambda i:(float(prob[i]),-i))
                  for name,prob in p.items()}
            expert='shifted' if p['shifted'][best['shifted']]>p['familiar'][best['familiar']] else 'familiar'
            index=old[best[expert]]
            choices[str(width)]=index
            outcomes[str(width)]=int(bool(evaluate_program(pool[index]['program'],
                                                            task['hidden'][8:])))
            score_counts[str(width)]+=2*n
        if path.name=='dual-specialist-integration-transfer-20260918':
            assert choices['100']==rec['dual_choices']['confidence']
        rows.append({'id':task['id'],'seed':task['seed'],
                     'domain':'shifted' if task['family']=='shifted_ast' else 'familiar',
                     'choices':choices,'outcomes':outcomes,'pool_size':len(pool)})
    return rows,score_counts


def summarize(rows):
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        bank={'seed':seed}
        for width in WIDTHS:
            name=str(width)
            bank[name]=sum(r['outcomes'][name] for r in group)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(r['outcomes'][name] for r in group
                                           if r['domain']==domain)
        banks.append(bank)
    totals={k:sum(b[k] for b in banks) for k in banks[0] if k!='seed'}
    comparison={}
    for width in WIDTHS[1:]:
        name=str(width)
        d=[b[name]-b['100'] for b in banks]
        comparison[name]={'gain':sum(d),'wins':sum(x>0 for x in d),
                          'losses':sum(x<0 for x in d),
                          'interval':interval(d)}
    return {'tasks':len(rows),'totals':totals,'comparison_to_100':comparison,
            'banks':banks}


def main():
    if OUT.exists():raise RuntimeError('development exists')
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANEL)
    models=load_models()
    targets={}
    all_rows=[];all_scores={str(w):0 for w in WIDTHS}
    for path in PANEL:
        rows,cost=panel_rows(path,models)
        all_rows.extend(rows)
        for key,value in cost.items():all_scores[key]+=value
        targets[path.name]={'summary':summarize(rows),'candidate_scores':cost}
    result={'scope':'opened development only','targets':targets,
            'combined':summarize(all_rows),'combined_candidate_scores':all_scores}
    write_json(OUT,result)
    print(json.dumps({'scope':result['scope'],
        'targets':{name:{'summary':{k:v for k,v in item['summary'].items()
                                   if k!='banks'},'candidate_scores':item['candidate_scores']}
                   for name,item in targets.items()},
        'combined':{k:v for k,v in result['combined'].items() if k!='banks'},
        'combined_candidate_scores':all_scores},indent=2))


if __name__=='__main__':main()
