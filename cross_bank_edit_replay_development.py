"""Development-only transfer of measured edit utility across validation banks."""
import json

import numpy as np

from rsi.common import ROOT,write_json
from mixed_probe_diagnostic import bool_safe_structure
from mixed_evaluator_source import train
from edit_effect_development import load_a,load_b,score,BASE_TASKS,EDIT_TASKS
import seed_growth


EFFECTS=ROOT/'analysis/edit-effect-development-v2.json'
OUT=ROOT/'analysis/cross-bank-edit-replay-development.json'


def episode(name,source,prior_target,current_effects):
    base_rows=source[:BASE_TASKS]
    base=train(base_rows)
    prior_baseline=score(base,prior_target)
    rows=[]
    by_id={r['id']:r for r in current_effects}
    for task in source[BASE_TASKS:BASE_TASKS+EDIT_TASKS]:
        child=train([*base_rows,task])
        prior=score(child,prior_target)
        current=by_id[task['id']]
        rows.append({'id':task['id'],'candidate_labels':task['n'],
                     'prior_delta_correct':prior[0]-prior_baseline[0],
                     'prior_delta_brier':prior_baseline[1]-prior[1],
                     'prior_delta_auc':prior[2]-prior_baseline[2],
                     'current_delta_correct':current['delta_correct'],
                     'current_delta_brier':current['delta_brier'],
                     'current_delta_auc':current['delta_auc']})
    summary={}
    for metric in ('correct','brier','auc'):
        p=np.asarray([r[f'prior_delta_{metric}'] for r in rows],dtype=float)
        c=np.asarray([r[f'current_delta_{metric}'] for r in rows],dtype=float)
        ranked=sorted(range(len(rows)),key=lambda i:(-p[i],rows[i]['id']))
        accepted=[i for i in range(len(rows)) if p[i]>0]
        summary[metric]={'correlation':float(np.corrcoef(p,c)[0,1])
            if np.std(p)>0 and np.std(c)>0 else None,
            'prior_positive_count':len(accepted),
            'current_mean_if_prior_positive':float(np.mean(c[accepted])) if accepted else None,
            'current_mean_all':float(np.mean(c)),
            'top12_current_mean':float(np.mean(c[ranked[:12]])),
            'top12_current_values':c[ranked[:12]].tolist()}
    return {'episode':name,'prior_baseline_correct':prior_baseline[0],
            'prior_baseline_brier':prior_baseline[1],
            'prior_baseline_auc':prior_baseline[2],
            'summary':summary,'edits':rows}


def main():
    seed_growth.structure=bool_safe_structure
    source_a,target_a=load_a()
    source_b,target_b=load_b()
    effect=json.loads(EFFECTS.read_text(encoding='utf-8'))['episodes']
    a=episode('A_edits_prior_B_validation',source_a,target_b,effect[0]['effects'])
    b=episode('B_edits_prior_A_validation',source_b,target_a,effect[1]['effects'])
    report={'scope':'development only; prior and current validation labels already inspected',
            'A':a['summary'],'B':b['summary']}
    write_json(OUT,{'summary':report,'episodes':[a,b]})
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
