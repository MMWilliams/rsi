"""Development-only diagnosis of remaining one-query evaluator errors."""
from __future__ import annotations

import json
from functools import lru_cache

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from active_probe_diagnostic import program_output


RUN=ROOT/'runs/sharp-query-value-transfer-20260917'
OUT=ROOT/'analysis/sharp-residual-diagnostic.json'


@lru_cache(maxsize=200000)
def output(program, inp):
    return program_output(program,inp)


def main():
    tasks=json.loads((RUN/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((RUN/'candidate_pools.json').read_text(encoding='utf-8'))
    plans=json.loads((RUN/'frozen_plans.json').read_text(encoding='utf-8'))
    outcomes=json.loads((RUN/'results.json').read_text(encoding='utf-8'))['tasks']
    rows_out=[]
    for task,plan,actual in zip(tasks,plans,outcomes):
        rows=pools[task['id']]
        scores=plan['scores']['temp_0.25_120']
        sharp=plan['selected']['temp_0.25_120']
        truth={}
        def correct(index):
            if index not in truth:
                truth[index]=bool(evaluate_program(rows[index]['program'],task['hidden'][8:]))
            return truth[index]
        choices=[]
        for inp,value in task['hidden'][:8]:
            matching=[i for i,row in enumerate(rows) if output(row['program'],inp)==value]
            index=max(matching,key=lambda i:(scores[i],-len(rows[i]['program']),
                                             rows[i]['program'])) if matching else sharp
            choices.append(index)
        probe_correct=[correct(index) for index in choices]
        queried=plan['queries']['top_disagreement'] is not None
        current=actual['correct']['top_disagreement']
        assert current==(probe_correct[plan['entropy_probe']] if queried else correct(sharp))
        rows_out.append({'id':task['id'],'seed':task['seed'],'family':task['family'],
                         'baseline':correct(sharp),'queried':queried,'current':current,
                         'entropy_probe':plan['entropy_probe'],
                         'probe_correct':probe_correct,
                         'any_probe_correct':any(probe_correct),
                         'best_probe_gain':int(any(probe_correct))-int(correct(sharp)),
                         'entropy_gain':int(probe_correct[plan['entropy_probe']])-int(correct(sharp))})
    def aggregate(group):
        return {'tasks':len(group),'baseline_correct':sum(x['baseline'] for x in group),
                'queried':sum(x['queried'] for x in group),
                'current_correct':sum(x['current'] for x in group),
                'unqueried_fixable':sum(not x['queried'] and not x['baseline'] and
                                       x['any_probe_correct'] for x in group),
                'queried_probe_miss':sum(x['queried'] and not x['current'] and
                                         x['any_probe_correct'] for x in group),
                'queried_unfixable':sum(x['queried'] and not x['current'] and
                                        not x['any_probe_correct'] for x in group),
                'query_harms':sum(x['queried'] and x['baseline'] and not x['current']
                                  for x in group),
                'query_all_entropy_correct':sum(x['baseline']+x['entropy_gain'] for x in group),
                'query_all_best_probe_correct':sum(x['baseline']+x['best_probe_gain'] for x in group)}
    summary={'scope':'development only; fresh transfer labels now inspected',
             'overall':aggregate(rows_out),
             'by_family':{family:aggregate([x for x in rows_out if x['family']==family])
                          for family in sorted({x['family'] for x in rows_out})},
             'by_bank':{str(seed):aggregate([x for x in rows_out if x['seed']==seed])
                        for seed in sorted({x['seed'] for x in rows_out})}}
    write_json(OUT,{'summary':summary,'tasks':rows_out})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
