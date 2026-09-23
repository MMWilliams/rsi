"""Fresh fixed-total oracle-query allocation across AST tasks."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from ast_feedback_replay_update import pools_for, updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs, rank
from ast_query_allocation_development import features, predict, allocate, fixed


DEST = ROOT / 'runs/ast-query-allocation-transfer-20260918'
SOURCE = ROOT / 'analysis/ast-query-allocation-development.json'
RANKER = ROOT / 'analysis/ast-feedback-replay-model.json'
MIXED_SEEDS = tuple(range(902330, 902336))
AST_SEEDS = tuple(range(902336, 902342))
POLICIES = ('learned', 'one_each', 'random', 'entropy', 'disagreement', 'scrambled')


def target_tasks():
    tasks = []
    for seed in MIXED_SEEDS:
        for task in random_bank(seed, 48, FAMILIES, visible=1, hidden=23):
            if task['family'] == 'ast_transition':
                tasks.append({**task, 'seed': seed, 'stream': 'mixed'})
    for seed in AST_SEEDS:
        tasks.extend({**task, 'seed': seed, 'stream': 'ast_only'}
                     for task in random_bank(seed, 8, ('ast_transition',), visible=1, hidden=23))
    return tasks


def model_data():
    raw = json.loads(SOURCE.read_text(encoding='utf-8'))['model']
    return tuple(np.asarray(raw[name], dtype=float) for name in ('mean','scale','w1','w2'))


def allocations(tasks, records, predicted, model):
    by_id = {row['id']: row for row in records}
    output = {}
    for seed in (*MIXED_SEEDS, *AST_SEEDS):
        group = [task for task in tasks if task['seed'] == seed]
        assert len(group) == 8
        ids = [task['id'] for task in group]
        x = np.stack([features(task, {**by_id[task['id']],
                                      'first_probe':{'top20_entropy':by_id[task['id']]['first_probe']}},
                               predicted[task['id']])
                      for task in group])
        p1,p2 = predict(model,x)
        shifted = np.roll(x,1,axis=0)
        scrambled_1,scrambled_2 = predict(model,shifted)
        choices = {'learned': allocate(p1,p2,8),
                   'scrambled': allocate(scrambled_1,scrambled_2,8),
                   **{name: fixed(ids,x,8,name)
                      for name in ('one_each','random','entropy','disagreement')}}
        assert all(sum(action)==8 and all(0<=v<=2 for v in action)
                   for action in choices.values())
        output[str(seed)] = {name: dict(zip(ids,action)) for name,action in choices.items()}
    return output


def prepare():
    if DEST.exists(): raise RuntimeError('fresh allocation directory exists')
    tasks = target_tasks()
    start = time.perf_counter()
    pools, elapsed = pools_for(tasks)
    public = [({'id': task['id'], 'probe_inputs': [text for text,_ in task['hidden'][:8]]},
               pools[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted = dict(executor.map(predicted_outputs, public))
    ranker = updated_model()
    records = []
    for task in tasks:
        key = task['id']; rows = pools[key]
        scores,order = rank(task,rows,ranker)
        first = choose_probe(key,predicted[key],order,scores,
                             set(range(len(rows))),[],'top20_entropy')
        records.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                        'pool_sha256':digest(rows),'scores':scores,'order':order,
                        'first_probe':first})
    allocation = allocations(tasks,records,predicted,model_data())
    manifest = {'protocol':'EXPERIMENT-ast-query-allocation-transfer.md',
                'mixed_seeds':MIXED_SEEDS,'ast_only_seeds':AST_SEEDS,
                'tasks':len(tasks),'calls_per_bank':8,'policies':POLICIES,
                'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'ranker_sha256':hashlib.sha256(RANKER.read_bytes()).hexdigest(),
                'runner_sha256':hashlib.sha256((ROOT/'ast_query_allocation_transfer.py').read_bytes()).hexdigest(),
                'sensor_sha256':hashlib.sha256((ROOT/'ast_probe_sensor_development.py').read_bytes()).hexdigest(),
                'candidate_count':sum(len(rows) for rows in pools.values()),
                'generation_seconds':sum(elapsed.values()),
                'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'candidate_pools.json',pools)
    write_json(DEST/'predicted_probe_outputs.json',predicted)
    write_json(DEST/'frozen_records.json',records)
    write_json(DEST/'frozen_allocations.json',allocation)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'prepared',**manifest},indent=2))


def score():
    if (DEST/'results.json').exists(): raise RuntimeError('results exist')
    manifest=json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['source_sha256']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert manifest['ranker_sha256']==hashlib.sha256(RANKER.read_bytes()).hexdigest()
    assert manifest['runner_sha256']==hashlib.sha256((ROOT/'ast_query_allocation_transfer.py').read_bytes()).hexdigest()
    assert manifest['sensor_sha256']==hashlib.sha256((ROOT/'ast_probe_sensor_development.py').read_bytes()).hexdigest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools=json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    records=json.loads((DEST/'frozen_records.json').read_text(encoding='utf-8'))
    allocation=json.loads((DEST/'frozen_allocations.json').read_text(encoding='utf-8'))
    outcomes=[]
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key];matrix=predicted[key]
        assert key==record['id'] and digest(rows)==record['pool_sha256']
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        order=record['order'];scores=record['scores']
        correct=[bool(labels[order[0]])];used=[];remaining=set(range(len(rows)))
        for n in (1,2):
            j=record['first_probe'] if n==1 else choose_probe(
                key,matrix,order,scores,remaining,used,'top20_entropy')
            used.append(j)
            matched={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
            if matched: remaining=matched
            index=next((i for i in order if i in remaining),order[0])
            correct.append(bool(labels[index]))
        outcomes.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                         'reachable':any(labels),'correct_by_calls':correct,
                         'query_indices':used})
    by_id={r['id']:r for r in outcomes}
    by_bank=[]
    for seed in (*MIXED_SEEDS,*AST_SEEDS):
        group=[r for r in outcomes if r['seed']==seed]
        scores={}
        for policy,mapping in allocation[str(seed)].items():
            assert sum(mapping.values())==8
            scores[policy]=sum(by_id[key]['correct_by_calls'][calls]
                               for key,calls in mapping.items())
        by_bank.append({'seed':seed,'stream':group[0]['stream'],
                        'reachable':sum(r['reachable'] for r in group),
                        'no_query':sum(r['correct_by_calls'][0] for r in group),
                        'correct':scores})
    summary={'scope':'fresh fixed-total AST query allocation transfer',
             'tasks':len(tasks),'reachable':sum(r['reachable'] for r in outcomes),
             'oracle_outputs_per_policy':8*len(by_bank),
             'correct':{name:sum(bank['correct'][name] for bank in by_bank) for name in POLICIES},
             'no_query':sum(b['no_query'] for b in by_bank),
             'by_stream':{stream:{name:sum(bank['correct'][name] for bank in by_bank
                                           if bank['stream']==stream) for name in POLICIES}
                          for stream in ('mixed','ast_only')},
             'by_bank':by_bank,
             'learned_minus_one_each_by_bank':[
                 b['correct']['learned']-b['correct']['one_each'] for b in by_bank]}
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':{'prepare':prepare,'score':score}[sys.argv[1]]()
