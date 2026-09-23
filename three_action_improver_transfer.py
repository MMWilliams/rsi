"""Fresh common-pool test of a three-action evaluator controller."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank, shifted_ast_bank
from wide_candidate_reranker_development import features
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from pooled_zero_query_reranker_development import MODELS as POOLED_MODELS
from zero_query_router_development import public_row
from three_action_improver_development import source_rows, fit, ACTIONS
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST=ROOT/'runs/three-action-improver-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-three-action-improver-transfer.md'
SCRIPT=ROOT/'three_action_improver_transfer.py'
SOURCE=(ROOT/'runs/zero-query-shifted-feedback-transfer-20260918',
        ROOT/'runs/combined-ranker-query-transfer-20260918')
MIXED_SOURCE=ROOT/'runs/specialist-applicability-transfer-20260918'
TWO_ACTION=ROOT/'runs/zero-query-mixed-integration-transfer-20260918'
SEEDS=tuple(range(903700,903724))
MODEL_NAMES=('early','later','scrambled','duplicate')
NAMES=('e0','ab','pooled','two_route','early','later','scrambled','duplicate')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(obj):
    return json.loads(json.dumps(obj,ensure_ascii=False))


def tasks_for():
    tasks=[]
    for seed in SEEDS:
        familiar=random_bank(seed,4,('ast_transition',),visible=1,hidden=23)
        shifted=shifted_ast_bank(seed+100000,4,visible=1,hidden=23)
        for a,b in zip(familiar,shifted):
            tasks.extend(({**a,'seed':seed},{**b,'seed':seed}))
    return tasks


def public_run(tasks):
    prior=previous.SEEDS
    previous.SEEDS=SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS=prior


def train():
    assert all(json.loads((p/'audit.json').read_text())['passed']
               for p in SOURCE+(MIXED_SOURCE,TWO_ACTION))
    candidate={name:joblib.load(SHIFTED_MODELS/f'{name}_top100.joblib')
               for name in ('a','ab')}
    pooled=joblib.load(POOLED_MODELS/'pooled_equal.joblib')
    source=[r for p in SOURCE for r in source_rows(p,candidate,pooled)]
    mixed=source_rows(MIXED_SOURCE,candidate,pooled)
    assert len(source)==288 and len(mixed)==192
    rng=np.random.default_rng(904011)
    scrambled=[]
    for seed in sorted({r['seed'] for r in mixed}):
        group=[r for r in mixed if r['seed']==seed]
        perm=rng.permutation(len(group))
        scrambled.extend([{**r,'labels':group[int(j)]['labels']}
                          for r,j in zip(group,perm)])
    duplicate=[]
    for domain in ('familiar','shifted'):
        group=[r for r in source if r['domain']==domain]
        duplicate.extend([group[i] for i in rng.choice(len(group),96,replace=True)])
    models={'early':fit(source),'later':fit(source+mixed),
            'scrambled':fit(source+scrambled),
            'duplicate':fit(source+duplicate)}
    stats={'early_tasks':len(source),'added_mixed_tasks':len(mixed),
           'duplicate_added_rows':len(duplicate),
           'early_action_correct':{name:sum(r['labels'][name] for r in source)
                                   for name in ACTIONS},
           'mixed_action_correct':{name:sum(r['labels'][name] for r in mixed)
                                   for name in ACTIONS}}
    return models,candidate,pooled,stats


def freeze_choices(tasks,wide,records,models,candidate,pooled):
    two=joblib.load(TWO_ACTION/'visible_later.joblib')
    counts={'a':0,'ab':0,'pooled':0,'controller_action_scores':0}
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        public=public_row(task,rec,pool,candidate)
        old=rec['orders']['old']
        n=min(100,len(old))
        x=features(task,pool,rec,n)
        p=pooled.predict_proba(x)[:,1]
        pooled_index=old[max(range(n),key=lambda i:(float(p[i]),-i))]
        action={'e0':public['choices']['e0'],
                'ab':public['choices']['ab'],'pooled':pooled_index}
        route_x=np.asarray([public['features']],np.float32)
        two_p=float(two.predict_proba(route_x)[0,1])
        choices={**action,'two_route':action['ab'] if two_p>=.6 else action['e0']}
        probabilities={}
        for name,model in models.items():
            heads=model[0]
            probs=[float(heads[arm].predict_proba(route_x)[0,1])
                   for arm in ACTIONS]
            pick=int(np.argmax(probs))
            choices[name]=action[ACTIONS[pick]]
            probabilities[name]=probs
            counts['controller_action_scores']+=len(ACTIONS)
        assert set(choices)==set(NAMES)
        rec['three_action_features']=public['features']
        rec['three_action_probabilities']=probabilities
        rec['three_action_two_probability']=two_p
        rec['three_action_choices']=choices
        counts['a']+=public['candidate_scores']['a']
        counts['ab']+=public['candidate_scores']['ab']
        counts['pooled']+=n
    return records,counts


def manifest_for(models,stats,cost,counts):
    return {'protocol_sha256':sha(PROTOCOL),'script_sha256':sha(SCRIPT),
            'source_audit_sha256':[sha(p/'audit.json')
                                   for p in SOURCE+(MIXED_SOURCE,TWO_ACTION)],
            'candidate_model_sha256':{name:sha(SHIFTED_MODELS/f'{name}_top100.joblib')
                                      for name in ('a','ab')},
            'pooled_model_sha256':sha(POOLED_MODELS/'pooled_equal.joblib'),
            'two_route_sha256':sha(TWO_ACTION/'visible_later.joblib'),
            'controller_file_sha256':{name:sha(DEST/f'{name}.joblib')
                                      for name in MODEL_NAMES},
            'controller_object_hash':{name:joblib.hash(models[name])
                                      for name in MODEL_NAMES},
            'seeds':SEEDS,'tasks':192,'source':stats,
            'candidate_scores':counts,'cost':cost,
            'frozen_sha256':{name:sha(DEST/name) for name in
                             ('sealed_bank.json','base_pools.json',
                              'ast_wide_pools.json','predicted_probe_outputs.json',
                              'frozen_records.json','frozen_allocations.json',
                              'frozen_forecasts.json')}}


def prepare():
    if DEST.exists():
        raise RuntimeError('run exists')
    models,candidate,pooled,stats=train()
    tasks=tasks_for()
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,counts=freeze_choices(tasks,wide,records,models,candidate,pooled)
    DEST.mkdir(parents=True)
    for name,model in models.items():
        joblib.dump(model,DEST/f'{name}.joblib',compress=3)
    for name,value in (('sealed_bank.json',tasks),('base_pools.json',base),
                       ('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        write_json(DEST/name,value)
    write_json(DEST/'manifest.json',manifest_for(models,stats,cost,counts))
    print(json.dumps({'status':'frozen','tasks':len(tasks),
                      'source':stats,'candidate_scores':counts,
                      'predicted_output_cells':cost['predicted_output_cells']},
                     indent=2))


def outcomes_for(tasks,wide,records):
    outcome=[]
    checked=0
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        assert rec['id']==task['id'] and digest(pool)==rec['pool_sha256']
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:])))
                for row in pool]
        checked+=len(labels)
        outcome.append({'id':task['id'],'seed':task['seed'],
                        'domain':'shifted' if task['family']=='shifted_ast'
                        else 'familiar',
                        'full_reachable':int(any(labels)),
                        'top100_reachable':int(any(labels[i] for i in
                                                    rec['orders']['old'][:100])),
                        'labels':{name:labels[index] for name,index in
                                  rec['three_action_choices'].items()}})
    return outcome,checked


def comparison(banks,a,b):
    d=[bank[a]-bank[b] for bank in banks]
    return {'gain':sum(d),'positive_banks':sum(v>0 for v in d),
            'losing_banks':sum(v<0 for v in d),
            'interval':interval(d),'bank_differences':d}


def summarize(outcomes,checked):
    banks=[]
    for seed in SEEDS:
        group=[r for r in outcomes if r['seed']==seed]
        bank={'seed':seed,'full_reachable':sum(r['full_reachable'] for r in group),
              'top100_reachable':sum(r['top100_reachable'] for r in group),
              'three_action_oracle':sum(max(r['labels'][name]
                  for name in ACTIONS) for r in group)}
        for name in NAMES:
            bank[name]=sum(r['labels'][name] for r in group)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(r['labels'][name] for r in group
                                         if r['domain']==domain)
        banks.append(bank)
    totals={name:sum(b[name] for b in banks)
            for name in banks[0] if name!='seed'}
    pairs=(('later','ab'),('later','pooled'),('later','two_route'),
           ('later','early'),('later','scrambled'),('later','duplicate'))
    contrasts={f'{a}_minus_{b}':comparison(banks,a,b) for a,b in pairs}
    integrated=contrasts['later_minus_ab']
    gate_integration=(integrated['gain']>=8 and
                      integrated['positive_banks']>=8 and
                      integrated['interval'][0]>0 and
                      totals['later_familiar']>=totals['e0_familiar']-2 and
                      totals['later_shifted']>=totals['ab_shifted']-3)
    growth=[contrasts[f'later_minus_{name}']
            for name in ('early','scrambled','duplicate')]
    gate_growth=(all(c['gain']>=5 and c['interval'][0]>0 for c in growth) and
                 growth[0]['positive_banks']>=8)
    return {'tasks':len(outcomes),'output_calls':0,
            'candidate_labels_checked':checked,'totals':totals,
            'contrasts':contrasts,
            'gates':{'integration':gate_integration,
                     'incremental_improver':gate_growth},'banks':banks}


def verify_manifest(manifest):
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['script_sha256']==sha(SCRIPT)
    assert manifest['source_audit_sha256']==[
        sha(p/'audit.json') for p in SOURCE+(MIXED_SOURCE,TWO_ACTION)]
    assert manifest['seeds']==list(SEEDS)
    assert all(manifest['candidate_model_sha256'][name]==
        sha(SHIFTED_MODELS/f'{name}_top100.joblib') for name in ('a','ab'))
    assert manifest['pooled_model_sha256']==sha(POOLED_MODELS/'pooled_equal.joblib')
    assert manifest['two_route_sha256']==sha(TWO_ACTION/'visible_later.joblib')
    assert all(manifest['controller_file_sha256'][name]==sha(DEST/f'{name}.joblib')
               for name in MODEL_NAMES)
    assert all(manifest['frozen_sha256'][name]==sha(DEST/name)
               for name in manifest['frozen_sha256'])


def score():
    if (DEST/'results.json').exists():
        raise RuntimeError('already scored')
    verify_manifest(json.loads((DEST/'manifest.json').read_text()))
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    records=json.loads((DEST/'frozen_records.json').read_text())
    outcomes,checked=outcomes_for(tasks,wide,records)
    summary=summarize(outcomes,checked)
    write_json(DEST/'results.json',{'manifest_sha256':sha(DEST/'manifest.json'),
                                   'summary':summary,'tasks':outcomes})
    print(json.dumps({k:v for k,v in summary.items() if k!='banks'},indent=2))


def audit():
    if (DEST/'audit.json').exists():
        raise RuntimeError('already audited')
    manifest=json.loads((DEST/'manifest.json').read_text())
    verify_manifest(manifest)
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    assert tasks==normalize(tasks_for())
    models,candidate,pooled,stats=train()
    assert stats==manifest['source']
    assert all(joblib.hash(models[name])==manifest['controller_object_hash'][name]
               for name in MODEL_NAMES)
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,counts=freeze_choices(tasks,wide,records,models,candidate,pooled)
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        assert normalize(value)==json.loads((DEST/name).read_text())
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[k]==manifest['cost'][k] for k in stable)
    assert counts==manifest['candidate_scores']
    outcomes,checked=outcomes_for(tasks,wide,records)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['manifest_sha256']==sha(DEST/'manifest.json')
    assert saved['tasks']==outcomes
    assert saved['summary']==summarize(outcomes,checked)
    result={'passed':True,'tasks_rebuilt':len(tasks),
            'source_action_rows_rechecked':stats['early_tasks']+
                                           stats['added_mixed_tasks'],
            'predicted_output_cells_rechecked':cost['predicted_output_cells'],
            'candidate_labels_rechecked':checked,
            'candidate_scores_rechecked':counts}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
