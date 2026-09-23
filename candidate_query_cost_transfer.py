"""Prospective lower-inference-cost E0 query-value checkpoint transfer."""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from collections import Counter,defaultdict

import numpy as np

from rsi.common import ROOT,write_json
import candidate_reranker_transfer as transfer
from candidate_conditioned_query_development import source_rows,features
from candidate_query_cost_ablation import cheap
from cross_family_meta_improver_development import fit_method,values
from cross_family_meta_improver_transfer import interval


DEST=ROOT/'runs/candidate-query-cost-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-candidate-query-cost-transfer.md'
SOURCE=ROOT/'runs/candidate-reranker-transfer-20260918'
PANELS=(SOURCE,ROOT/'runs/candidate-reranker-replication-20260918',
        ROOT/'runs/candidate-conditioned-query-transfer-20260918')
QUERY_MODEL=ROOT/'runs/focused-feedback-transfer-20260918/models.json'
DEVELOPMENT=ROOT/'analysis/candidate-query-cost-ablation-20260918.json'
FROZEN=DEST/'cost_children.json'
REPORT=DEST/'cost_results.json'
SEEDS=tuple(range(902546,902558))
NAMES=('cheap_initial','cheap_later','scrambled','duplicate',
       'full_matched','old_matched','incumbent')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def configure():
    transfer.DEST=DEST
    transfer.PROTOCOL=PROTOCOL
    transfer.SEEDS=SEEDS


def prepare():
    if DEST.exists():raise RuntimeError('run already exists')
    assert all(json.loads((p/'audit.json').read_text())['passed'] for p in PANELS)
    dev=json.loads(DEVELOPMENT.read_text())
    assert dev['summary']['source_cv']['cheap']>=dev['summary']['source_cv']['full']-2
    prior=json.loads((SOURCE/'source_manifest.json').read_text())
    DEST.mkdir(parents=True)
    for name,expected in prior['model_sha256'].items():
        shutil.copy2(SOURCE/f'{name}.joblib',DEST/f'{name}.joblib')
        assert sha(DEST/f'{name}.joblib')==expected
    prior['protocol_sha256']=sha(PROTOCOL)
    prior['replicated_from']=str(SOURCE.relative_to(ROOT))
    write_json(DEST/'source_manifest.json',prior)
    configure();transfer.freeze_banks()


def cheap_public_features(record,matrix):
    """24 public features without reading E1 or 7-leaf model output."""
    scores=np.asarray(record['old_scores'],float)
    old=record['orders']['old'];new=record['orders']['e0']
    head=new[:20];probe=record['probe'];n=len(head)
    assert n>0
    outputs=[matrix[i][probe] for i in head];counts=Counter(outputs)
    shares=np.asarray(list(counts.values()),float)/n
    top=outputs[0];std=max(float(scores.std()),.05)
    agreement=[sum(matrix[i][j]==matrix[head[0]][j] for i in head)/n
               for j in range(8)]
    distinct_rank=next((rank for rank,index in enumerate(head)
                        if matrix[index][probe]!=top),n)
    old_rank={idx:rank for rank,idx in enumerate(old)}
    extra=[old_rank[new[0]]/len(old),
           (scores[old[0]]-scores[new[0]])/std,
           (scores[new[0]]-scores[new[1]])/std if len(new)>1 else 0.,
           -sum(x*math.log(x) for x in shares),
           counts[top]/n,max(shares),len(counts)/n,
           distinct_rank/n,sum(agreement)/8,max(agreement),
           float(new[0]==old[0]),
           float(matrix[new[0]][probe]==matrix[old[0]][probe])]
    result=list(record['query_features'])+extra
    assert len(result)==24
    return result


def all_source_rows():
    first,_=source_rows();assert len(first)==1152
    third=PANELS[2]
    records=json.loads((third/'frozen_records.json').read_text())
    matrix=json.loads((third/'predicted_probe_outputs.json').read_text())
    outcomes=json.loads((third/'results.json').read_text())['tasks']
    added=[]
    for record,outcome in zip(records,outcomes):
        assert record['id']==outcome['id']
        full=features(record,matrix[record['id']])
        short=cheap_public_features(record,matrix[record['id']])
        assert np.allclose(short,cheap(full))
        added.append({'id':record['id'],'seed':record['seed'],
            'family':record['family'],'public_block':record['public_block'],
            'old_features':record['query_features'],
            'conditioned_features':full,'cheap_features':short,
            'gain':outcome['one']['e0']-outcome['zero']['e0']})
    result=[]
    for row in first:
        result.append({**row,'cheap_features':cheap(row['conditioned_features'])})
    result.extend(added)
    assert len(result)==1728 and len({r['id'] for r in result})==1728
    return result


def source_tables(rows):
    first=rows[:1152];added=rows[1152:]
    assert len(added)==576
    scrambled=[dict(r) for r in added]
    for family in sorted({r['family'] for r in added}):
        indexes=[i for i,r in enumerate(added) if r['family']==family]
        for target,donor in zip(indexes,indexes[-1:]+indexes[:-1]):
            scrambled[target]={**scrambled[target],'gain':added[donor]['gain']}
    return {'cheap_initial':first,'cheap_later':rows,
        'scrambled':first+scrambled,'duplicate':first+first[:576],
        'full_matched':rows,'old_matched':rows}


def method_for(name):
    if name=='full_matched':return 'conditioned_features','interaction_100'
    if name in ('old_matched','incumbent'):return 'old_features','family_100'
    return 'cheap_features','interaction_100'


def model_rows(rows,field):
    return [{**row,'features':row[field]} for row in rows]


def child_states(records,matrix):
    source=all_source_rows();tables=source_tables(source)
    target=[]
    for record in records:
        full=features(record,matrix[record['id']])
        short=cheap_public_features(record,matrix[record['id']])
        assert np.allclose(short,cheap(full))
        target.append({'id':record['id'],'seed':record['seed'],
            'public_block':record['public_block'],'old_features':
                record['query_features'],'conditioned_features':full,
            'cheap_features':short})
    assert len(target)==576
    grouped=defaultdict(list)
    for row in target:grouped[row['seed']].append(row)
    assert tuple(sorted(grouped))==SEEDS
    old=json.loads(QUERY_MODEL.read_text())['e0']
    children={}
    for name in NAMES:
        field,method=method_for(name)
        model=old if name=='incumbent' else fit_method(
            model_rows(tables[name],field),method)
        calls={};forecasts=[]
        for seed in SEEDS:
            bank=grouped[seed]
            p=values(model,model_rows(bank,field))
            order=sorted(range(len(bank)),key=lambda i:(float(p[i]),bank[i]['id']),
                         reverse=True)
            calls[str(seed)]=sorted(bank[i]['id'] for i in order[:8])
            forecasts.extend({'id':r['id'],'value':float(value)}
                             for r,value in zip(bank,p))
        children[name]={'field':field,'method':method,'model':model,
            'source_tasks':576 if name=='incumbent' else len(tables[name]),
            'calls':calls,'forecasts':forecasts}
    return children


def freeze():
    if FROZEN.exists():raise RuntimeError('children already frozen')
    assert not (DEST/'results.json').exists(),'target labels already scored'
    records=json.loads((DEST/'frozen_records.json').read_text())
    matrix=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    children=child_states(records,matrix)
    assert children['incumbent']['calls']==json.loads(
        (DEST/'frozen_allocations.json').read_text())
    files=[DEVELOPMENT,QUERY_MODEL,ROOT/'candidate_query_cost_ablation.py',
        ROOT/'candidate_conditioned_query_development.py',
        *(p/name for p in PANELS for name in ('audit.json','results.json',
            'frozen_records.json','predicted_probe_outputs.json'))]
    manifest={'protocol_sha256':sha(PROTOCOL),
        'runner_sha256':sha(ROOT/'candidate_query_cost_transfer.py'),
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
    if not FROZEN.exists():raise RuntimeError('children must be frozen')
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
        child=frozen['children'][name]
        lookup={r['id']:r['value'] for r in child['forecasts']}
        errors=[];selected_gain=0;hindsight=0
        for seed in SEEDS:
            bank=grouped[seed];calls=set(child['calls'][str(seed)])
            assert len(bank)==48 and len(calls)==8
            gains=[]
            for row in bank:
                gain=row['one']['e0']-row['zero']['e0'];gains.append(gain)
                errors.append((lookup[row['id']]-gain)**2)
                if row['id'] in calls:selected_gain+=gain
            hindsight+=sum(sorted(gains,reverse=True)[:8])
        forecasts[name]={'mse':sum(errors)/len(errors),
            'selected_gain':selected_gain,'hindsight_gain':hindsight,
            'regret':hindsight-selected_gain}
    for seed in SEEDS:
        bank=grouped[seed];entry={}
        for name in NAMES:
            calls=set(frozen['children'][name]['calls'][str(seed)])
            entry[name]=sum((r['one'] if r['id'] in calls else r['zero'])['e0']
                            for r in bank)
        entry['e0_noquery']=sum(r['zero']['e0'] for r in bank)
        banks[str(seed)]=entry
    totals={label:{name:sum(banks[str(seed)][name] for seed in seeds)
                   for name in NAMES+('e0_noquery',)}
            for label,seeds in {'admission':SEEDS[:6],
                                'transfer':SEEDS[6:],'all':SEEDS}.items()}
    return totals,banks,forecasts


def gates(totals,banks,forecasts):
    def compare(a,b,seeds):
        diffs=[banks[str(seed)][a]-banks[str(seed)][b] for seed in seeds]
        return {'gain':sum(diffs),'positive_banks':sum(x>0 for x in diffs),
            'losing_banks':sum(x<0 for x in diffs),'interval':interval(diffs)}
    cost=compare('cheap_later','full_matched',SEEDS)
    cost['noninferior']=bool(cost['gain']>=-2 and cost['interval'][0]>=-6 and
        forecasts['cheap_later']['mse']<=forecasts['full_matched']['mse']+.005)
    prior=compare('cheap_later','incumbent',SEEDS)
    prior['promote']=bool(prior['gain']>=8 and prior['positive_banks']>=8 and
        prior['losing_banks']<=2 and prior['interval'][0]>0 and
        forecasts['cheap_later']['mse']<forecasts['incumbent']['mse'])
    admission=totals['admission'];transfer=totals['transfer']
    admitted=all(admission['cheap_later']>=admission[name] for name in
                 ('cheap_initial','incumbent','old_matched'))
    child=compare('cheap_later','cheap_initial',SEEDS[6:])
    child['admitted']=admitted
    child['growth']=bool(admitted and child['gain']>=4 and
        child['positive_banks']>=4 and child['interval'][0]>0 and
        all(transfer['cheap_later']>transfer[name] for name in
            ('scrambled','duplicate','incumbent')))
    return {'cost':cost,'incumbent':prior,'improver':child}


def report():
    if REPORT.exists():raise RuntimeError('report already exists')
    assert json.loads((DEST/'audit.json').read_text())['passed']
    frozen=json.loads(FROZEN.read_text())
    assert frozen['protocol_sha256']==sha(PROTOCOL)
    assert frozen['runner_sha256']==sha(ROOT/'candidate_query_cost_transfer.py')
    assert all(sha(ROOT/name)==value for name,value in
               frozen['source_sha256'].items())
    outcomes=json.loads((DEST/'results.json').read_text())['tasks']
    totals,banks,forecasts=calculate(frozen,outcomes)
    result={'scores':totals,'by_bank':banks,'forecasts':forecasts,
        'gates':gates(totals,banks,forecasts),'source_tasks':
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
    assert child_states(records,matrix)==frozen['children']
    outcomes=json.loads((DEST/'results.json').read_text())['tasks']
    totals,banks,forecasts=calculate(frozen,outcomes)
    assert totals==saved['scores'] and banks==saved['by_bank']
    assert forecasts==saved['forecasts']
    assert gates(totals,banks,forecasts)==saved['gates']
    print(json.dumps({'passed':True,'source_tasks_rebuilt':1728,
        'target_child_decisions_rechecked':576*len(NAMES)},indent=2))


if __name__=='__main__':
    {'prepare':prepare,'freeze':freeze,'score':score,'audit':audit_base,
     'report':report,'check':check}[sys.argv[1]]()
