"""Opened shifted-AST top-20/50/100 reranker-width screen."""
from __future__ import annotations

import json
from collections import Counter,defaultdict

import joblib
import numpy as np

from rsi.common import ROOT,write_json
from rsi.semantic_invention import evaluate_program
from ast_evaluator_feedback import features as structural_features
from gated_ast_feedback import public_block
from cross_family_meta_improver_transfer import interval


RUN=ROOT/'runs/shifted-ast-seed-transfer-20260918'
MODEL=ROOT/'runs/candidate-reranker-transfer-20260918/e0.joblib'
OUT=ROOT/'analysis/shifted-ast-shortlist-development-20260918.json'
BLOCKS=(0x700,0x800,0x900,0xa00,0xc00,0xd00)
WIDTHS=(20,50,100)


def order_for(task,pool,record,width,model):
    old=record['orders']['old'];scores=np.asarray(record['old_scores'],float)
    head=old[:width];structural=np.asarray(structural_features(task,
        [pool[i] for i in head]),np.float32)
    assert structural.shape==(len(head),175)
    std=max(float(scores.std()),.05);top=float(scores[old[0]])
    block=np.asarray([float(public_block(task)==b) for b in BLOCKS],np.float32)
    x=[]
    for rank,index in enumerate(head):
        extra=np.asarray([(scores[index]-top)/std,rank/20,
                          np.log1p(len(pool))/8.],np.float32)
        x.append(np.r_[structural[rank],extra,block])
    p=model.predict_proba(np.asarray(x,np.float32))[:,1]
    top_order=sorted(range(len(head)),key=lambda i:(-float(p[i]),i))
    return [head[i] for i in top_order]+old[len(head):],len(head)


def main():
    if OUT.exists():raise RuntimeError('development output exists')
    assert json.loads((RUN/'audit.json').read_text())['passed']
    tasks=json.loads((RUN/'sealed_bank.json').read_text())
    pools=json.loads((RUN/'ast_wide_pools.json').read_text())
    matrices=json.loads((RUN/'predicted_probe_outputs.json').read_text())
    records=json.loads((RUN/'frozen_records.json').read_text())
    allocations=json.loads((RUN/'frozen_allocations.json').read_text())
    outcomes=json.loads((RUN/'results.json').read_text())['tasks']
    model=joblib.load(MODEL);rows=[];labels_checked=0
    for task,record,outcome in zip(tasks,records,outcomes):
        key=task['id'];assert key==record['id']==outcome['id']
        pool=pools[key];matrix=matrices[key]
        labels=[int(bool(evaluate_program(item['program'],task['hidden'][8:])))
                for item in pool]
        labels_checked+=len(labels)
        probe=record['probe'];truth=task['hidden'][probe][1]
        surviving={i for i in range(len(pool)) if matrix[i][probe]==truth}
        if not surviving:surviving=set(range(len(pool)))
        row={'id':key,'seed':task['seed'],'widths':{}}
        for width in WIDTHS:
            order,n=order_for(task,pool,record,width,model)
            if width==20:assert order==record['orders']['e0']
            row['widths'][str(width)]={'zero':labels[order[0]],
                'one':labels[next(i for i in order if i in surviving)],
                'rescores':n,'reachable':int(any(labels[i] for i in
                    record['orders']['old'][:width]))}
        rows.append(row)
    banks=[]
    for seed in sorted({r['seed'] for r in rows}):
        group=[r for r in rows if r['seed']==seed]
        selected=set(allocations[str(seed)]['cheap'])
        entry={'seed':seed}
        for width in WIDTHS:
            key=str(width)
            entry[key]={'zero':sum(r['widths'][key]['zero'] for r in group),
                'one_each':sum(r['widths'][key]['one'] for r in group),
                'four_calls':sum((r['widths'][key]['one'] if r['id'] in selected
                    else r['widths'][key]['zero']) for r in group),
                'reachable':sum(r['widths'][key]['reachable'] for r in group)}
        banks.append(entry)
    totals={str(w):{field:sum(b[str(w)][field] for b in banks) for field in
        ('zero','one_each','four_calls','reachable')} for w in WIDTHS}
    comparisons={}
    for width in WIDTHS[1:]:
        diffs=[b[str(width)]['four_calls']-b['20']['four_calls'] for b in banks]
        comparisons[str(width)]={'gain_four_calls':sum(diffs),
            'positive_banks':sum(x>0 for x in diffs),
            'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs),
            'task_gains':sum(r['widths'][str(width)]['zero']>
                             r['widths']['20']['zero'] for r in rows),
            'task_harms':sum(r['widths'][str(width)]['zero']<
                             r['widths']['20']['zero'] for r in rows)}
    result={'scope':'opened shifted-AST development only; not fresh transfer',
        'tasks':len(rows),'candidate_labels_rechecked':labels_checked,
        'totals':totals,'comparisons':comparisons,
        'model_predictions':{str(w):sum(r['widths'][str(w)]['rescores']
                                      for r in rows) for w in WIDTHS},
        'by_bank':banks,'rows':rows}
    assert labels_checked==json.loads((RUN/'results.json').read_text())[
        'summary']['candidate_labels_checked']
    write_json(OUT,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('by_bank','rows')},
                     indent=2))


if __name__=='__main__':main()
