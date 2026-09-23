"""Fresh matched E0/E1 ranker plus cheap query-value package test."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import defaultdict

from rsi.common import ROOT,write_json
import candidate_reranker_transfer as transfer
from combined_ranker_query_development import PANELS,source_rows,feature_for
from cross_family_meta_improver_development import fit_method,values
from cross_family_meta_improver_transfer import interval


DEST=ROOT/'runs/combined-ranker-query-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-combined-ranker-query-transfer.md'
SOURCE=PANELS[0]
DEVELOPMENT=ROOT/'analysis/combined-ranker-query-development-20260918.json'
QUERY_MODEL=ROOT/'runs/focused-feedback-transfer-20260918/models.json'
FROZEN=DEST/'combined_children.json'
REPORT=DEST/'combined_results.json'
SEEDS=tuple(range(902558,902570))
NAMES=('e0_full','e1_initial','e1_full','e1_scrambled','e1_duplicate',
       'e0_old_allocator','e1_old_allocator')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def configure():
    transfer.DEST=DEST;transfer.PROTOCOL=PROTOCOL;transfer.SEEDS=SEEDS


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANELS)
    assert json.loads(DEVELOPMENT.read_text())['e1_minus_e0']['gain']==29
    source=json.loads((SOURCE/'source_manifest.json').read_text())
    DEST.mkdir(parents=True)
    for name,expected in source['model_sha256'].items():
        shutil.copy2(SOURCE/f'{name}.joblib',DEST/f'{name}.joblib')
        assert sha(DEST/f'{name}.joblib')==expected
    source['protocol_sha256']=sha(PROTOCOL)
    source['replicated_from']=str(SOURCE.relative_to(ROOT))
    write_json(DEST/'source_manifest.json',source)
    configure();transfer.freeze_banks()


def tables(rows):
    first=rows[:1152];added=rows[1152:]
    assert len(first)==len(added)==1152
    scrambled=[dict(row) for row in added]
    for family in sorted({r['family'] for r in added}):
        indexes=[i for i,r in enumerate(added) if r['family']==family]
        for target,donor in zip(indexes,indexes[-1:]+indexes[:-1]):
            donor_gain=added[donor]['e1']['gain']
            scrambled[target]={**scrambled[target],
                'e1':{**scrambled[target]['e1'],'gain':donor_gain}}
    return {'e0_full':rows,'e1_initial':first,'e1_full':rows,
            'e1_scrambled':first+scrambled,'e1_duplicate':first+first}


def ranker(name):return 'e0' if name.startswith('e0_') else 'e1'


def model_rows(rows,name):
    return [{'id':r['id'],'seed':r['seed'],'public_block':r['public_block'],
             **r[name]} for r in rows]


def children_from(records,matrix):
    source=source_rows();training=tables(source)
    target=[]
    for record in records:
        target.append({'id':record['id'],'seed':record['seed'],
            'public_block':record['public_block'],
            'old_features':record['query_features'],
            'e0':{'features':feature_for(record,matrix[record['id']],'e0')},
            'e1':{'features':feature_for(record,matrix[record['id']],'e1')}})
    assert len(target)==576
    grouped=defaultdict(list)
    for row in target:grouped[row['seed']].append(row)
    assert tuple(sorted(grouped))==SEEDS
    old=json.loads(QUERY_MODEL.read_text())['e0']
    original=json.loads((DEST/'frozen_allocations.json').read_text())
    children={}
    for name in NAMES:
        policy=ranker(name)
        if name.endswith('old_allocator'):
            model=old;count=576
        else:
            model=fit_method(model_rows(training[name],policy),'interaction_100')
            count=len(training[name])
        calls={};forecasts=[]
        for seed in SEEDS:
            bank=grouped[seed]
            if name.endswith('old_allocator'):
                p=values(model,[{'id':r['id'],'public_block':r['public_block'],
                                 'features':r['old_features']} for r in bank])
                calls[str(seed)]=original[str(seed)]
            else:
                p=values(model,model_rows(bank,policy))
                order=sorted(range(len(bank)),key=lambda i:(float(p[i]),bank[i]['id']),
                             reverse=True)
                calls[str(seed)]=sorted(bank[i]['id'] for i in order[:8])
            forecasts.extend({'id':r['id'],'value':float(value)}
                             for r,value in zip(bank,p))
            assert len(calls[str(seed)])==8
        children[name]={'ranker':policy,'source_tasks':count,'model':model,
            'calls':calls,'forecasts':forecasts}
    return children


def freeze():
    if FROZEN.exists():raise RuntimeError('children already frozen')
    assert not (DEST/'results.json').exists(),'target labels already scored'
    records=json.loads((DEST/'frozen_records.json').read_text())
    matrix=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    children=children_from(records,matrix)
    files=[DEVELOPMENT,QUERY_MODEL,ROOT/'combined_ranker_query_development.py',
        ROOT/'candidate_query_cost_transfer.py',
        *(p/name for p in PANELS for name in ('audit.json','results.json',
            'frozen_records.json','predicted_probe_outputs.json'))]
    manifest={'protocol_sha256':sha(PROTOCOL),
        'runner_sha256':sha(ROOT/'combined_ranker_query_transfer.py'),
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},
        'bank_manifest_sha256':sha(DEST/'bank_manifest.json'),
        'target_records_sha256':sha(DEST/'frozen_records.json'),
        'target_predictions_sha256':sha(DEST/'predicted_probe_outputs.json'),
        'children':children,'admission_seeds':SEEDS[:6],
        'transfer_seeds':SEEDS[6:]}
    write_json(FROZEN,manifest)
    print(json.dumps({'status':'children frozen','source_tasks':
        {n:children[n]['source_tasks'] for n in NAMES},
        'calls_per_child':96,'frozen_sha256':sha(FROZEN)},indent=2))


def score():
    if not FROZEN.exists():raise RuntimeError('freeze children before scoring')
    configure();transfer.score_banks()


def audit_base():
    configure()
    import audit_candidate_reranker_transfer as independent
    independent.main()


def calculate(frozen,outcomes):
    grouped=defaultdict(list)
    for row in outcomes:grouped[row['seed']].append(row)
    banks={};forecasts={}
    for name in NAMES:
        child=frozen['children'][name];policy=child['ranker']
        lookup={r['id']:r['value'] for r in child['forecasts']}
        errors=[];selected_gain=0;hindsight=0
        for seed in SEEDS:
            bank=grouped[seed];calls=set(child['calls'][str(seed)])
            assert len(bank)==48 and len(calls)==8
            gains=[]
            for row in bank:
                gain=row['one'][policy]-row['zero'][policy];gains.append(gain)
                errors.append((lookup[row['id']]-gain)**2)
                if row['id'] in calls:selected_gain+=gain
            hindsight+=sum(sorted(gains,reverse=True)[:8])
        forecasts[name]={'mse':sum(errors)/len(errors),
            'selected_gain':selected_gain,'hindsight_gain':hindsight,
            'regret':hindsight-selected_gain}
    for seed in SEEDS:
        bank=grouped[seed];entry={}
        for name in NAMES:
            child=frozen['children'][name];policy=child['ranker']
            calls=set(child['calls'][str(seed)])
            entry[name]=sum((r['one'] if r['id'] in calls else r['zero'])[policy]
                            for r in bank)
        entry['e0_noquery']=sum(r['zero']['e0'] for r in bank)
        entry['e1_noquery']=sum(r['zero']['e1'] for r in bank)
        banks[str(seed)]=entry
    totals={label:{name:sum(banks[str(seed)][name] for seed in seeds)
                   for name in NAMES+('e0_noquery','e1_noquery')}
            for label,seeds in {'admission':SEEDS[:6],
                                'transfer':SEEDS[6:],'all':SEEDS}.items()}
    return totals,banks,forecasts


def gates(totals,banks):
    def paired(a,b,seeds):
        diffs=[banks[str(seed)][a]-banks[str(seed)][b] for seed in seeds]
        return {'gain':sum(diffs),'positive_banks':sum(x>0 for x in diffs),
            'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    package=paired('e1_full','e0_full',SEEDS)
    package['promote']=bool(package['gain']>=8 and package['positive_banks']>=8
        and package['losing_banks']<=2 and package['interval'][0]>0)
    admission=totals['admission'];transfer=totals['transfer']
    child=paired('e1_full','e1_initial',SEEDS[6:])
    child['admitted']=bool(admission['e1_full']>=admission['e1_initial'] and
        admission['e1_full']>=admission['e1_old_allocator'])
    child['growth']=bool(child['admitted'] and child['gain']>=4 and
        child['positive_banks']>=4 and child['interval'][0]>0 and
        all(transfer['e1_full']>transfer[name] for name in
            ('e1_scrambled','e1_duplicate','e1_old_allocator')))
    return {'package':package,'improver':child}


def report():
    if REPORT.exists():raise RuntimeError('report already exists')
    assert json.loads((DEST/'audit.json').read_text())['passed']
    frozen=json.loads(FROZEN.read_text())
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert frozen['runner_sha256']==sha(ROOT/'combined_ranker_query_transfer.py')
    assert all(sha(ROOT/name)==value for name,value in
               frozen['source_sha256'].items())
    outcomes=json.loads((DEST/'results.json').read_text())['tasks']
    totals,banks,forecasts=calculate(frozen,outcomes)
    result={'scores':totals,'by_bank':banks,'forecasts':forecasts,
        'gates':gates(totals,banks),'source_tasks':
            {n:frozen['children'][n]['source_tasks'] for n in NAMES},
        'query_calls_per_child':96,
        'bank_manifest':json.loads((DEST/'bank_manifest.json').read_text()),
        'base_audit':json.loads((DEST/'audit.json').read_text()),
        'frozen_sha256':sha(FROZEN),'target_results_sha256':sha(DEST/'results.json')}
    write_json(REPORT,result)
    print(json.dumps({k:v for k,v in result.items() if k not in
        ('by_bank','bank_manifest','base_audit')},indent=2))


def check():
    saved=json.loads(REPORT.read_text());frozen=json.loads(FROZEN.read_text())
    assert saved['frozen_sha256']==sha(FROZEN)
    assert saved['target_results_sha256']==sha(DEST/'results.json')
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert all(sha(ROOT/name)==value for name,value in
               frozen['source_sha256'].items())
    records=json.loads((DEST/'frozen_records.json').read_text())
    matrix=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    assert children_from(records,matrix)==frozen['children']
    outcomes=json.loads((DEST/'results.json').read_text())['tasks']
    totals,banks,forecasts=calculate(frozen,outcomes)
    assert totals==saved['scores'] and banks==saved['by_bank']
    assert forecasts==saved['forecasts']
    assert gates(totals,banks)==saved['gates']
    print(json.dumps({'passed':True,'source_tasks_rebuilt':2304,
        'target_child_decisions_rechecked':576*len(NAMES)},indent=2))


if __name__=='__main__':
    {'prepare':prepare,'freeze':freeze,'score':score,'audit':audit_base,
     'report':report,'check':check}[sys.argv[1]]()
