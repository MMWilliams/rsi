"""Development-only sensor-gated choice among evaluator-training edits."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import representation
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_source import train
from edit_effect_development import score
import seed_growth


SOURCE_A=ROOT/'analysis/mixed-evaluator-source.json'
RUN_B=ROOT/'runs/improver-acquisition-transfer-20260917'
OUT=ROOT/'analysis/seed-improver-gate-development.json'


def load_b():
    public=json.loads((RUN_B/'source_public_records.json').read_text(encoding='utf-8'))
    bank=json.loads((RUN_B/'source_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((RUN_B/'candidate_pools.json').read_text(encoding='utf-8'))
    source=[]
    for task,row in zip(bank,public):
        rows=pools[task['id']]
        source.append({**row,'family':task['family'],
                       'labels':[bool(evaluate_program(r['program'],task['hidden'][8:]))
                                 for r in rows]})
    target_bank=json.loads((RUN_B/'target_bank.json').read_text(encoding='utf-8'))
    target=[]
    for task in target_bank:
        rows=pools[task['id']]
        x=representation({'id':task['id'],'visible':task['visible']},rows)['structural']
        target.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                       'n':len(rows),'programs':[r['program'] for r in rows],
                       'structural':x.tolist(),
                       'labels':[bool(evaluate_program(r['program'],task['hidden'][8:]))
                                 for r in rows]})
    return source,target


def main():
    seed_growth.structure=bool_safe_structure
    a=json.loads(SOURCE_A.read_text(encoding='utf-8'))
    old=a['tasks'];base=np.asarray(a['full_weights'])
    new,target=load_b()
    models={'E192_base':base}
    for count in (48,96,192):
        replacement=train(new[:count])
        models[f'replace_B{count}']=replacement
        models[f'cumulative_A192_B{count}']=train([*old,*new[:count]])
        models[f'blend_A_B{count}']=.5*base+.5*replacement
    admission=target[:96];final=target[96:]
    scores={name:{'admission':score(w,admission),'final':score(w,final),
                  'source_B_tasks':0 if name=='E192_base' else
                    int(name.split('B')[-1])}
            for name,w in models.items()}
    admissible=[name for name in models if name!='E192_base' and
                scores[name]['admission'][0]>=scores['E192_base']['admission'][0]+2]
    chosen=max(admissible,key=lambda name:(scores[name]['admission'][0],
               -scores[name]['source_B_tasks'],name)) if admissible else 'E192_base'
    summary={'scope':'development only; target labels inspected in prior study',
             'admission_tasks':len(admission),'final_tasks':len(final),
             'gate':'admission correct >= base + 2; pick highest admission, then least B tasks',
             'scores':{name:{'admission_correct':s['admission'][0],
                             'final_correct':s['final'][0],
                             'admission_brier':s['admission'][1],
                             'final_brier':s['final'][1],
                             'source_B_tasks':s['source_B_tasks']}
                       for name,s in scores.items()},
             'chosen':chosen,'chosen_final_gain':scores[chosen]['final'][0]-
                                    scores['E192_base']['final'][0],
             'hindsight_best_final':max(models,key=lambda name:scores[name]['final'][0])}
    write_json(OUT,{'summary':summary,'weights':{k:v.tolist() for k,v in models.items()}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
