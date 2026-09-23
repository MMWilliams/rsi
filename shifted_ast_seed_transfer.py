"""Changed-mechanism AST transfer of the protected E0 plus cheap query seed."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import joblib
import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import shifted_ast_bank
from gated_ast_feedback import pools_for,public_block,BLOCK_AST
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features as query_features
from cross_family_meta_improver_development import values
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import candidate_features
from candidate_query_cost_transfer import cheap_public_features


DEST=ROOT/'runs/shifted-ast-seed-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-shifted-ast-seed-transfer.md'
RERANKER=ROOT/'runs/candidate-reranker-transfer-20260918/e0.joblib'
CHEAP_STATE=ROOT/'runs/candidate-query-cost-transfer-20260918/cost_children.json'
QUERY_MODEL=ROOT/'runs/focused-feedback-transfer-20260918/models.json'
SEEDS=tuple(range(903000,903012))
TASKS_PER_BANK=8
BUDGET=4


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for():
    return [{**task,'seed':seed} for seed in SEEDS
            for task in shifted_ast_bank(seed,TASKS_PER_BANK,visible=1,hidden=23)]


def route_for_generation(tasks):
    return [{**task,'family':'ast_transition'} for task in tasks]


def selected(rows,scores,k=BUDGET):
    order=sorted(range(len(rows)),key=lambda i:(float(scores[i]),rows[i]['id']),
                 reverse=True)
    return sorted(rows[i]['id'] for i in order[:k])


def hash_four(rows):
    return sorted(r['id'] for r in sorted(rows,key=lambda r:
        hashlib.sha256((r['id']+':shifted-four').encode()).digest())[:BUDGET])


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    assert json.loads((RERANKER.parent/'audit.json').read_text())['passed']
    assert json.loads((CHEAP_STATE.parent/'audit.json').read_text())['passed']
    tasks=tasks_for();start=time.perf_counter()
    base,wide,times=pools_for(route_for_generation(tasks))
    assert len(tasks)==96 and len(base)==96 and len(wide)==96
    public=[({'id':t['id'],'probe_inputs':[x for x,_ in t['hidden'][:8]]},
             wide[t['id']]) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    old_model=updated_model();e0=joblib.load(RERANKER)
    cheap=json.loads(CHEAP_STATE.read_text())['children']['cheap_initial']['model']
    prior=json.loads(QUERY_MODEL.read_text())['e0']
    records=[];rescores=0
    for task in tasks:
        key=task['id'];pool=wide[key]
        assert public_block(task)==BLOCK_AST
        scores,old_order=rank(task,pool,old_model)
        probe=choose_probe(key,predicted[key],old_order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        qfeatures=query_features(task,{'scores':scores,'order':old_order,
            'first_probe':{'top20_entropy':probe}},predicted[key])
        x=candidate_features(task,pool,scores,old_order)
        p=e0.predict_proba(x)[:,1]
        top=sorted(range(len(x)),key=lambda i:(-float(p[i]),i))
        e0_order=[old_order[i] for i in top]+old_order[len(x):]
        rescores+=len(x)
        record={'id':key,'seed':task['seed'],'family':task['family'],
            'public_block':public_block(task),'pool_sha256':digest(pool),
            'old_scores':scores,'orders':{'old':old_order,'e0':e0_order},
            'probe':probe,'query_features':qfeatures.tolist()}
        record['cheap_features']=cheap_public_features(record,predicted[key])
        records.append(record)
    by_seed={seed:[r for r in records if r['seed']==seed] for seed in SEEDS}
    allocations={};forecasts={}
    for seed in SEEDS:
        group=by_seed[seed]
        cheap_rows=[{'id':r['id'],'public_block':r['public_block'],
                     'features':r['cheap_features']} for r in group]
        old_rows=[{'id':r['id'],'public_block':r['public_block'],
                   'features':r['query_features']} for r in group]
        cp=values(cheap,cheap_rows);op=values(prior,old_rows)
        allocations[str(seed)]={'cheap':selected(group,cp),
            'incumbent':selected(group,op),'hash_four':hash_four(group)}
        forecasts[str(seed)]={'cheap':{r['id']:float(v) for r,v in zip(group,cp)},
            'incumbent':{r['id']:float(v) for r,v in zip(group,op)}}
        assert all(len(ids)==BUDGET for ids in allocations[str(seed)].values())
    manifest={'protocol_sha256':sha(PROTOCOL),
        'runner_sha256':sha(ROOT/'shifted_ast_seed_transfer.py'),
        'reranker_sha256':sha(RERANKER),'cheap_state_sha256':sha(CHEAP_STATE),
        'query_model_sha256':sha(QUERY_MODEL),'seeds':SEEDS,'tasks':len(tasks),
        'base_candidates':sum(map(len,base.values())),
        'extra_ast_candidates':sum(len(wide[k])-len(base[k]) for k in base),
        'top20_rescores':rescores,
        'candidate_output_cells':sum(len(wide[t['id']])*8 for t in tasks),
        'generation_seconds':sum(times.values()),
        'preparation_wall_seconds':time.perf_counter()-start}
    DEST.mkdir(parents=True)
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'base_pools.json',base)
    write_json(DEST/'ast_wide_pools.json',wide)
    write_json(DEST/'predicted_probe_outputs.json',predicted)
    write_json(DEST/'frozen_records.json',records)
    write_json(DEST/'frozen_allocations.json',allocations)
    write_json(DEST/'frozen_forecasts.json',forecasts)
    manifest['records_sha256']=sha(DEST/'frozen_records.json')
    manifest['allocations_sha256']=sha(DEST/'frozen_allocations.json')
    manifest['forecasts_sha256']=sha(DEST/'frozen_forecasts.json')
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'frozen',**manifest},indent=2))


def outcomes_for(tasks,wide,predicted,records):
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide[key];matrix=predicted[key]
        assert key==record['id'] and digest(pool)==record['pool_sha256']
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:])))
                for row in pool]
        checked+=len(labels)
        probe=record['probe']
        matching={i for i in range(len(pool))
                  if matrix[i][probe]==task['hidden'][probe][1]}
        remaining=matching if matching else set(range(len(pool)))
        old=record['orders']['old'];e0=record['orders']['e0']
        outcomes.append({'id':key,'seed':task['seed'],
            'full_reachable':int(any(labels)),
            'top20_reachable':int(any(labels[i] for i in old[:20])),
            'zero_old':labels[old[0]],'zero_e0':labels[e0[0]],
            'one_e0':labels[next(i for i in e0 if i in remaining)]})
    return outcomes,checked


def summarize(outcomes,allocations,checked):
    by_seed={seed:[r for r in outcomes if r['seed']==seed] for seed in SEEDS}
    banks=[]
    for seed in SEEDS:
        rows=by_seed[seed];entry={'seed':seed,'tasks':len(rows),
            'full_reachable':sum(r['full_reachable'] for r in rows),
            'top20_reachable':sum(r['top20_reachable'] for r in rows),
            'zero_old':sum(r['zero_old'] for r in rows),
            'zero_e0':sum(r['zero_e0'] for r in rows),
            'one_each':sum(r['one_e0'] for r in rows)}
        for name,ids in allocations[str(seed)].items():
            chosen=set(ids)
            entry[name]=sum(r['one_e0'] if r['id'] in chosen else r['zero_e0']
                            for r in rows)
        banks.append(entry)
    fields=('full_reachable','top20_reachable','zero_old','zero_e0',
            'cheap','incumbent','hash_four','one_each')
    totals={name:sum(b[name] for b in banks) for name in fields}
    comparisons={}
    for name in ('incumbent','hash_four'):
        diffs=[b['cheap']-b[name] for b in banks]
        comparisons[name]={'gain':sum(diffs),'positive_banks':sum(x>0 for x in diffs),
            'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    gate=bool(all(x['gain']>=4 and x['positive_banks']>=8 and
                  x['interval'][0]>0 for x in comparisons.values()))
    return {'tasks':len(outcomes),'candidate_labels_checked':checked,
        'calls_per_four_policy':len(SEEDS)*BUDGET,
        'calls_one_each':len(outcomes),'totals':totals,
        'comparisons':comparisons,'transfer_gate':gate,'banks':banks}


def score():
    if (DEST/'results.json').exists():raise RuntimeError('already scored')
    manifest=json.loads((DEST/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'shifted_ast_seed_transfer.py')
    assert manifest['records_sha256']==sha(DEST/'frozen_records.json')
    assert manifest['allocations_sha256']==sha(DEST/'frozen_allocations.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    records=json.loads((DEST/'frozen_records.json').read_text())
    allocations=json.loads((DEST/'frozen_allocations.json').read_text())
    outcomes,checked=outcomes_for(tasks,wide,predicted,records)
    summary=summarize(outcomes,allocations,checked)
    write_json(DEST/'results.json',{'summary':summary,'tasks':outcomes,
        'manifest_sha256':sha(DEST/'manifest.json')})
    print(json.dumps(summary,indent=2))


def audit():
    if (DEST/'audit.json').exists():raise RuntimeError('audit already exists')
    manifest=json.loads((DEST/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'shifted_ast_seed_transfer.py')
    assert manifest['reranker_sha256']==sha(RERANKER)
    assert manifest['cheap_state_sha256']==sha(CHEAP_STATE)
    assert manifest['query_model_sha256']==sha(QUERY_MODEL)
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    assert tasks==tasks_for()
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    rebuilt_base,rebuilt_wide,_=pools_for(route_for_generation(tasks))
    assert base==rebuilt_base and wide==rebuilt_wide
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    public=[({'id':t['id'],'probe_inputs':[x for x,_ in t['hidden'][:8]]},
             wide[t['id']]) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    old_model=updated_model();e0=joblib.load(RERANKER)
    cheap=json.loads(CHEAP_STATE.read_text())['children']['cheap_initial']['model']
    prior=json.loads(QUERY_MODEL.read_text())['e0']
    records=json.loads((DEST/'frozen_records.json').read_text())
    allocations=json.loads((DEST/'frozen_allocations.json').read_text())
    forecasts=json.loads((DEST/'frozen_forecasts.json').read_text())
    rebuilt=[]
    for task in tasks:
        key=task['id'];pool=wide[key]
        scores,old_order=rank(task,pool,old_model)
        probe=choose_probe(key,predicted[key],old_order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        qfeatures=query_features(task,{'scores':scores,'order':old_order,
            'first_probe':{'top20_entropy':probe}},predicted[key])
        x=candidate_features(task,pool,scores,old_order)
        p=e0.predict_proba(x)[:,1]
        top=sorted(range(len(x)),key=lambda i:(-float(p[i]),i))
        e0_order=[old_order[i] for i in top]+old_order[len(x):]
        row={'id':key,'seed':task['seed'],'family':task['family'],
            'public_block':public_block(task),'pool_sha256':digest(pool),
            'old_scores':scores,'orders':{'old':old_order,'e0':e0_order},
            'probe':probe,'query_features':qfeatures.tolist()}
        row['cheap_features']=cheap_public_features(row,predicted[key])
        rebuilt.append(row)
    assert rebuilt==records
    for seed in SEEDS:
        group=[r for r in rebuilt if r['seed']==seed]
        cp=values(cheap,[{'id':r['id'],'public_block':r['public_block'],
                          'features':r['cheap_features']} for r in group])
        op=values(prior,[{'id':r['id'],'public_block':r['public_block'],
                          'features':r['query_features']} for r in group])
        assert allocations[str(seed)]=={'cheap':selected(group,cp),
            'incumbent':selected(group,op),'hash_four':hash_four(group)}
        assert forecasts[str(seed)]=={'cheap':{r['id']:float(v)
            for r,v in zip(group,cp)},'incumbent':{r['id']:float(v)
            for r,v in zip(group,op)}}
    outcomes,checked=outcomes_for(tasks,wide,predicted,rebuilt)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['manifest_sha256']==sha(DEST/'manifest.json')
    assert saved['tasks']==outcomes
    assert saved['summary']==summarize(outcomes,allocations,checked)
    write_json(DEST/'audit.json',{'passed':True,'tasks_rebuilt':len(tasks),
        'candidate_labels_rechecked':checked,
        'predicted_output_cells_rechecked':manifest['candidate_output_cells'],
        'top20_rescores_rechecked':manifest['top20_rescores'],
        'allocations_rechecked':len(SEEDS)*3})
    print(json.dumps(json.loads((DEST/'audit.json').read_text()),indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
