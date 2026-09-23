"""Retrospective expert replay on already scored router banks (development)."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import representation
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_transfer import choose
import seed_growth


EXPERT=ROOT/'analysis/context-expert-evaluator-development.json'
RUN=ROOT/'runs/evaluator-router-transfer-20260917'
OUT=ROOT/'analysis/context-expert-replay-development.json'


def main():
    seed_growth.structure=bool_safe_structure
    model=json.loads(EXPERT.read_text(encoding='utf-8'))
    global_w=np.asarray(model['global_weights'])
    experts={int(k):np.asarray(v) for k,v in model['expert_weights'].items()}
    tasks=json.loads((RUN/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((RUN/'candidate_pools.json').read_text(encoding='utf-8'))
    outcome=[]
    for task in tasks:
        rows=pools[task['id']]
        if not rows:
            outcome.append({'id':task['id'],'seed':task['seed'],
                            'correct':{'global':False,'expert':False,'blend':False}})
            continue
        features=representation({'id':task['id'],'visible':task['visible']},rows)
        x=features['structural'];block=features['block']
        labels=[bool(evaluate_program(r['program'],task['hidden'][8:])) for r in rows]
        weights={'global':global_w,'expert':experts[block],
                 'blend':.5*global_w+.5*experts[block]}
        correct={name:bool(labels[choose(1/(1+np.exp(-np.clip(x@w,-30,30))),rows)])
                 for name,w in weights.items()}
        outcome.append({'id':task['id'],'seed':task['seed'],'correct':correct})
    summary={'scope':'development only; previously inspected fresh router banks',
             'tasks':len(outcome),'correct':{name:sum(r['correct'][name] for r in outcome)
                                            for name in ('global','expert','blend')},
             'by_bank':{str(seed):{name:sum(r['correct'][name] for r in outcome
                                         if r['seed']==seed)
                                   for name in ('global','expert','blend')}
                        for seed in sorted({r['seed'] for r in outcome})}}
    write_json(OUT,{'summary':summary,'tasks':outcome})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
