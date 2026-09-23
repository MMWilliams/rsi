"""Fresh mixed-bank test of zero-query evaluator integration and controller feedback."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank, shifted_ast_bank
from wide_candidate_reranker_development import features
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from pooled_zero_query_reranker_development import MODELS as POOLED_MODELS
from zero_query_router_development import public_row, rows_for
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST=ROOT/'runs/zero-query-mixed-integration-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-zero-query-mixed-integration-transfer.md'
SCRIPT=ROOT/'zero_query_mixed_integration_transfer.py'
SOURCE=(ROOT/'runs/zero-query-shifted-feedback-transfer-20260918',
        ROOT/'runs/combined-ranker-query-transfer-20260918')
MIXED_SOURCE=ROOT/'runs/specialist-applicability-transfer-20260918'
SEEDS=tuple(range(903600,903624))
THRESHOLD=.6
MODEL_NAMES=('visible_early','visible_later','visible_scrambled',
             'visible_duplicate','effect_early','effect_later',
             'effect_scrambled','effect_duplicate')
NAMES=('e0','ab','pooled','visible_early','visible_later',
       'visible_scrambled','visible_duplicate','effect_early',
       'effect_later','effect_scrambled','effect_duplicate','type_oracle')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(obj):
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


def fit_visible(rows):
    x=np.asarray([r['features'] for r in rows],np.float32)
    y=np.asarray([r['domain']=='shifted' for r in rows],int)
    return HistGradientBoostingClassifier(max_depth=3,max_iter=70,
        learning_rate=.05,min_samples_leaf=16,l2_regularization=5,
        random_state=221).fit(x,y)


def fit_effect(rows):
    x=np.asarray([r['features'] for r in rows],np.float32)
    y=np.asarray([r['effect'] for r in rows],float)
    return HistGradientBoostingRegressor(max_depth=3,max_iter=70,
        learning_rate=.05,min_samples_leaf=16,l2_regularization=5,
        random_state=221).fit(x,y)


def train_controllers():
    assert all(json.loads((p/'audit.json').read_text())['passed']
               for p in SOURCE+(MIXED_SOURCE,))
    candidate_models={name:joblib.load(SHIFTED_MODELS/f'{name}_top100.joblib')
                      for name in ('a','ab')}
    source=[r for p in SOURCE for r in rows_for(p,candidate_models)]
    mixed=rows_for(MIXED_SOURCE,candidate_models)
    assert len(source)==288 and len(mixed)==192
    rng=np.random.default_rng(903822)
    scrambled_domain=[]
    scrambled_effect=[]
    for seed in sorted({r['seed'] for r in mixed}):
        group=[r for r in mixed if r['seed']==seed]
        domain=rng.permutation([r['domain'] for r in group])
        effect=rng.permutation([r['effect'] for r in group])
        scrambled_domain.extend([{**r,'domain':str(v)}
                                 for r,v in zip(group,domain)])
        scrambled_effect.extend([{**r,'effect':int(v)}
                                 for r,v in zip(group,effect)])
    repeated=[]
    for domain in ('familiar','shifted'):
        group=[r for r in source if r['domain']==domain]
        repeated.extend([group[i] for i in rng.choice(len(group),96,replace=True)])
    training={'early':source,'later':source+mixed,
              'visible_scrambled':source+scrambled_domain,
              'effect_scrambled':source+scrambled_effect,
              'duplicate':source+repeated}
    models={'visible_early':fit_visible(training['early']),
            'visible_later':fit_visible(training['later']),
            'visible_scrambled':fit_visible(training['visible_scrambled']),
            'visible_duplicate':fit_visible(training['duplicate']),
            'effect_early':fit_effect(training['early']),
            'effect_later':fit_effect(training['later']),
            'effect_scrambled':fit_effect(training['effect_scrambled']),
            'effect_duplicate':fit_effect(training['duplicate'])}
    stats={'early_tasks':len(source),'added_mixed_tasks':len(mixed),
           'early_shifted':sum(r['domain']=='shifted' for r in source),
           'early_familiar':sum(r['domain']=='familiar' for r in source),
           'mixed_positive_effects':sum(r['effect']>0 for r in mixed),
           'mixed_negative_effects':sum(r['effect']<0 for r in mixed),
           'mixed_zero_effects':sum(r['effect']==0 for r in mixed),
           'duplicate_added_rows':len(repeated)}
    return models,candidate_models,stats


def freeze_choices(tasks,wide,records,controllers,candidate_models):
    pooled=joblib.load(POOLED_MODELS/'pooled_equal.joblib')
    scores={'a':0,'ab':0,'pooled':0}
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        public=public_row(task,rec,pool,candidate_models)
        x=np.asarray([public['features']],np.float32)
        prob={name:float(controllers[name].predict_proba(x)[0,1])
              for name in MODEL_NAMES if name.startswith('visible_')}
        effect={name:float(controllers[name].predict(x)[0])
                for name in MODEL_NAMES if name.startswith('effect_')}
        old=rec['orders']['old']
        n=min(100,len(old))
        feat=features(task,pool,rec,n)
        p=pooled.predict_proba(feat)[:,1]
        pooled_index=old[max(range(n),key=lambda i:(float(p[i]),-i))]
        base=public['choices']['e0']
        special=public['choices']['ab']
        choices={'e0':base,'ab':special,'pooled':pooled_index,
                 'type_oracle':special if task['family']=='shifted_ast' else base}
        choices.update({name:special if value>=THRESHOLD else base
                        for name,value in prob.items()})
        choices.update({name:special if value>0 else base
                        for name,value in effect.items()})
        assert set(choices)==set(NAMES)
        rec['zero_route_features']=public['features']
        rec['zero_route_forecasts']={**prob,**effect}
        rec['zero_route_choices']=choices
        scores['a']+=public['candidate_scores']['a']
        scores['ab']+=public['candidate_scores']['ab']
        scores['pooled']+=n
    return records,scores


def manifest_for(models,stats,cost,scores):
    return {'protocol_sha256':sha(PROTOCOL),'script_sha256':sha(SCRIPT),
            'source_audit_sha256':[sha(p/'audit.json') for p in SOURCE+(MIXED_SOURCE,)],
            'candidate_model_sha256':{name:sha(SHIFTED_MODELS/f'{name}_top100.joblib')
                                      for name in ('a','ab')},
            'pooled_model_sha256':sha(POOLED_MODELS/'pooled_equal.joblib'),
            'controller_model_sha256':{name:sha(DEST/f'{name}.joblib')
                                       for name in MODEL_NAMES},
            'controller_object_hash':{name:joblib.hash(models[name])
                                      for name in MODEL_NAMES},
            'seeds':SEEDS,'tasks':192,'threshold':THRESHOLD,
            'source':stats,'candidate_scores':scores,'cost':cost,
            'frozen_sha256':{name:sha(DEST/name) for name in
                             ('sealed_bank.json','base_pools.json',
                              'ast_wide_pools.json','predicted_probe_outputs.json',
                              'frozen_records.json','frozen_allocations.json',
                              'frozen_forecasts.json')}}


def prepare():
    if DEST.exists():
        raise RuntimeError('run exists')
    models,candidate_models,stats=train_controllers()
    tasks=tasks_for()
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,scores=freeze_choices(tasks,wide,records,models,candidate_models)
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
    manifest=manifest_for(models,stats,cost,scores)
    write_json(DEST/'manifest.json',manifest)
    print(json.dumps({'status':'frozen','tasks':len(tasks),
                      'source':stats,'candidate_scores':scores,
                      'predicted_output_cells':cost['predicted_output_cells']},
                     indent=2))


def outcomes_for(tasks,wide,records):
    result=[]
    checked=0
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        assert rec['id']==task['id'] and digest(pool)==rec['pool_sha256']
        label=[int(bool(evaluate_program(row['program'],task['hidden'][8:])))
               for row in pool]
        checked+=len(label)
        result.append({'id':task['id'],'seed':task['seed'],
                       'domain':'shifted' if task['family']=='shifted_ast'
                       else 'familiar',
                       'full_reachable':int(any(label)),
                       'top100_reachable':int(any(label[i]
                           for i in rec['orders']['old'][:100])),
                       'labels':{name:label[index] for name,index in
                                 rec['zero_route_choices'].items()}})
    return result,checked


def contrast(banks,a,b):
    d=[row[a]-row[b] for row in banks]
    return {'gain':sum(d),'positive_banks':sum(x>0 for x in d),
            'losing_banks':sum(x<0 for x in d),
            'interval':interval(d),'bank_differences':d}


def summarize(outcomes,checked):
    banks=[]
    for seed in SEEDS:
        group=[r for r in outcomes if r['seed']==seed]
        bank={'seed':seed,'full_reachable':sum(r['full_reachable'] for r in group),
              'top100_reachable':sum(r['top100_reachable'] for r in group)}
        for name in NAMES:
            bank[name]=sum(r['labels'][name] for r in group)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(r['labels'][name] for r in group
                                         if r['domain']==domain)
        banks.append(bank)
    totals={name:sum(b[name] for b in banks)
            for name in banks[0] if name!='seed'}
    pairs=(('visible_later','ab'),('visible_later','e0'),
           ('visible_later','visible_early'),
           ('visible_later','visible_scrambled'),
           ('visible_later','visible_duplicate'),
           ('effect_later','effect_early'),
           ('effect_later','effect_scrambled'),
           ('effect_later','effect_duplicate'),
           ('effect_later','ab'),('pooled','ab'))
    contrasts={f'{a}_minus_{b}':contrast(banks,a,b) for a,b in pairs}
    route=contrasts['visible_later_minus_ab']
    integration=(route['gain']>=5 and route['positive_banks']>=12 and
                 route['interval'][0]>0 and
                 totals['visible_later_familiar']>=totals['e0_familiar']-2 and
                 totals['visible_later_shifted']>=totals['ab_shifted']-8)
    growth=[contrasts[f'effect_later_minus_{name}']
            for name in ('effect_early','effect_scrambled','effect_duplicate')]
    improver=(all(c['gain']>=5 and c['interval'][0]>0 for c in growth) and
              growth[0]['positive_banks']>=8)
    return {'tasks':len(outcomes),'output_calls':0,
            'candidate_labels_checked':checked,'totals':totals,
            'contrasts':contrasts,
            'gates':{'integration':integration,'improver_growth':improver},
            'banks':banks}


def verify_manifest(manifest):
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['script_sha256']==sha(SCRIPT)
    assert manifest['source_audit_sha256']==[
        sha(p/'audit.json') for p in SOURCE+(MIXED_SOURCE,)]
    assert manifest['seeds']==list(SEEDS) and manifest['threshold']==THRESHOLD
    assert all(manifest['candidate_model_sha256'][name]==
        sha(SHIFTED_MODELS/f'{name}_top100.joblib') for name in ('a','ab'))
    assert manifest['pooled_model_sha256']==sha(POOLED_MODELS/'pooled_equal.joblib')
    assert all(manifest['controller_model_sha256'][name]==sha(DEST/f'{name}.joblib')
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
    assert tasks==normalized(tasks_for())
    models,candidate_models,stats=train_controllers()
    assert stats==manifest['source']
    assert all(joblib.hash(models[name])==
               manifest['controller_object_hash'][name] for name in MODEL_NAMES)
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,scores=freeze_choices(tasks,wide,records,models,candidate_models)
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        assert normalized(value)==json.loads((DEST/name).read_text())
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[k]==manifest['cost'][k] for k in stable)
    assert scores==manifest['candidate_scores']
    outcomes,checked=outcomes_for(tasks,wide,records)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['manifest_sha256']==sha(DEST/'manifest.json')
    assert saved['tasks']==outcomes
    assert saved['summary']==summarize(outcomes,checked)
    result={'passed':True,'tasks_rebuilt':len(tasks),
            'source_effect_rows_rechecked':stats['early_tasks']+
                                             stats['added_mixed_tasks'],
            'predicted_output_cells_rechecked':cost['predicted_output_cells'],
            'candidate_labels_rechecked':checked,
            'candidate_scores_rechecked':scores}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
