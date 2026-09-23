"""Development-only public-context experts from the same verified labels."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_source import train
from mixed_evaluator_transfer import choose
from pairwise_evaluator_development import target_b
import seed_growth


SOURCE=ROOT/'analysis/mixed-evaluator-source.json'
TARGET_A=ROOT/'analysis/improver-acquisition-target-development.json'
OUT=ROOT/'analysis/context-expert-evaluator-development.json'


def block(row):
    return round(row['structural'][0][137]*4096)


def evaluate(tasks,global_weight,experts,blend):
    metrics={'global':0,'expert':0,'blended':0,'reachable':0}
    by_block={}
    for task in tasks:
        if not task['n']:continue
        key=block(task)
        x=np.asarray(task['structural'],dtype=float)
        rows=[{'program':p} for p in task['programs']]
        y=task['labels'];metrics['reachable']+=any(y)
        entry=by_block.setdefault(key,{'tasks':0,'reachable':0,'global':0,'expert':0,'blended':0})
        entry['tasks']+=1;entry['reachable']+=any(y)
        weights={'global':global_weight,'expert':experts[key],
                 'blended':blend*experts[key]+(1-blend)*global_weight}
        for name,w in weights.items():
            p=1/(1+np.exp(-np.clip(x@w,-30,30)))
            correct=bool(y[choose(p,rows)])
            metrics[name]+=correct;entry[name]+=correct
    return {'overall':metrics,'by_public_block':by_block}


def main():
    seed_growth.structure=bool_safe_structure
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    rows=source['tasks'];global_weight=np.asarray(source['full_weights'])
    groups={}
    for row in rows:groups.setdefault(block(row),[]).append(row)
    experts={key:train(group) for key,group in groups.items()}
    target_a=json.loads(TARGET_A.read_text(encoding='utf-8'))
    target_b_rows=target_b()
    variants={'blend_0.5':{'A':evaluate(target_a,global_weight,experts,.5),
                           'B':evaluate(target_b_rows,global_weight,experts,.5)}}
    summary={'scope':'development only; targets inspected before expert design',
             'source_tasks':len(rows),'source_candidate_labels':sum(r['n'] for r in rows),
             'public_block_source_tasks':{str(k):len(v) for k,v in groups.items()},
             'variants':variants}
    write_json(OUT,{'summary':summary,'global_weights':global_weight.tolist(),
                    'expert_weights':{str(k):w.tolist() for k,w in experts.items()}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
