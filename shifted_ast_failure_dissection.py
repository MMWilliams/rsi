"""Opened shifted-AST bottleneck decomposition after audited transfer."""
from __future__ import annotations

import json
from collections import Counter

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program


RUN=ROOT/'runs/shifted-ast-seed-transfer-20260918'
OUT=ROOT/'analysis/shifted-ast-failure-dissection-v2-20260918.json'


def main():
    if OUT.exists():raise RuntimeError('analysis already exists')
    assert json.loads((RUN/'audit.json').read_text())['passed']
    tasks=json.loads((RUN/'sealed_bank.json').read_text())
    pools=json.loads((RUN/'ast_wide_pools.json').read_text())
    matrix=json.loads((RUN/'predicted_probe_outputs.json').read_text())
    records=json.loads((RUN/'frozen_records.json').read_text())
    outcomes=json.loads((RUN/'results.json').read_text())['tasks']
    rows=[];checked=0
    for task,record,outcome in zip(tasks,records,outcomes):
        key=task['id'];assert key==record['id']==outcome['id']
        pool=pools[key];labels=[int(bool(evaluate_program(item['program'],
            task['hidden'][8:]))) for item in pool]
        checked+=len(labels)
        old=record['orders']['old'];e0=record['orders']['e0']
        probe=record['probe'];truth=task['hidden'][probe][1]
        surviving={i for i in range(len(pool)) if matrix[key][i][probe]==truth}
        if not surviving:surviving=set(range(len(pool)))
        correct={i for i,v in enumerate(labels) if v}
        top=set(old[:20]);top_correct=correct&top
        survivor_correct=correct&surviving
        post_choice=next(i for i in e0 if i in surviving)
        assert labels[old[0]]==outcome['zero_old']
        assert labels[e0[0]]==outcome['zero_e0']
        assert labels[post_choice]==outcome['one_e0']
        category=('unreachable' if not correct else
                  'correct_zero' if labels[e0[0]] else
                  'query_recovers' if labels[post_choice] else
                  'outside_top20' if not top_correct else
                  'probe_eliminated_correct' if not survivor_correct else
                  'surviving_correct_not_selected')
        old_best=next((rank for rank,i in enumerate(old) if i in correct),None)
        e0_best=next((rank for rank,i in enumerate(e0) if i in correct),None)
        rows.append({'id':key,'seed':task['seed'],'category':category,
            'full_reachable':int(bool(correct)),
            'top20_reachable':int(bool(top_correct)),
            'final_correct_survives_probe':int(bool(survivor_correct)),
            'final_correct_top20_survives_probe':int(bool(top_correct&surviving)),
            'zero_e0':labels[e0[0]],'one_e0':labels[post_choice],
            'best_correct_old_rank':old_best,'best_correct_e0_rank':e0_best,
            'correct_candidates':len(correct),'surviving_candidates':len(surviving)})
    counts=dict(Counter(r['category'] for r in rows))
    ranks={str(k):sum(r['best_correct_e0_rank'] is not None and
                       r['best_correct_e0_rank']<k for r in rows)
           for k in (1,5,10,20,50,100)}
    summary={'tasks':len(rows),'candidate_labels_rechecked':checked,
        'categories':counts,'best_correct_e0_within_rank':ranks,
        'full_reachable':sum(r['full_reachable'] for r in rows),
        'top20_reachable':sum(r['top20_reachable'] for r in rows),
        'correct_survives_probe':sum(r['final_correct_survives_probe'] for r in rows),
        'top20_correct_survives_probe':sum(
            r['final_correct_top20_survives_probe'] for r in rows),
        'zero_correct':sum(r['zero_e0'] for r in rows),
        'one_correct':sum(r['one_e0'] for r in rows),
        'query_recovers_below_old_top20':sum(r['one_e0'] and
            not r['zero_e0'] and not r['top20_reachable'] for r in rows)}
    assert summary['candidate_labels_rechecked']==json.loads(
        (RUN/'results.json').read_text())['summary']['candidate_labels_checked']
    write_json(OUT,{'scope':'opened changed-mechanism failure decomposition',
                    'summary':summary,'rows':rows})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
