"""Fresh mixed-bank test of two validated candidate evaluators and effect feedback."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank,shifted_ast_bank
from dual_specialist_router_development import PANEL, VISIBLE, public_pair, rows_for
from familiar_ast_zero_query_development import MODELS as FAMILIAR_MODELS
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST=ROOT/'runs/dual-specialist-integration-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-dual-specialist-integration-transfer.md'
SCRIPT=ROOT/'dual_specialist_integration_transfer.py'
SEEDS=tuple(range(903900,903924))
MODEL_NAMES=('early','later','scrambled','duplicate','nonlinear_later')
NAMES=('e0','familiar','shifted','confidence','prior_visible',
       'early','later','scrambled','duplicate','nonlinear_later')


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


def fit_ridge(rows):
    x=np.asarray([r['features'] for r in rows],np.float32)
    y=np.asarray([r['effect'] for r in rows],float)
    scaler=StandardScaler().fit(x)
    return (scaler,Ridge(alpha=30.).fit(scaler.transform(x),y))


def predict(model,x):
    if isinstance(model,tuple):
        return model[1].predict(model[0].transform(x))
    return model.predict(x)


def train():
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANEL)
    assert json.loads((ROOT/'runs/familiar-ast-zero-query-transfer-20260918/audit.json').read_text())['passed']
    candidate={name:joblib.load(SHIFTED_MODELS/f'{name}_top100.joblib')
               for name in ('a','ab')}
    familiar=joblib.load(FAMILIAR_MODELS/'early.joblib')
    visible=joblib.load(VISIBLE)
    first=rows_for(PANEL[0],candidate,familiar,visible)
    second=rows_for(PANEL[1],candidate,familiar,visible)
    assert len(first)==len(second)==192
    rng=np.random.default_rng(904510)
    scrambled=[]
    for seed in sorted({r['seed'] for r in second}):
        group=[r for r in second if r['seed']==seed]
        perm=rng.permutation([r['effect'] for r in group])
        scrambled.extend([{**r,'effect':int(v)} for r,v in zip(group,perm)])
    repeated=[]
    for domain in ('familiar','shifted'):
        group=[r for r in first if r['domain']==domain]
        repeated.extend([group[i] for i in rng.choice(len(group),96,replace=True)])
    models={'early':fit_ridge(first),
            'later':fit_ridge(first+second),
            'scrambled':fit_ridge(first+scrambled),
            'duplicate':fit_ridge(first+repeated),
            'nonlinear_later':HistGradientBoostingRegressor(
                max_depth=3,max_iter=70,learning_rate=.05,
                min_samples_leaf=16,l2_regularization=5,
                random_state=221).fit(
                    np.asarray([r['features'] for r in first+second],np.float32),
                    np.asarray([r['effect'] for r in first+second],float))}
    stats={'early_tasks':len(first),'added_tasks':len(second),
           'duplicate_added_rows':len(repeated),
           'first_effect_positive':sum(r['effect']>0 for r in first),
           'first_effect_negative':sum(r['effect']<0 for r in first),
           'second_effect_positive':sum(r['effect']>0 for r in second),
           'second_effect_negative':sum(r['effect']<0 for r in second),
           'first_action_correct':{name:sum(r['labels'][name] for r in first)
                                   for name in ('familiar','shifted')},
           'second_action_correct':{name:sum(r['labels'][name] for r in second)
                                    for name in ('familiar','shifted')}}
    return models,candidate,familiar,visible,stats,first+second


def freeze_choices(tasks,wide,records,models,candidate,familiar,visible):
    counts={'a':0,'ab':0,'familiar':0,'controller_effect_predictions':0}
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        public=public_pair(task,rec,pool,candidate,familiar,visible)
        x=np.asarray([public['features']],np.float32)
        forecasts={name:float(predict(model,x)[0])
                   for name,model in models.items()}
        choices={'e0':rec['orders']['e0'][0],
                 **public['choices'],
                 'confidence':public['choices']['shifted']
                     if public['confidence_difference']>0 else public['choices']['familiar'],
                 'prior_visible':public['choices']['shifted']
                     if public['visible_probability']>=.6 else public['choices']['familiar']}
        choices.update({name:public['choices']['shifted'] if value>0
                        else public['choices']['familiar']
                        for name,value in forecasts.items()})
        assert set(choices)==set(NAMES)
        rec['dual_features']=public['features']
        rec['dual_confidence_difference']=public['confidence_difference']
        rec['dual_visible_probability']=public['visible_probability']
        rec['dual_effect_forecasts']=forecasts
        rec['dual_choices']=choices
        for name,value in public['candidate_scores'].items():
            counts[name]+=value
        counts['controller_effect_predictions']+=len(models)
    return records,counts


def manifest_for(models,stats,cost,counts):
    return {'protocol_sha256':sha(PROTOCOL),'script_sha256':sha(SCRIPT),
            'source_audit_sha256':[sha(p/'audit.json') for p in PANEL],
            'familiar_source_audit_sha256':sha(ROOT/'runs/familiar-ast-zero-query-transfer-20260918/audit.json'),
            'candidate_model_sha256':{name:sha(SHIFTED_MODELS/f'{name}_top100.joblib')
                                      for name in ('a','ab')},
            'familiar_model_sha256':sha(FAMILIAR_MODELS/'early.joblib'),
            'visible_model_sha256':sha(VISIBLE),
            'controller_file_sha256':{name:sha(DEST/f'{name}.joblib')
                                      for name in MODEL_NAMES},
            'seeds':SEEDS,'tasks':192,'source':stats,
            'candidate_scores':counts,'cost':cost,
            'frozen_sha256':{name:sha(DEST/name) for name in
                             ('sealed_bank.json','base_pools.json',
                              'ast_wide_pools.json','predicted_probe_outputs.json',
                              'frozen_records.json','frozen_allocations.json',
                              'frozen_forecasts.json')}}


def prepare():
    if DEST.exists():raise RuntimeError('run exists')
    models,candidate,familiar,visible,stats,_=train()
    tasks=tasks_for()
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,counts=freeze_choices(tasks,wide,records,models,candidate,familiar,visible)
    DEST.mkdir(parents=True)
    for name,model in models.items():joblib.dump(model,DEST/f'{name}.joblib',compress=3)
    for name,value in (('sealed_bank.json',tasks),('base_pools.json',base),
                       ('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        write_json(DEST/name,value)
    write_json(DEST/'manifest.json',manifest_for(models,stats,cost,counts))
    print(json.dumps({'status':'frozen','tasks':len(tasks),'source':stats,
        'candidate_scores':counts,
        'predicted_output_cells':cost['predicted_output_cells']},indent=2))


def outcomes_for(tasks,wide,records):
    outcomes=[];checked=0
    for task,rec in zip(tasks,records):
        pool=wide[task['id']]
        assert rec['id']==task['id'] and digest(pool)==rec['pool_sha256']
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:])))
                for row in pool]
        checked+=len(labels)
        outcomes.append({'id':task['id'],'seed':task['seed'],
            'domain':'shifted' if task['family']=='shifted_ast' else 'familiar',
            'full_reachable':int(any(labels)),
            'top100_reachable':int(any(labels[i] for i in
                                        rec['orders']['old'][:100])),
            'labels':{name:labels[index] for name,index in
                      rec['dual_choices'].items()}})
    return outcomes,checked


def contrast(banks,a,b):
    d=[row[a]-row[b] for row in banks]
    return {'gain':sum(d),'positive_banks':sum(v>0 for v in d),
            'losing_banks':sum(v<0 for v in d),
            'interval':interval(d),'bank_differences':d}


def summarize(outcomes,checked):
    banks=[]
    for seed in SEEDS:
        group=[r for r in outcomes if r['seed']==seed]
        bank={'seed':seed,
              'full_reachable':sum(r['full_reachable'] for r in group),
              'top100_reachable':sum(r['top100_reachable'] for r in group),
              'oracle_two':sum(max(r['labels']['familiar'],
                                    r['labels']['shifted']) for r in group)}
        for name in NAMES:
            bank[name]=sum(r['labels'][name] for r in group)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(r['labels'][name] for r in group
                                         if r['domain']==domain)
        banks.append(bank)
    totals={name:sum(b[name] for b in banks)
            for name in banks[0] if name!='seed'}
    pairs=(('confidence','familiar'),('confidence','shifted'),
           ('later','early'),('later','scrambled'),('later','duplicate'),
           ('later','confidence'),('later','familiar'),('later','shifted'))
    comparisons={f'{a}_minus_{b}':contrast(banks,a,b) for a,b in pairs}
    fixed=[comparisons[f'confidence_minus_{name}']
           for name in ('familiar','shifted')]
    integration=(all(c['gain']>=12 and c['positive_banks']>=12 and
                     c['interval'][0]>0 for c in fixed) and
                 totals['confidence_familiar']>=totals['familiar_familiar']-8 and
                 totals['confidence_shifted']>=totals['shifted_shifted']-8)
    growth=[comparisons[f'later_minus_{name}']
            for name in ('early','scrambled','duplicate','confidence')]
    improver=(all(c['gain']>=5 and c['interval'][0]>0 for c in growth) and
              growth[0]['positive_banks']>=8)
    return {'tasks':len(outcomes),'output_calls':0,
            'candidate_labels_checked':checked,'totals':totals,
            'comparisons':comparisons,
            'gates':{'integration':integration,'improver_growth':improver},
            'banks':banks}


def verify_manifest(m):
    assert m['protocol_sha256']==sha(PROTOCOL)
    assert m['script_sha256']==sha(SCRIPT)
    assert m['source_audit_sha256']==[sha(p/'audit.json') for p in PANEL]
    assert m['familiar_source_audit_sha256']==sha(ROOT/'runs/familiar-ast-zero-query-transfer-20260918/audit.json')
    assert m['seeds']==list(SEEDS)
    assert all(m['candidate_model_sha256'][name]==
        sha(SHIFTED_MODELS/f'{name}_top100.joblib') for name in ('a','ab'))
    assert m['familiar_model_sha256']==sha(FAMILIAR_MODELS/'early.joblib')
    assert m['visible_model_sha256']==sha(VISIBLE)
    assert all(m['controller_file_sha256'][name]==sha(DEST/f'{name}.joblib')
               for name in MODEL_NAMES)
    assert all(m['frozen_sha256'][name]==sha(DEST/name)
               for name in m['frozen_sha256'])


def score():
    if (DEST/'results.json').exists():raise RuntimeError('already scored')
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
    if (DEST/'audit.json').exists():raise RuntimeError('already audited')
    m=json.loads((DEST/'manifest.json').read_text())
    verify_manifest(m)
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    assert tasks==normalize(tasks_for())
    models,candidate,familiar,visible,stats,source_rows=train()
    assert stats==m['source']
    saved_models={name:joblib.load(DEST/f'{name}.joblib')
                  for name in MODEL_NAMES}
    source_x=np.asarray([r['features'] for r in source_rows],np.float32)
    for name in MODEL_NAMES:
        assert np.array_equal(predict(models[name],source_x),
                              predict(saved_models[name],source_x)),name
    base,wide,predicted,records,allocations,forecasts,cost=public_run(tasks)
    records,counts=freeze_choices(tasks,wide,records,saved_models,
                                  candidate,familiar,visible)
    target_x=np.asarray([r['dual_features'] for r in records],np.float32)
    for name in MODEL_NAMES:
        assert np.array_equal(predict(models[name],target_x),
                              predict(saved_models[name],target_x)),name
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
                       ('predicted_probe_outputs.json',predicted),
                       ('frozen_records.json',records),
                       ('frozen_allocations.json',allocations),
                       ('frozen_forecasts.json',forecasts)):
        assert normalize(value)==json.loads((DEST/name).read_text()),name
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[k]==m['cost'][k] for k in stable)
    assert counts==m['candidate_scores']
    outcomes,checked=outcomes_for(tasks,wide,records)
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['manifest_sha256']==sha(DEST/'manifest.json')
    assert saved['tasks']==outcomes
    assert saved['summary']==summarize(outcomes,checked)
    result={'passed':True,'tasks_rebuilt':len(tasks),
            'source_effect_rows_rechecked':len(source_rows),
            'source_model_predictions_rechecked':len(source_rows)*len(MODEL_NAMES),
            'target_model_predictions_rechecked':len(tasks)*len(MODEL_NAMES),
            'predicted_output_cells_rechecked':cost['predicted_output_cells'],
            'target_candidate_labels_rechecked':checked,
            'candidate_scores_rechecked':counts}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
