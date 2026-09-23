"""Transfer a learned second-query allocator to fresh AST task banks."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_source_search import read
from active_probe_diagnostic import initial_model,choose_probe
from active_probe_sparse_pilot import larger_pool
from active_evaluator_transfer import unlabeled
from sequential_budget_development import fit,signals,rank


SOURCE=ROOT/'analysis/sequential-budget-development.json'
DEST=ROOT/'runs/sequential-budget-transfer-20260917'
SEEDS=tuple(range(902123,902129))
PER_BANK=64
EXTRA=16
METHODS=('learned','entropy','top_disagreement','survivors','random')


def prepare():
    if DEST.exists(): raise RuntimeError('transfer directory already exists')
    DEST.mkdir(parents=True)
    source_bytes=SOURCE.read_bytes()
    model=fit(json.loads(source_bytes)['tasks'])
    prior=ROOT/'runs/seed-low-9000'
    ranker=initial_model(prior,read(prior/'protected_banks.json'),
                         read(prior/'candidate_pools.json'))
    tasks=[]
    for seed in SEEDS:
        for task in random_bank(seed,PER_BANK,('ast_transition',),visible=2,hidden=22):
            tasks.append({'id':task['id'],'seed':seed,'visible':task['visible'],
                          'probe_inputs':[p[0] for p in task['hidden'][:8]],
                          'probe_outputs':[p[1] for p in task['hidden'][:8]],
                          'final':task['hidden'][8:]})
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated=list(executor.map(larger_pool,tasks))
    pools={key:rows for key,rows,_ in generated}
    records=[]; feature_rows=[]
    for task in tasks:
        record=unlabeled(task,pools[task['id']],ranker)
        assert record['n']>0
        first=choose_probe(task['id'],record['predicted_probe_outputs'],
                           list(range(record['n'])),[],record['scores'],
                           'weighted_entropy')
        minimax=max(range(8),key=lambda j:(record['features'][j][2],-j))
        record['choices']={'weighted_first':first,'minimax':minimax}
        del record['features']
        first_output=task['probe_outputs'][first]
        feature_rows.append(signals({'id':task['id'],'seed':task['seed'],
                                     'first_output':first_output},record))
        records.append(record)
    selected={}
    for seed in SEEDS:
        group=[r for r in feature_rows if r['seed']==seed]
        assert len(group)==PER_BANK
        for method in METHODS:
            chosen=sorted(group,key=lambda r:(-rank(r,method,model),r['id']))[:EXTRA]
            selected[f'{seed}:{method}']=[r['id'] for r in chosen]
    manifest={'protocol':'EXPERIMENT-sequential-evaluator-budget.md',
              'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
              'runner_sha256':hashlib.sha256(
                  (ROOT/'sequential_budget_transfer.py').read_bytes()).hexdigest(),
              'seeds':SEEDS,'per_bank':PER_BANK,'extra_queries_per_bank':EXTRA,
              'preparation_wall_seconds':time.perf_counter()-start,
              'model':{'scale':model[0].tolist(),'weights':model[1].tolist()}}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'frozen_records.json',records)
    write_json(DEST/'first_feedback_features.json',feature_rows)
    write_json(DEST/'frozen_allocations.json',selected)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared','tasks':len(tasks),
                      'extra_queries_per_bank':EXTRA,
                      'preparation_wall_seconds':manifest['preparation_wall_seconds']},indent=2))


def score():
    if (DEST/'results.json').exists(): raise RuntimeError('results already exist')
    manifest=read(DEST/'manifest.json')
    assert manifest['runner_sha256']==hashlib.sha256(
        (ROOT/'sequential_budget_transfer.py').read_bytes()).hexdigest()
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    tasks=read(DEST/'sealed_bank.json');records=read(DEST/'frozen_records.json')
    pools=read(DEST/'candidate_pools.json')
    feature_rows=read(DEST/'first_feedback_features.json')
    allocation=read(DEST/'frozen_allocations.json')
    selected={name:set(ids) for name,ids in allocation.items()}
    output=[]
    for task,record,feature in zip(tasks,records,feature_rows):
        assert task['id']==record['id']==feature['id']
        rows=pools[task['id']]
        assert digest(rows)==record['candidate_digest']
        correct=[evaluate_program(row['program'],task['final']) for row in rows]
        order=record['ranking'];pred=record['predicted_probe_outputs']
        j=record['choices']['weighted_first'];truth=task['probe_outputs']
        remaining=[i for i in order if pred[i][j]==truth[j]]
        if not remaining: remaining=order
        first=remaining[0]
        k=feature['second_probe']
        second_remaining=[i for i in remaining if pred[i][k]==truth[k]]
        second=second_remaining[0] if second_remaining else first
        outcomes={'baseline':bool(correct[order[0]]),'one_query':bool(correct[first]),
                  'all_two_query':bool(correct[second])}
        for method in METHODS:
            chosen=task['id'] in selected[f"{task['seed']}:{method}"]
            outcomes[method]=bool(correct[second if chosen else first])
        output.append({'id':task['id'],'seed':task['seed'],'reachable':any(correct),
                       'first_correct':bool(correct[first]),
                       'second_correct':bool(correct[second]),
                       'correct':outcomes})
    by_bank=[]
    names=list(output[0]['correct'])
    for seed in SEEDS:
        group=[r for r in output if r['seed']==seed]
        by_bank.append({'seed':seed,'reachable':sum(r['reachable'] for r in group),
                        **{name:sum(r['correct'][name] for r in group) for name in names}})
    summary={'scope':'fresh AST transfer; second-query allocation frozen before second outputs',
             'tasks':len(output),'reachable':sum(r['reachable'] for r in output),
             'query_budgets':{'baseline':0,'one_query':len(output),
                              'all_two_query':2*len(output),
                              **{name:len(output)+EXTRA*len(SEEDS) for name in METHODS}},
             'results':{name:sum(r['correct'][name] for r in output) for name in names},
             'learned_minus_entropy_by_bank':[b['learned']-b['entropy'] for b in by_bank],
             'by_bank':by_bank}
    write_json(DEST/'results.json',{'summary':summary,'tasks':output})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
