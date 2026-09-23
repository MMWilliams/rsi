"""Development-only complementarity of classification and pairwise evaluators."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_transfer import choose
from pairwise_evaluator_development import target_b
import seed_growth


MODEL=ROOT/'analysis/pairwise-evaluator-development.json'
TARGET_A=ROOT/'analysis/improver-acquisition-target-development.json'
OUT=ROOT/'analysis/pairwise-complementarity-development.json'


def analyze(name,tasks,weights):
    rows=[]
    for task in tasks:
        x=np.asarray(task['structural'],dtype=float)
        programs=[{'program':p} for p in task['programs']]
        selected={}
        for key,w in weights.items():
            p=1/(1+np.exp(-np.clip(x@w,-30,30)))
            i=choose(p,programs)
            top=np.partition(p,-2)[-2:] if len(p)>1 else np.r_[p,p]
            selected[key]={'index':i,'correct':bool(task['labels'][i]),
                           'top_probability':float(top[-1]),
                           'margin':float(top[-1]-top[-2])}
        rows.append({'id':task['id'],'n':task['n'],'selected':selected})
    a='E192_classification';b='pairwise_random'
    summary={'tasks':len(rows),
             'classification':sum(r['selected'][a]['correct'] for r in rows),
             'pairwise':sum(r['selected'][b]['correct'] for r in rows),
             'combined_weights':sum(r['selected']['combined_pairwise_random']['correct'] for r in rows),
             'union_correct':sum(r['selected'][a]['correct'] or r['selected'][b]['correct'] for r in rows),
             'classification_only':sum(r['selected'][a]['correct'] and not r['selected'][b]['correct'] for r in rows),
             'pairwise_only':sum(r['selected'][b]['correct'] and not r['selected'][a]['correct'] for r in rows),
             'different_choice':sum(r['selected'][a]['index']!=r['selected'][b]['index'] for r in rows)}
    return {'name':name,'summary':summary,'tasks':rows}


def main():
    seed_growth.structure=bool_safe_structure
    raw=json.loads(MODEL.read_text(encoding='utf-8'))
    weights={k:np.asarray(v) for k,v in raw['weights'].items()}
    a=json.loads(TARGET_A.read_text(encoding='utf-8'))
    b=target_b()
    episodes=[analyze('A',a,weights),analyze('B',b,weights)]
    summary={r['name']:r['summary'] for r in episodes}
    write_json(OUT,{'summary':summary,'episodes':episodes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
