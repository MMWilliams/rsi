"""Fresh candidate reranker checkpoint and fixed-budget integration test."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_development import MODES
from ast_query_allocation_development import features as query_features
from cross_family_meta_improver_development import select as allocate
from cross_family_meta_improver_transfer import interval
from ast_evaluator_feedback import features as structural_features


DEST=ROOT/'runs/candidate-reranker-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-candidate-reranker-transfer.md'
CACHE=ROOT/'analysis/candidate-reranker-top20-cache-20260918'
QUERY_MODEL=ROOT/'runs/focused-feedback-transfer-20260918/models.json'
SEEDS=tuple(range(902510,902522))
BLOCKS=(0x700,0x800,0x900,0xa00,0xc00,0xd00)
NAMES=('old','e0','e1','leaf7','scrambled')
K=20


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def model_path(name):return DEST/f'{name}.joblib'


def model_for(leaves):
    return HistGradientBoostingClassifier(max_leaf_nodes=leaves,
        min_samples_leaf=80,learning_rate=.05,max_iter=100,
        l2_regularization=1.,random_state=0)


def source_arrays(panels):
    xs=[];ys=[];meta=[]
    for name in panels:
        raw=np.load(CACHE/f'{name}.npz')
        record=json.loads((CACHE/f'{name}.json').read_text())
        x=raw['x'];y=raw['y'];detail=record['tasks_detail']
        assert len(y)==sum(r['candidate_count'] for r in detail)
        xs.append(x);ys.append(y);meta.extend(detail)
    return np.concatenate(xs),np.concatenate(ys),meta


def scramble_within_task(y,meta):
    out=y.copy();offset=0
    for row in meta:
        n=row['candidate_count']
        if n>1:out[offset:offset+n]=np.roll(y[offset:offset+n],1)
        offset+=n
    assert offset==len(y)
    return out


def freeze_source():
    if DEST.exists():raise RuntimeError('run exists')
    early=('meta_admission','meta_a')
    late=('meta_admission','meta_a','meta_b')
    x0,y0,m0=source_arrays(early)
    x1,y1,m1=source_arrays(late)
    models={'e0':model_for(15).fit(x0,y0),
            'e1':model_for(15).fit(x1,y1),
            'leaf7':model_for(7).fit(x1,y1),
            'scrambled':model_for(15).fit(x1,scramble_within_task(y1,m1))}
    for name,model in models.items():
        DEST.mkdir(parents=True,exist_ok=True)
        joblib.dump(model,model_path(name),compress=3)
    files=(ROOT/'candidate_reranker_development.py',
           ROOT/'analysis/temperature-ranker-development.json',
           ROOT/'analysis/ast-feedback-replay-model.json',QUERY_MODEL,
           *(CACHE/f'{name}{suffix}' for name in late for suffix in ('.npz','.json')))
    manifest={'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'candidate_reranker_transfer.py'),
              'source_sha256':{str(path.relative_to(ROOT)):sha(path) for path in files},
              'source_tasks_e0':len(m0),'source_tasks_e1':len(m1),
              'candidate_labels_e0':len(y0),'candidate_labels_e1':len(y1),
              'positive_labels_e0':int(y0.sum()),
              'positive_labels_e1':int(y1.sum()),
              'model_sha256':{name:sha(model_path(name)) for name in models},
              'seeds':SEEDS,'names':NAMES}
    write_json(DEST/'source_manifest.json',manifest)
    print(json.dumps({'status':'source frozen',**manifest},indent=2))


def candidate_features(task,pool,scores,order):
    head=order[:K];subset=[pool[i] for i in head]
    structural=np.asarray(structural_features(task,subset),np.float32)
    assert structural.shape==(len(head),175)
    std=max(float(np.std(scores)),.05);top=float(scores[head[0]])
    block=np.asarray([float(public_block(task)==b) for b in BLOCKS],np.float32)
    result=[]
    for rank,index in enumerate(head):
        extra=np.asarray([(scores[index]-top)/std,rank/K,
                          np.log1p(len(pool))/8.],np.float32)
        result.append(np.r_[structural[rank],extra,block])
    return np.asarray(result,np.float32)


def freeze_banks():
    if (DEST/'frozen_allocations.json').exists():raise RuntimeError('already prepared')
    source=json.loads((DEST/'source_manifest.json').read_text())
    assert source['protocol_sha256']==sha(PROTOCOL)
    assert source['runner_sha256']==sha(ROOT/'candidate_reranker_transfer.py')
    assert all(sha(model_path(name))==digest for name,digest in
               source['model_sha256'].items())
    start=time.perf_counter()
    tasks=[{**t,'seed':seed} for seed in SEEDS
           for t in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    base,wide,times=pools_for(tasks)
    public=[({'id':t['id'],'probe_inputs':[text for text,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    evaluators=evaluator_models();replay=updated_model()
    trained={name:joblib.load(model_path(name)) for name in source['model_sha256']}
    records=[];rescored=0
    for task in tasks:
        key=task['id'];block=public_block(task);pool=wide.get(key,base[key])
        ranker=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,old_order=rank(task,pool,ranker)
        first=choose_probe(key,predicted[key],old_order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        qfeatures=query_features(task,{'scores':scores,'order':old_order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        x=candidate_features(task,pool,scores,old_order)
        rescored+=len(x);orders={'old':old_order}
        for name,model in trained.items():
            probabilities=model.predict_proba(x)[:,1]
            order_top=sorted(range(len(x)),key=lambda i:(-float(probabilities[i]),i))
            orders[name]=[old_order[i] for i in order_top]+old_order[len(x):]
        assert all(len(order)==len(pool) and len(set(order))==len(pool)
                   for order in orders.values())
        records.append({'id':key,'seed':task['seed'],'family':task['family'],
                        'public_block':block,'pool_sha256':digest(pool),
                        'old_scores':scores,'orders':orders,'probe':first,
                        'query_features':qfeatures.tolist()})
    allocator=json.loads(QUERY_MODEL.read_text())['e0']
    by_id={r['id']:r for r in records};allocations={}
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        rows=[{'id':r['id'],'seed':seed,'public_block':r['public_block'],
               'features':r['query_features']} for r in group]
        allocations[str(seed)]=sorted(allocate(rows,allocator))
        assert len(allocations[str(seed)])==8
    manifest={'seeds':SEEDS,'tasks':len(tasks),'calls_per_bank':8,
              'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'candidate_reranker_transfer.py'),
              'source_manifest_sha256':sha(DEST/'source_manifest.json'),
              'model_sha256':source['model_sha256'],
              'query_model_sha256':sha(QUERY_MODEL),
              'base_candidates':sum(len(v) for v in base.values()),
              'extra_ast_candidates':sum(len(v)-len(base[k]) for k,v in wide.items()),
              'top20_candidates_rescored':rescored,
              'candidate_output_cells':sum(len(wide.get(t['id'],base[t['id']]))*8
                                           for t in tasks),
              'generation_seconds':sum(times.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json',tasks)
    write_json(DEST/'base_pools.json',base)
    write_json(DEST/'ast_wide_pools.json',wide)
    write_json(DEST/'predicted_probe_outputs.json',predicted)
    write_json(DEST/'frozen_records.json',records)
    write_json(DEST/'frozen_allocations.json',allocations)
    manifest['frozen_records_sha256']=sha(DEST/'frozen_records.json')
    manifest['frozen_allocations_sha256']=sha(DEST/'frozen_allocations.json')
    write_json(DEST/'bank_manifest.json',manifest)
    print(json.dumps({'status':'banks frozen',**manifest},indent=2))


def score_banks():
    if (DEST/'results.json').exists():raise RuntimeError('already scored')
    manifest=json.loads((DEST/'bank_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'candidate_reranker_transfer.py')
    assert manifest['frozen_records_sha256']==sha(DEST/'frozen_records.json')
    assert manifest['frozen_allocations_sha256']==sha(DEST/'frozen_allocations.json')
    assert manifest['query_model_sha256']==sha(QUERY_MODEL)
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    records=json.loads((DEST/'frozen_records.json').read_text())
    allocations=json.loads((DEST/'frozen_allocations.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        assert key==record['id'] and digest(pool)==record['pool_sha256']
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:])))
                for row in pool]
        checked+=len(labels)
        first=record['probe']
        matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matching if matching else set(range(len(pool)))
        zero={name:labels[order[0]] for name,order in record['orders'].items()}
        one={name:labels[next(i for i in order if i in remaining)]
             for name,order in record['orders'].items()}
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'public_block':record['public_block'],
                         'full_reachable':int(any(labels)),
                         'top20_reachable':int(any(labels[i] for i in record['orders']['old'][:K])),
                         'zero':zero,'one':one})
    lookup={o['id']:o for o in outcomes};banks=[]
    for seed in SEEDS:
        group=[lookup[t['id']] for t in tasks if t['seed']==seed]
        selected=set(allocations[str(seed)])
        noquery={name:sum(r['zero'][name] for r in group) for name in NAMES}
        budget={name:sum(r['one'][name] if r['id'] in selected else r['zero'][name]
                         for r in group) for name in NAMES}
        oneeach={name:sum(r['one'][name] for r in group) for name in NAMES}
        banks.append({'seed':seed,'full_reachable':sum(r['full_reachable'] for r in group),
                      'top20_reachable':sum(r['top20_reachable'] for r in group),
                      'noquery':noquery,'budget_eight':budget,'one_each':oneeach})
    totals={field:{name:sum(b[field][name] for b in banks) for name in NAMES}
            for field in ('noquery','budget_eight','one_each')}
    diffs=[b['noquery']['e1']-b['noquery']['e0'] for b in banks]
    gate={'e1_minus_e0':sum(diffs),'positive_banks':sum(d>0 for d in diffs),
          'losing_banks':sum(d<0 for d in diffs),'interval':interval(diffs)}
    gate['promote']=(gate['e1_minus_e0']>=8 and gate['positive_banks']>=8 and
                     gate['losing_banks']<=2 and gate['interval'][0]>0 and
                     totals['noquery']['e1']>totals['noquery']['leaf7'] and
                     totals['noquery']['e1']>totals['noquery']['scrambled'] and
                     totals['budget_eight']['e1']>=totals['budget_eight']['e0'])
    summary={'tasks':len(tasks),'banks':len(banks),'candidate_labels_checked':checked,
             'true_output_calls_per_policy':len(banks)*8,
             'full_reachable':sum(b['full_reachable'] for b in banks),
             'top20_reachable':sum(b['top20_reachable'] for b in banks),
             'totals':totals,'e1_minus_e0_by_bank':diffs,'gate':gate}
    write_json(DEST/'results.json',{'summary':summary,'banks':banks,'tasks':outcomes,
                                    'bank_manifest_sha256':sha(DEST/'bank_manifest.json')})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    {'source':freeze_source,'prepare':freeze_banks,'score':score_banks}[sys.argv[1]]()
