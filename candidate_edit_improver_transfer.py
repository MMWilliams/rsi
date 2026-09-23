"""Frozen same-base parent/child edit-effect improver on a second bank."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import fit_method,select,values
from cross_family_meta_improver_transfer import interval


RUN=ROOT/'runs/candidate-reranker-replication-20260918'
LEDGER=ROOT/'analysis/candidate-edit-effect-ledger-20260918.json'
PROTOCOL=ROOT/'EXPERIMENT-candidate-edit-improver-transfer.md'
FROZEN=RUN/'improver_frozen.json'
REPORT=RUN/'improver_results.json'
NAMES=('old','e0','e1','leaf7')
PARENTS=('initial','later','scrambled','duplicate')
SEEDS=tuple(range(902522,902534))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tables():
    ledger=json.loads(LEDGER.read_text())
    assert ledger['tasks']==576
    rows=ledger['rows'];first=rows[:288];later=rows[288:]
    assert len({r['seed'] for r in first})==len({r['seed'] for r in later})==6
    scrambled=[dict(r) for r in later]
    for family in sorted({r['family'] for r in later}):
        indexes=[i for i,r in enumerate(later) if r['family']==family]
        for target,donor in zip(indexes,indexes[-1:]+indexes[:-1]):
            scrambled[target]={**scrambled[target],
                'zero':later[donor]['zero'],'one':later[donor]['one']}
    return {'initial':first,'later':rows,
            'scrambled':first+scrambled,'duplicate':first+first}


def route(rows):
    families=sorted({r['family'] for r in rows});result={}
    for family in families:
        group=[r for r in rows if r['family']==family]
        counts={name:sum(r['zero'][name] for r in group) for name in NAMES}
        eligible=[name for name in NAMES if name=='e1' or
                  counts[name]>=counts['e1']+2]
        result[family]=max(eligible,key=lambda name:(counts[name],-NAMES.index(name)))
    return result


def training_rows(rows,routes):
    return [{'id':r['id'],'seed':r['seed'],'public_block':r['public_block'],
             'features':r['public_query_features'],
             'gain':r['one'][routes[r['family']]]-r['zero'][routes[r['family']]]}
            for r in rows]


def freeze():
    if FROZEN.exists():raise RuntimeError('already frozen')
    assert not (RUN/'results.json').exists(), 'final labels already scored'
    assert all((RUN/name).exists() for name in ('bank_manifest.json','frozen_records.json',
        'frozen_allocations.json','sealed_bank.json'))
    records=json.loads((RUN/'frozen_records.json').read_text())
    tables=source_tables();children={};grouped=defaultdict(list)
    for record in records:grouped[record['seed']].append(record)
    assert tuple(sorted(grouped))==SEEDS and all(len(grouped[s])==48 for s in SEEDS)
    for parent in PARENTS:
        source=tables[parent];routes=route(source)
        model=fit_method(training_rows(source,routes),'family_100')
        calls={}
        for seed in SEEDS:
            bank=[{'id':r['id'],'seed':seed,'public_block':r['public_block'],
                   'features':r['query_features']} for r in grouped[seed]]
            calls[str(seed)]=sorted(select(bank,model))
            assert len(calls[str(seed)])==8
        children[parent]={'source_tasks':len(source),'source_task_ids':
            [r['id'] for r in source],'route':routes,'query_model':model,'calls':calls}
    manifest={'protocol_sha256':sha(PROTOCOL),'runner_sha256':sha(ROOT/
        'candidate_edit_improver_transfer.py'),'ledger_sha256':sha(LEDGER),
        'target_records_sha256':sha(RUN/'frozen_records.json'),
        'target_bank_manifest_sha256':sha(RUN/'bank_manifest.json'),
        'admission_seeds':SEEDS[:6],'transfer_seeds':SEEDS[6:],
        'children':children}
    write_json(FROZEN,manifest)
    print(json.dumps({'status':'children frozen','routes':{p:children[p]['route']
        for p in PARENTS},'calls_by_parent':{p:sum(len(v) for v in
        children[p]['calls'].values()) for p in PARENTS}},indent=2))


def compute(frozen,outcomes,baseline_calls):
    grouped=defaultdict(list)
    for row in outcomes:grouped[row['seed']].append(row)
    scores={};by_bank={}
    for seed in SEEDS:
        bank=grouped[seed];entry={}
        for parent in PARENTS:
            child=frozen['children'][parent]
            selected=set(child['calls'][str(seed)])
            entry[parent]=sum((r['one'] if r['id'] in selected else r['zero'])
                [child['route'][r['family']]] for r in bank)
        fixed=set(baseline_calls[str(seed)])
        entry['fixed_e1']=sum((r['one'] if r['id'] in fixed else r['zero'])['e1']
                              for r in bank)
        by_bank[str(seed)]=entry
    for label,seeds in (('admission',SEEDS[:6]),('transfer',SEEDS[6:]),('all',SEEDS)):
        scores[label]={name:sum(by_bank[str(s)][name] for s in seeds)
                       for name in PARENTS+('fixed_e1',)}
    return scores,by_bank


def forecast_metrics(frozen,records,outcomes):
    lookup={r['id']:r for r in outcomes}
    result={}
    for parent in PARENTS:
        child=frozen['children'][parent]
        rows=[{'id':r['id'],'public_block':r['public_block'],
               'features':r['query_features']} for r in records]
        predictions=values(child['query_model'],rows)
        actual=[]
        for record in records:
            outcome=lookup[record['id']]
            name=child['route'][record['family']]
            actual.append(outcome['one'][name]-outcome['zero'][name])
        errors=[float(pred)-truth for pred,truth in zip(predictions,actual)]
        chosen=sum(actual[i] for i,r in enumerate(records) if r['id'] in
                   set(child['calls'][str(r['seed'])]))
        oracle=0
        for seed in SEEDS:
            oracle+=sum(sorted((actual[i] for i,r in enumerate(records)
                if r['seed']==seed),reverse=True)[:8])
        result[parent]={'query_gain_mse':sum(e*e for e in errors)/len(errors),
            'query_gain_mae':sum(abs(e) for e in errors)/len(errors),
            'predicted_mean_gain':float(sum(predictions)/len(predictions)),
            'observed_mean_gain':sum(actual)/len(actual),
            'selected_query_gain':chosen,'unavailable_hindsight_gain':oracle,
            'selected_regret':oracle-chosen}
    return result


def score():
    if REPORT.exists():raise RuntimeError('already reported')
    frozen=json.loads(FROZEN.read_text())
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert frozen['runner_sha256']==sha(ROOT/'candidate_edit_improver_transfer.py')
    assert frozen['ledger_sha256']==sha(LEDGER)
    assert frozen['target_records_sha256']==sha(RUN/'frozen_records.json')
    assert frozen['target_bank_manifest_sha256']==sha(RUN/'bank_manifest.json')
    assert json.loads((RUN/'audit.json').read_text())['passed']
    outcomes=json.loads((RUN/'results.json').read_text())['tasks']
    records=json.loads((RUN/'frozen_records.json').read_text())
    calls=json.loads((RUN/'frozen_allocations.json').read_text())
    scores,banks=compute(frozen,outcomes,calls)
    forecasts=forecast_metrics(frozen,records,outcomes)
    admission=scores['admission'];transfer=scores['transfer']
    admitted=(admission['later']>=admission['initial'] and
              admission['later']>=admission['fixed_e1'])
    diffs=[banks[str(seed)]['later']-banks[str(seed)]['initial']
           for seed in SEEDS[6:]]
    gate={'admitted':admitted,'later_minus_initial':sum(diffs),
          'positive_banks':sum(x>0 for x in diffs),
          'losing_banks':sum(x<0 for x in diffs),
          'interval':interval(diffs)}
    gate['growth']=bool(admitted and sum(diffs)>=4 and
        gate['positive_banks']>=4 and gate['interval'][0]>0 and
        transfer['later']>transfer['scrambled'] and
        transfer['later']>transfer['duplicate'] and
        transfer['later']>=transfer['fixed_e1'])
    result={'scores':scores,'by_bank':banks,'gate':gate,'forecasts':forecasts,
            'source_tasks':{p:frozen['children'][p]['source_tasks'] for p in PARENTS},
            'output_calls_per_child':len(SEEDS)*8,
            'frozen_sha256':sha(FROZEN),'target_results_sha256':sha(RUN/'results.json'),
            'limits':['Fixed researcher-written edit vocabulary and training rule.',
                'Synthetic task generator; no autonomous edit-type creation.']}
    write_json(REPORT,result)
    print(json.dumps(result,indent=2))


def audit():
    frozen=json.loads(FROZEN.read_text())
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert frozen['ledger_sha256']==sha(LEDGER)
    records=json.loads((RUN/'frozen_records.json').read_text())
    tables=source_tables()
    for parent in PARENTS:
        child=frozen['children'][parent];source=tables[parent]
        routes=route(source);assert routes==child['route']
        assert child['source_task_ids']==[r['id'] for r in source]
        model=fit_method(training_rows(source,routes),'family_100')
        assert model==child['query_model']
        for seed in SEEDS:
            bank=[{'id':r['id'],'seed':seed,'public_block':r['public_block'],
                   'features':r['query_features']} for r in records if r['seed']==seed]
            assert sorted(select(bank,model))==child['calls'][str(seed)]
    scored=json.loads(REPORT.read_text());assert scored['frozen_sha256']==sha(FROZEN)
    assert scored['target_results_sha256']==sha(RUN/'results.json')
    outcomes=json.loads((RUN/'results.json').read_text())['tasks']
    calls=json.loads((RUN/'frozen_allocations.json').read_text())
    scores,banks=compute(frozen,outcomes,calls)
    assert scores==scored['scores'] and banks==scored['by_bank']
    assert forecast_metrics(frozen,records,outcomes)==scored['forecasts']
    print(json.dumps({'passed':True,'source_rows_rechecked':sum(len(v) for v
        in tables.values()),'target_decisions_rechecked':len(outcomes)*len(PARENTS)},
        indent=2))


if __name__=='__main__':
    {'freeze':freeze,'score':score,'audit':audit}[sys.argv[1]]()
