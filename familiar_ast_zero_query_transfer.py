"""Fresh zero-query transfer of familiar-AST candidate ranker checkpoints."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from wide_candidate_reranker_development import features
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from pooled_zero_query_reranker_development import MODELS as POOLED_MODELS
from familiar_ast_zero_query_development import (MODELS, FIRST, SECOND,
                                                 arrays)
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST=ROOT/'runs/familiar-ast-zero-query-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-familiar-ast-zero-query-transfer.md'
SCRIPT=ROOT/'familiar_ast_zero_query_transfer.py'
SEEDS=tuple(range(903800,903824))
NAMES=('e0','ab','pooled','early','later','scrambled','duplicate')
MODEL_NAMES=('early','later','scrambled','duplicate')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(obj):
    return json.loads(json.dumps(obj,ensure_ascii=False))


def tasks_for():
    return [{**task,'seed':seed} for seed in SEEDS for task in
            random_bank(seed,8,('ast_transition',),visible=1,hidden=23)]


def public_run(tasks):
    prior=previous.SEEDS
    previous.SEEDS=SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS=prior


def models_for():
    models={name:joblib.load(MODELS/f'{name}.joblib') for name in MODEL_NAMES}
    models['ab']=joblib.load(SHIFTED_MODELS/'ab_top100.joblib')
    models['pooled']=joblib.load(POOLED_MODELS/'pooled_equal.joblib')
    return models


def freeze_choices(tasks,wide,records,models):
    scores={name:0 for name in models}
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        old=rec['orders']['old']
        n=min(100,len(old))
        x=features(task,pool,rec,n)
        choices={'e0':rec['orders']['e0'][0]}
        for name,model in models.items():
            p=model.predict_proba(x)[:,1]
            choices[name]=old[max(range(n),key=lambda i:(float(p[i]),-i))]
            scores[name]+=n
        rec['familiar_zero_choices']=choices
    return records,scores


def manifest_for(scores,cost):
    return {'protocol_sha256':sha(PROTOCOL),'script_sha256':sha(SCRIPT),
            'source_audit_sha256':[sha(p/'audit.json') for p in FIRST+(SECOND,)],
            'source_development_sha256':sha(ROOT/'analysis/familiar-ast-zero-query-development-20260918.json'),
            'model_sha256':{name:sha(MODELS/f'{name}.joblib')
                            for name in MODEL_NAMES},
            'shifted_ab_sha256':sha(SHIFTED_MODELS/'ab_top100.joblib'),
            'pooled_sha256':sha(POOLED_MODELS/'pooled_equal.joblib'),
            'seeds':SEEDS,'tasks':192,'candidate_scores':scores,'cost':cost,
            'frozen_sha256':{name:sha(DEST/name) for name in
                             ('sealed_bank.json','base_pools.json',
                              'ast_wide_pools.json','predicted_probe_outputs.json',
                              'frozen_records.json','frozen_allocations.json',
                              'frozen_forecasts.json')}}


def prepare():
    if DEST.exists():
        raise RuntimeError('run exists')
    assert all(json.loads((p/'audit.json').read_text())['passed']
               for p in FIRST+(SECOND,))
    models=models_for()
    tasks=tasks_for()
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,scores=freeze_choices(tasks,wide,records,models)
    DEST.mkdir(parents=True)
    for name,value in (('sealed_bank.json',tasks),('base_pools.json',base),
                       ('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        write_json(DEST/name,value)
    write_json(DEST/'manifest.json',manifest_for(scores,cost))
    print(json.dumps({'status':'frozen','tasks':len(tasks),
                      'candidate_scores':scores,
                      'predicted_output_cells':cost['predicted_output_cells']},
                     indent=2))


def outcomes_for(tasks,wide,records):
    outcomes=[]
    checked=0
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        assert rec['id']==task['id'] and digest(pool)==rec['pool_sha256']
        label=[int(bool(evaluate_program(row['program'],task['hidden'][8:])))
               for row in pool]
        checked+=len(label)
        outcomes.append({'id':task['id'],'seed':task['seed'],
                         'full_reachable':int(any(label)),
                         'top100_reachable':int(any(label[i] for i in
                              rec['orders']['old'][:100])),
                         'labels':{name:label[index] for name,index in
                                   rec['familiar_zero_choices'].items()}})
    return outcomes,checked


def contrast(banks,a,b):
    d=[bank[a]-bank[b] for bank in banks]
    return {'gain':sum(d),'positive_banks':sum(v>0 for v in d),
            'losing_banks':sum(v<0 for v in d),
            'interval':interval(d),'bank_differences':d}


def summarize(outcomes,checked):
    banks=[]
    for seed in SEEDS:
        group=[r for r in outcomes if r['seed']==seed]
        banks.append({'seed':seed,
          'full_reachable':sum(r['full_reachable'] for r in group),
          'top100_reachable':sum(r['top100_reachable'] for r in group),
          **{name:sum(r['labels'][name] for r in group) for name in NAMES}})
    totals={name:sum(b[name] for b in banks)
            for name in banks[0] if name!='seed'}
    pairs=(('early','e0'),('early','pooled'),('later','early'),
           ('later','scrambled'),('later','duplicate'),('later','pooled'))
    comparisons={f'{a}_minus_{b}':contrast(banks,a,b) for a,b in pairs}
    component=[comparisons[f'early_minus_{name}'] for name in ('e0','pooled')]
    incremental=[comparisons[f'later_minus_{name}']
                 for name in ('early','scrambled','duplicate')]
    gates={'component':all(c['gain']>=20 and c['positive_banks']>=12 and
                           c['interval'][0]>0 for c in component),
           'incremental_evaluator':all(c['gain']>=5 and c['interval'][0]>0
                                       for c in incremental) and
                                    incremental[0]['positive_banks']>=8}
    return {'tasks':len(outcomes),'output_calls':0,
            'candidate_labels_checked':checked,'totals':totals,
            'comparisons':comparisons,'gates':gates,'banks':banks}


def verify_manifest(m):
    assert m['protocol_sha256']==sha(PROTOCOL)
    assert m['script_sha256']==sha(SCRIPT)
    assert m['source_audit_sha256']==[sha(p/'audit.json') for p in FIRST+(SECOND,)]
    assert m['source_development_sha256']==sha(ROOT/'analysis/familiar-ast-zero-query-development-20260918.json')
    assert m['seeds']==list(SEEDS)
    assert all(m['model_sha256'][name]==sha(MODELS/f'{name}.joblib')
               for name in MODEL_NAMES)
    assert m['shifted_ab_sha256']==sha(SHIFTED_MODELS/'ab_top100.joblib')
    assert m['pooled_sha256']==sha(POOLED_MODELS/'pooled_equal.joblib')
    assert all(m['frozen_sha256'][name]==sha(DEST/name)
               for name in m['frozen_sha256'])


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
    m=json.loads((DEST/'manifest.json').read_text())
    verify_manifest(m)
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    assert tasks==normalize(tasks_for())
    a=arrays(FIRST);b=arrays((SECOND,))
    x=np.r_[a['x'],b['x']];y=np.r_[a['y'],b['y']]
    rng=np.random.default_rng(904220)
    scrambled=b['y'].copy()
    for group in b['groups']:
        scrambled[group]=rng.permutation(scrambled[group])
    retrained={'early':model_for(15).fit(a['x'],a['y']),
        'later':model_for(15).fit(x,y),
        'scrambled':model_for(15).fit(x,np.r_[a['y'],scrambled]),
        'duplicate':model_for(15).fit(
            np.r_[a['x'],a['x'][:len(b['x'])]],
            np.r_[a['y'],a['y'][:len(b['y'])]])}
    assert all(joblib.hash(retrained[name])==
               joblib.hash(joblib.load(MODELS/f'{name}.joblib'))
               for name in MODEL_NAMES)
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,scores=freeze_choices(tasks,wide,records,models_for())
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        assert normalize(value)==json.loads((DEST/name).read_text())
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[k]==m['cost'][k] for k in stable)
    assert scores==m['candidate_scores']
    outcomes,checked=outcomes_for(tasks,wide,records)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['manifest_sha256']==sha(DEST/'manifest.json')
    assert saved['tasks']==outcomes
    assert saved['summary']==summarize(outcomes,checked)
    result={'passed':True,'tasks_rebuilt':len(tasks),
            'source_candidate_labels_rechecked':len(y),
            'predicted_output_cells_rechecked':cost['predicted_output_cells'],
            'target_candidate_labels_rechecked':checked,
            'candidate_scores_rechecked':scores}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
