"""Prospective E0 query-value checkpoints on a third untouched panel."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import defaultdict

import numpy as np

from rsi.common import ROOT,write_json
import candidate_reranker_transfer as transfer
from candidate_conditioned_query_development import (PANELS,source_rows,
    features,model_rows,fit,predict,selected)
from cross_family_meta_improver_development import values
from cross_family_meta_improver_transfer import interval


DEST=ROOT/'runs/candidate-conditioned-query-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-candidate-conditioned-query-transfer.md'
SOURCE=ROOT/'runs/candidate-reranker-transfer-20260918'
DEVELOPMENT=ROOT/'analysis/candidate-conditioned-query-development-20260918.json'
QUERY_MODEL=ROOT/'runs/focused-feedback-transfer-20260918/models.json'
FROZEN=DEST/'conditioned_children.json'
REPORT=DEST/'conditioned_results.json'
SEEDS=tuple(range(902534,902546))
NAMES=('initial','later','scrambled','duplicate','old_matched',
       'conditioned_family','incumbent')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def configure():
    transfer.DEST=DEST
    transfer.PROTOCOL=PROTOCOL
    transfer.SEEDS=SEEDS


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    assert json.loads((SOURCE/'audit.json').read_text())['passed']
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANELS)
    dev=json.loads(DEVELOPMENT.read_text())
    assert dev['selected_method']=='conditioned_interaction_100'
    manifest=json.loads((SOURCE/'source_manifest.json').read_text())
    DEST.mkdir(parents=True)
    for name,expected in manifest['model_sha256'].items():
        shutil.copy2(SOURCE/f'{name}.joblib',DEST/f'{name}.joblib')
        assert sha(DEST/f'{name}.joblib')==expected
    manifest['protocol_sha256']=sha(PROTOCOL)
    manifest['replicated_from']=str(SOURCE.relative_to(ROOT))
    write_json(DEST/'source_manifest.json',manifest)
    configure();transfer.freeze_banks()


def source_tables(rows):
    first=rows[:576];second=rows[576:]
    assert len(first)==len(second)==576
    scrambled=[dict(row) for row in second]
    for family in sorted({r['family'] for r in second}):
        indexes=[i for i,r in enumerate(second) if r['family']==family]
        for target,donor in zip(indexes,indexes[-1:]+indexes[:-1]):
            scrambled[target]={**scrambled[target],'gain':second[donor]['gain']}
    return {'initial':first,'later':rows,'scrambled':first+scrambled,
            'duplicate':first+first,'old_matched':rows,
            'conditioned_family':rows}


def children_from(records,predicted):
    source,_=source_rows();tables=source_tables(source)
    target=[{'id':r['id'],'seed':r['seed'],'family':r['family'],
        'public_block':r['public_block'],'old_features':r['query_features'],
        'conditioned_features':features(r,predicted[r['id']])} for r in records]
    assert len(target)==576 and len({r['id'] for r in target})==576
    methods={'initial':'conditioned_interaction_100',
             'later':'conditioned_interaction_100',
             'scrambled':'conditioned_interaction_100',
             'duplicate':'conditioned_interaction_100',
             'old_matched':'old_family_100',
             'conditioned_family':'conditioned_family_100'}
    query=json.loads(QUERY_MODEL.read_text())['e0']
    children={};grouped=defaultdict(list)
    for row in target:grouped[row['seed']].append(row)
    assert tuple(sorted(grouped))==SEEDS and all(len(grouped[s])==48 for s in SEEDS)
    for name in NAMES:
        if name=='incumbent':model=query;method='old_family_100';count=576
        else:
            method=methods[name];model=fit(tables[name],method);count=len(tables[name])
        predictions=[];calls={}
        for seed in SEEDS:
            group=grouped[seed]
            scores=(values(model,model_rows(group,method)) if name=='incumbent'
                    else predict(model,group,method))
            predictions.extend({'id':row['id'],'value':float(value)}
                               for row,value in zip(group,scores))
            calls[str(seed)]=sorted(selected(group,scores))
            assert len(calls[str(seed)])==8
        children[name]={'method':method,'source_tasks':count,
                        'model':model,'forecasts':predictions,'calls':calls}
    return children


def freeze():
    if FROZEN.exists():raise RuntimeError('children already frozen')
    assert not (DEST/'results.json').exists(),'target labels already opened'
    assert (DEST/'frozen_records.json').exists()
    records=json.loads((DEST/'frozen_records.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    children=children_from(records,predicted)
    original=json.loads((DEST/'frozen_allocations.json').read_text())
    assert children['incumbent']['calls']==original
    files=[DEVELOPMENT,QUERY_MODEL,ROOT/'candidate_conditioned_query_development.py',
           *(p/name for p in PANELS for name in ('audit.json','results.json',
               'frozen_records.json','predicted_probe_outputs.json'))]
    manifest={'protocol_sha256':sha(PROTOCOL),
        'runner_sha256':sha(ROOT/'candidate_conditioned_query_transfer.py'),
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},
        'bank_manifest_sha256':sha(DEST/'bank_manifest.json'),
        'target_records_sha256':sha(DEST/'frozen_records.json'),
        'target_predictions_sha256':sha(DEST/'predicted_probe_outputs.json'),
        'admission_seeds':SEEDS[:6],'transfer_seeds':SEEDS[6:],
        'children':children}
    write_json(FROZEN,manifest)
    print(json.dumps({'status':'children frozen','source_tasks':
        {n:children[n]['source_tasks'] for n in NAMES},
        'calls_per_child':sum(len(v) for v in children['later']['calls'].values()),
        'frozen_sha256':sha(FROZEN)},indent=2))


def score():
    if not FROZEN.exists():raise RuntimeError('freeze children before scoring')
    configure();transfer.score_banks()


def audit_base():
    configure()
    import audit_candidate_reranker_transfer as independent
    independent.main()


def compute(frozen,outcomes):
    grouped=defaultdict(list)
    for row in outcomes:grouped[row['seed']].append(row)
    by_bank={};forecasts={}
    for name in NAMES:
        child=frozen['children'][name]
        lookup={r['id']:r['value'] for r in child['forecasts']}
        assert len(lookup)==len(outcomes)
        errors=[];selected_gain=0;hindsight=0
        for seed in SEEDS:
            group=grouped[seed];calls=set(child['calls'][str(seed)])
            assert len(group)==48 and len(calls)==8
            gains=[]
            for row in group:
                gain=row['one']['e0']-row['zero']['e0']
                gains.append(gain);errors.append((lookup[row['id']]-gain)**2)
                if row['id'] in calls:selected_gain+=gain
            hindsight+=sum(sorted(gains,reverse=True)[:8])
        forecasts[name]={'mse':sum(errors)/len(errors),
            'selected_gain':selected_gain,'unavailable_hindsight_gain':hindsight,
            'selected_regret':hindsight-selected_gain}
    for seed in SEEDS:
        group=grouped[seed];entry={}
        for name in NAMES:
            calls=set(frozen['children'][name]['calls'][str(seed)])
            entry[name]=sum((r['one'] if r['id'] in calls else r['zero'])['e0']
                            for r in group)
        entry['e0_noquery']=sum(r['zero']['e0'] for r in group)
        by_bank[str(seed)]=entry
    slices={'admission':SEEDS[:6],'transfer':SEEDS[6:],'all':SEEDS}
    totals={part:{name:sum(by_bank[str(seed)][name] for seed in seeds)
                  for name in NAMES+('e0_noquery',)}
            for part,seeds in slices.items()}
    return totals,by_bank,forecasts


def gates(totals,banks,forecasts):
    all_diffs=[banks[str(s)]['later']-banks[str(s)]['incumbent'] for s in SEEDS]
    evaluator={'gain':sum(all_diffs),'positive_banks':sum(x>0 for x in all_diffs),
        'losing_banks':sum(x<0 for x in all_diffs),
        'interval':interval(all_diffs)}
    evaluator['promote']=bool(evaluator['gain']>=8 and
        evaluator['positive_banks']>=8 and evaluator['losing_banks']<=2 and
        evaluator['interval'][0]>0 and
        forecasts['later']['mse']<forecasts['incumbent']['mse'])
    evaluator['matched_feature_advantage']=bool(
        totals['all']['later']>totals['all']['old_matched'] and
        totals['all']['later']>totals['all']['conditioned_family'])
    admission=totals['admission'];transfer=totals['transfer']
    admitted=all(admission['later']>=admission[name] for name in
                 ('initial','incumbent','old_matched'))
    diffs=[banks[str(s)]['later']-banks[str(s)]['initial'] for s in SEEDS[6:]]
    improver={'admitted':admitted,'gain':sum(diffs),
        'positive_banks':sum(x>0 for x in diffs),
        'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    improver['growth']=bool(admitted and improver['gain']>=4 and
        improver['positive_banks']>=4 and improver['interval'][0]>0 and
        all(transfer['later']>transfer[name] for name in
            ('scrambled','duplicate','old_matched','incumbent')))
    return evaluator,improver


def report():
    if REPORT.exists():raise RuntimeError('report already exists')
    assert json.loads((DEST/'audit.json').read_text())['passed']
    frozen=json.loads(FROZEN.read_text())
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert frozen['runner_sha256']==sha(ROOT/'candidate_conditioned_query_transfer.py')
    assert all(sha(ROOT/name)==expected for name,expected in
               frozen['source_sha256'].items())
    outcomes=json.loads((DEST/'results.json').read_text())['tasks']
    totals,banks,forecasts=compute(frozen,outcomes)
    evaluator,improver=gates(totals,banks,forecasts)
    output={'scores':totals,'by_bank':banks,'forecasts':forecasts,
        'evaluator_gate':evaluator,'improver_gate':improver,
        'source_tasks':{n:frozen['children'][n]['source_tasks'] for n in NAMES},
        'query_calls_per_child':len(SEEDS)*8,
        'bank_manifest':json.loads((DEST/'bank_manifest.json').read_text()),
        'base_audit':json.loads((DEST/'audit.json').read_text()),
        'frozen_sha256':sha(FROZEN),'target_results_sha256':sha(DEST/'results.json')}
    write_json(REPORT,output)
    print(json.dumps({k:v for k,v in output.items() if k not in
        ('by_bank','bank_manifest','base_audit')},indent=2))


def audit_child():
    saved=json.loads(REPORT.read_text());frozen=json.loads(FROZEN.read_text())
    assert saved['frozen_sha256']==sha(FROZEN)
    assert saved['target_results_sha256']==sha(DEST/'results.json')
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert all(sha(ROOT/name)==expected for name,expected in
               frozen['source_sha256'].items())
    records=json.loads((DEST/'frozen_records.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    rebuilt=children_from(records,predicted)
    assert rebuilt==frozen['children']
    outcomes=json.loads((DEST/'results.json').read_text())['tasks']
    scores,banks,forecasts=compute(frozen,outcomes)
    assert scores==saved['scores'] and banks==saved['by_bank']
    assert forecasts==saved['forecasts']
    e,i=gates(scores,banks,forecasts)
    assert e==saved['evaluator_gate'] and i==saved['improver_gate']
    print(json.dumps({'passed':True,'source_tasks_reconstructed':1152,
        'target_child_decisions_rechecked':len(outcomes)*len(NAMES)},indent=2))


if __name__=='__main__':
    {'prepare':prepare,'freeze':freeze,'score':score,'audit':audit_base,
     'report':report,'check':audit_child}[sys.argv[1]]()
