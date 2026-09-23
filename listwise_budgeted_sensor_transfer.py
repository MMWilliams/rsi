"""Fresh frozen test of feedback-trained sensor allocation after listwise ranking."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter,defaultdict

import joblib
import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank,shifted_ast_bank
from dual_specialist_seed_evaluator import load_models,FAMILIAR,SHIFTED
from wide_candidate_reranker_development import features
from specialist_applicability_development import pair_features
from task_listwise_top200_transfer import predict_listwise,TRAINED
from listwise_sensor_allocator_development import fit,predict,select
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST=ROOT/'runs/listwise-budgeted-sensor-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-listwise-budgeted-sensor-transfer.md'
SCRIPT=ROOT/'listwise_budgeted_sensor_transfer.py'
SOURCE=ROOT/'analysis/listwise-sensor-edit-source-20260918.json'
ADDED=ROOT/'analysis/listwise-sensor-edit-diagnostic-20260918.json'
LISTWISE=TRAINED/'later_listwise.joblib'
SEEDS=tuple(range(905700,905724))
LEARNED=('early_logistic','early_hgb','later_logistic','later_hgb',
         'scrambled_hgb','duplicate_hgb')
NAMES=('none','early_logistic','early_hgb','later_logistic','later_hgb',
       'scrambled_hgb','duplicate_hgb','probe_entropy','low_margin',
       'disagreement','random','all_query','oracle_four')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value):return json.loads(json.dumps(value,ensure_ascii=False))


def tasks_for():
    tasks=[]
    for seed in SEEDS:
        familiar=random_bank(seed,4,('ast_transition',),visible=1,hidden=23)
        shifted=shifted_ast_bank(seed+100000,4,visible=1,hidden=23)
        for a,b in zip(familiar,shifted):
            tasks.extend(({**a,'seed':seed},{**b,'seed':seed}))
    return tasks


def public_run(tasks):
    old=previous.SEEDS
    previous.SEEDS=SEEDS
    try:return previous.public_run(tasks)
    finally:previous.SEEDS=old


def source_models():
    early=json.loads(SOURCE.read_text())['rows']
    added=json.loads(ADDED.read_text())['rows']
    assert len(early)==192 and len(added)==384
    rng=np.random.default_rng(905699)
    scrambled=[]
    for seed in sorted({r['seed'] for r in added}):
        group=[r for r in added if r['seed']==seed]
        perm=rng.permutation([r['listwise_query_effect'] for r in group])
        scrambled.extend([{**r,'listwise_query_effect':int(effect)}
                          for r,effect in zip(group,perm)])
    duplicate=[early[i] for i in rng.choice(len(early),len(added),replace=True)]
    models={'early_logistic':fit(early,'logistic'),
            'early_hgb':fit(early,'hgb'),
            'later_logistic':fit(early+added,'logistic'),
            'later_hgb':fit(early+added,'hgb'),
            'scrambled_hgb':fit(early+scrambled,'hgb'),
            'duplicate_hgb':fit(early+duplicate,'hgb')}
    stats={'early_tasks':len(early),'added_tasks':len(added),
           'early_positive_effects':sum(r['listwise_query_effect']>0 for r in early),
           'added_positive_effects':sum(r['listwise_query_effect']>0 for r in added),
           'scrambled_positive_effects':sum(r['listwise_query_effect']>0
                                            for r in scrambled),
           'duplicate_positive_effects':sum(r['listwise_query_effect']>0
                                            for r in duplicate)}
    return models,stats


def public_rows(tasks,wide,matrix,records,specialists,listwise):
    started=time.perf_counter()
    rows=[]
    for task,rec in zip(tasks,records):
        key=task['id'];pool=wide[key]
        old=rec['orders']['old'][:200];n=len(old)
        structural=features(task,pool,rec,n)
        pf=specialists['familiar'].predict_proba(structural)[:,1]
        ps=specialists['shifted'].predict_proba(structural)[:,1]
        scores=np.asarray(rec['old_scores'],float)
        std=max(float(scores.std()),.05)
        meta=np.stack((pf,ps,np.maximum(pf,ps),np.abs(pf-ps),pf*ps,
            (scores[old]-scores[old[0]])/std,np.arange(n)/100.),
            axis=1).astype(np.float32)
        logit=predict_listwise(listwise,np.c_[structural,meta].astype(np.float32))
        order_local=sorted(range(n),key=lambda i:(-float(logit[i]),i))
        rank_order=[old[i] for i in order_local]
        f=int(np.argmax(pf));s=int(np.argmax(ps))
        dual=old[s if ps[s]>pf[f] else f]
        top_logit=sorted((float(v) for v in logit),reverse=True)
        probe=rec['probe'];outputs=matrix[key]
        partitions=Counter(str(outputs[index][probe]) for index in old)
        probs=np.asarray(list(partitions.values()),float)/n
        public=pair_features(task['visible'][0])+[
            n/200.,len(pool)/512.,std,float(pf[f]),float(ps[s]),
            float(ps[s]-pf[f]),float(logit.max()),float(logit.std()),
            float(top_logit[0]-top_logit[1]) if n>1 else 0.,
            float(dual==rank_order[0]),
            float(-(probs*np.log(np.maximum(probs,1e-12))).sum()),
            len(partitions)/n]
        rows.append({'id':key,'seed':task['seed'],'probe':probe,
            'pool_sha256':digest(pool),'rank_order':rank_order,
            'public_features':public,'candidate_scores':3*n})
    return rows,time.perf_counter()-started


def allocations(rows,models):
    out={'none':[],'all_query':list(range(len(rows)))}
    for name,model in models.items():out[name]=select(rows,predict(model,rows))
    features=np.asarray([r['public_features'] for r in rows],float)
    out['probe_entropy']=select(rows,features[:,-2])
    out['low_margin']=select(rows,-features[:,-4])
    out['disagreement']=select(rows,1-features[:,-3])
    out['random']=select(rows,np.random.default_rng(905698).random(len(rows)))
    return {name:sorted(ids) for name,ids in out.items()}


def manifest():
    files=('sealed_bank.json','base_pools.json','ast_wide_pools.json',
           'predicted_probe_outputs.json','frozen_records.json',
           'public_rows.json','allocations.json')
    return {'protocol_sha256':sha(PROTOCOL),'script_sha256':sha(SCRIPT),
            'source_sha256':sha(SOURCE),'added_sha256':sha(ADDED),
            'listwise_sha256':sha(LISTWISE),
            'specialist_sha256':{'familiar':sha(FAMILIAR),'shifted':sha(SHIFTED)},
            'model_sha256':{name:sha(DEST/f'{name}.joblib') for name in LEARNED},
            'seeds':list(SEEDS),'tasks':192,
            'frozen_sha256':{name:sha(DEST/name) for name in files}}


def verify_manifest():
    saved=json.loads((DEST/'manifest.json').read_text())
    expected=manifest()
    assert all(saved[key]==value for key,value in expected.items())
    return saved


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    models,stats=source_models()
    tasks=tasks_for()
    base,wide,matrix,records,_,_,cost=public_run(tasks)
    # The host's common generator records the true probe output; remove it
    # before feature construction, allocation or freezing public records.
    public_records=[{k:v for k,v in rec.items() if k!='probe_output'}
                    for rec in records]
    rows,decision_seconds=public_rows(tasks,wide,matrix,public_records,
                                       load_models(),joblib.load(LISTWISE))
    selected=allocations(rows,models)
    assert all(len(selected[name])==96 for name in selected
               if name not in ('none','all_query'))
    DEST.mkdir(parents=True)
    for name,model in models.items():joblib.dump(model,DEST/f'{name}.joblib',compress=3)
    for name,value in (('sealed_bank.json',tasks),('base_pools.json',base),
        ('ast_wide_pools.json',wide),('predicted_probe_outputs.json',matrix),
        ('frozen_records.json',public_records),('public_rows.json',rows),
        ('allocations.json',selected)):
        write_json(DEST/name,value)
    write_json(DEST/'manifest.json',{**manifest(),'source':stats,
        'generation_cost':cost,'public_decision_wall_seconds':decision_seconds,
        'output_calls_per_budgeted_arm':96,
        'measurement_output_accesses_after_freeze':192})
    print(json.dumps({'frozen':True,'tasks':len(tasks),'source':stats,
        'generation_cost':cost,'public_decision_wall_seconds':decision_seconds,
        'selection_count':{name:len(ids) for name,ids in selected.items()}},
        indent=2))


def outcomes_for(tasks,wide,matrix,rows):
    outcome=[];checked=0
    for task,row in zip(tasks,rows):
        key=task['id'];pool=wide[key]
        assert row['id']==key and digest(pool)==row['pool_sha256']
        labels=[int(bool(evaluate_program(item['program'],task['hidden'][8:])))
                for item in pool]
        checked+=len(labels)
        order=row['rank_order'];probe=row['probe'];truth=task['hidden'][probe][1]
        surviving=[i for i in order if matrix[key][i][probe]==truth]
        if not surviving:surviving=order
        zero=labels[order[0]];one=labels[surviving[0]]
        outcome.append({'id':key,'seed':task['seed'],
            'domain':'shifted' if task['family']=='shifted_ast' else 'familiar',
            'probe_output':truth,'zero':zero,'one':one,'effect':one-zero,
            'top200_reachable':int(any(labels[i] for i in order))})
    return outcome,checked


def contrast(banks,a,b):
    d=[row[a]-row[b] for row in banks]
    return {'gain':sum(d),'positive_banks':sum(v>0 for v in d),
            'negative_banks':sum(v<0 for v in d),'interval':interval(d),
            'bank_differences':d}


def summarize(outcome,rows,alloc,checked):
    policies={**alloc}
    policies['oracle_four']=select(rows,np.asarray([r['effect'] for r in outcome]))
    banks=[]
    for seed in SEEDS:
        ids=[i for i,r in enumerate(outcome) if r['seed']==seed]
        bank={'seed':seed,'reachable':sum(outcome[i]['top200_reachable'] for i in ids)}
        for name in NAMES:
            chosen=set(policies[name])
            bank[name]=sum(outcome[i]['one' if i in chosen else 'zero'] for i in ids)
            bank[name+'_positive_effects']=sum(outcome[i]['effect']>0
                                                for i in ids if i in chosen)
            bank[name+'_negative_effects']=sum(outcome[i]['effect']<0
                                                for i in ids if i in chosen)
            for domain in ('familiar','shifted'):
                bank[name+'_'+domain]=sum(outcome[i]['one' if i in chosen
                                                   else 'zero'] for i in ids
                                          if outcome[i]['domain']==domain)
        banks.append(bank)
    totals={key:sum(b[key] for b in banks) for key in banks[0] if key!='seed'}
    comparisons={f'later_logistic_minus_{name}':contrast(banks,'later_logistic',name)
                 for name in ('none','early_logistic','scrambled_hgb',
                              'duplicate_hgb','probe_entropy','low_margin','random')}
    integration=comparisons['later_logistic_minus_none']
    early=comparisons['later_logistic_minus_early_logistic']
    entropy=comparisons['later_logistic_minus_probe_entropy']
    sensor=(integration['gain']>=6 and integration['interval'][0]>0 and
            integration['positive_banks']>=8)
    incremental=(all(comparisons[f'later_logistic_minus_{name}']['gain']>=4
                     for name in ('early_logistic','scrambled_hgb','duplicate_hgb'))
                 and early['interval'][0]>0 and early['positive_banks']>=8)
    fixed=(all(comparisons[f'later_logistic_minus_{name}']['gain']>=4
               for name in ('probe_entropy','low_margin','random'))
           and entropy['interval'][0]>0 and entropy['positive_banks']>=8)
    return {'tasks':len(outcome),'candidate_labels_checked':checked,
        'measurement_output_accesses':len(outcome),'output_calls_budgeted':96,
        'candidate_scores_common':sum(r['candidate_scores'] for r in rows),
        'total_positive_query_effects':sum(r['effect']>0 for r in outcome),
        'total_negative_query_effects':sum(r['effect']<0 for r in outcome),
        'totals':totals,'comparisons':comparisons,
        'gates':{'sensor_integration':sensor,'incremental_selector':incremental,
                 'fixed_policy':fixed},'banks':banks}


def score():
    if (DEST/'results.json').exists():raise RuntimeError('already scored')
    verify_manifest()
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    matrix=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    rows=json.loads((DEST/'public_rows.json').read_text())
    alloc=json.loads((DEST/'allocations.json').read_text())
    outcome,checked=outcomes_for(tasks,wide,matrix,rows)
    summary=summarize(outcome,rows,alloc,checked)
    write_json(DEST/'results.json',{'manifest_sha256':sha(DEST/'manifest.json'),
                                   'summary':summary,'tasks':outcome})
    print(json.dumps({k:v for k,v in summary.items() if k!='banks'},indent=2))


def audit():
    if (DEST/'audit.json').exists():raise RuntimeError('already audited')
    m=verify_manifest()
    tasks=tasks_for()
    assert normalize(tasks)==json.loads((DEST/'sealed_bank.json').read_text())
    models,stats=source_models()
    assert stats==m['source']
    saved={name:joblib.load(DEST/f'{name}.joblib') for name in LEARNED}
    base,wide,matrix,records,_,_,cost=public_run(tasks)
    public_records=[{k:v for k,v in rec.items() if k!='probe_output'}
                    for rec in records]
    rows,_=public_rows(tasks,wide,matrix,public_records,
                       load_models(),joblib.load(LISTWISE))
    x=np.asarray([r['public_features'] for r in rows],np.float32)
    for name in LEARNED:
        assert np.array_equal(models[name].predict_proba(x),
                              saved[name].predict_proba(x)),name
    alloc=allocations(rows,saved)
    for name,value in (('base_pools.json',base),('ast_wide_pools.json',wide),
        ('predicted_probe_outputs.json',matrix),
        ('frozen_records.json',public_records),('public_rows.json',rows),
        ('allocations.json',alloc)):
        assert normalize(value)==json.loads((DEST/name).read_text()),name
    stable=('base_candidates','extra_ast_candidates',
            'predicted_output_cells','e0_candidate_scores',
            'post_query_candidate_scores')
    assert all(cost[key]==m['generation_cost'][key] for key in stable)
    outcome,checked=outcomes_for(tasks,wide,matrix,rows)
    summary=summarize(outcome,rows,alloc,checked)
    saved_result=json.loads((DEST/'results.json').read_text())
    assert saved_result=={'manifest_sha256':sha(DEST/'manifest.json'),
                          'summary':summary,'tasks':outcome}
    result={'passed':True,'tasks_rebuilt':len(tasks),
        'source_models_retrained':len(models),
        'source_effect_rows_rechecked':stats['early_tasks']+stats['added_tasks'],
        'public_output_cells_rebuilt':cost['predicted_output_cells'],
        'target_forecasts_rechecked':len(tasks)*len(LEARNED),
        'exact_candidate_labels_rebuilt':checked,
        'allocations_rebuilt':{name:len(ids) for name,ids in alloc.items()}}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    {'prepare':prepare,'score':score,'audit':audit}[sys.argv[1]]()
