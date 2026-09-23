"""Opened-bank task-level candidate-ranker edit catalog headroom."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT,write_json


RUN=ROOT/'runs/candidate-reranker-transfer-20260918'
OUT=ROOT/'analysis/candidate-edit-catalog-headroom-v2-20260918.json'
NAMES=('old','e0','e1','leaf7')


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    tasks=json.loads((RUN/'results.json').read_text())['tasks']
    families=defaultdict(list)
    for task in tasks:families[task['family']].append(task)
    totals={name:sum(t['zero'][name] for t in tasks) for name in NAMES}
    best_fixed=max(NAMES,key=lambda name:(totals[name],-NAMES.index(name)))
    family_best={family:max(NAMES,key=lambda name:(sum(t['zero'][name] for t in rows),
                                                 -NAMES.index(name)))
                 for family,rows in families.items()}
    family_score=sum(t['zero'][family_best[t['family']]] for t in tasks)
    task_score=sum(max(t['zero'][name] for name in NAMES) for t in tasks)
    by_bank=defaultdict(list)
    for task in tasks:by_bank[task['seed']].append(task)
    e1_oracle_eight=0;joint_oracle_eight=0
    for group in by_bank.values():
        e1_oracle_eight+=sum(t['zero']['e1'] for t in group)+sum(sorted(
            (t['one']['e1']-t['zero']['e1'] for t in group),reverse=True)[:8])
        base_score=[max(t['zero'][name] for name in NAMES) for t in group]
        best_one=[max(t['one'][name] for name in NAMES) for t in group]
        joint_oracle_eight+=sum(base_score)+sum(sorted(
            (a-b for a,b in zip(best_one,base_score)),reverse=True)[:8])
    result={'scope':'opened-bank hindsight catalog bound; final labels unavailable to a deployed improver',
            'tasks':len(tasks),'policies':NAMES,'policy_correct':totals,
            'best_fixed':best_fixed,'best_fixed_correct':totals[best_fixed],
            'unavailable_best_family_route':family_best,
            'unavailable_best_family_correct':family_score,
            'unavailable_best_task_correct':task_score,
            'task_route_headroom':task_score-totals[best_fixed],
            'unavailable_e1_best_eight_queries':e1_oracle_eight,
            'unavailable_joint_task_edit_eight_queries':joint_oracle_eight,
            'joint_headroom_over_e1_fixed_eight':joint_oracle_eight-
                json.loads((RUN/'results.json').read_text())['summary']['totals']['budget_eight']['e1'],
            'top20_reachable':sum(t['top20_reachable'] for t in tasks),
            'full_reachable':sum(t['full_reachable'] for t in tasks),
            'by_family':{family:{'tasks':len(rows),
                        'correct':{name:sum(t['zero'][name] for t in rows) for name in NAMES},
                        'oracle_task_best':sum(max(t['zero'][name] for name in NAMES)
                                               for t in rows)}
                         for family,rows in families.items()},
            'limits':['Both oracle routes use hidden final labels; this is action-space headroom, not achieved improvement.',
                      'The catalog contains only already tested candidate rankers on a fixed pool.',
                      'Deploying multiple models has additional training and inference cost.']}
    write_json(OUT,result)
    print(json.dumps({k:result[k] for k in ('policy_correct','best_fixed',
        'best_fixed_correct','unavailable_best_family_correct',
        'unavailable_best_task_correct','task_route_headroom',
        'unavailable_e1_best_eight_queries',
        'unavailable_joint_task_edit_eight_queries','joint_headroom_over_e1_fixed_eight',
        'top20_reachable','full_reachable')},indent=2))


if __name__=='__main__':main()
