"""Independent source, freeze and exact-oracle replay of candidate reranker transfer."""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor

import joblib
import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features as query_features
from cross_family_meta_improver_development import select as allocate
from cross_family_meta_improver_transfer import interval
from candidate_reranker_development import panel_path
from candidate_reranker_transfer import (DEST,PROTOCOL,CACHE,QUERY_MODEL,SEEDS,
    NAMES,BLOCKS,K,sha,model_path,model_for,source_arrays,scramble_within_task,
    candidate_features)


def source_audit():
    source=json.loads((DEST/'source_manifest.json').read_text())
    assert source['protocol_sha256']==sha(PROTOCOL)
    assert source['runner_sha256']==sha(ROOT/'candidate_reranker_transfer.py')
    assert all(sha(ROOT/name)==value for name,value in source['source_sha256'].items())
    labels_checked=0;feature_rows=0
    from ast_evaluator_feedback import features as structural_features
    for name in ('meta_admission','meta_a','meta_b'):
        directory=panel_path(name)
        tasks=json.loads((directory/'sealed_bank.json').read_text())
        base=json.loads((directory/'base_pools.json').read_text())
        wide=json.loads((directory/'ast_wide_pools.json').read_text())
        records=json.loads((directory/'frozen_records.json').read_text())
        cached=np.load(CACHE/f'{name}.npz')
        detail=json.loads((CACHE/f'{name}.json').read_text())['tasks_detail']
        expected_x=[];expected_y=[]
        for task,record,row in zip(tasks,records,detail):
            key=task['id'];assert key==record['id']==row['id']
            pool=wide.get(key,base[key]);scores=np.asarray(record['scores'],float)
            order=record['order'][:K]
            structural=np.asarray(structural_features(task,[pool[i] for i in order]),
                                  np.float32)
            assert structural.shape==(len(order),175)
            std=max(float(scores.std()),.05);top=float(scores[order[0]])
            block=np.asarray([float(public_block(task)==b) for b in BLOCKS],np.float32)
            labels=[]
            for rank,index in enumerate(order):
                extra=np.asarray([(scores[index]-top)/std,rank/K,
                                  np.log1p(len(pool))/8.],np.float32)
                expected_x.append(np.r_[structural[rank],extra,block])
                label=int(bool(evaluate_program(pool[index]['program'],task['hidden'][8:])))
                expected_y.append(label);labels.append(label)
            assert row['candidate_count']==len(order)
            assert row['baseline_correct']==labels[0]
            assert row['top20_reachable']==int(any(labels))
        assert np.array_equal(cached['y'],np.asarray(expected_y,np.int8))
        assert np.allclose(cached['x'],np.asarray(expected_x,np.float32),atol=1e-7)
        labels_checked+=len(expected_y);feature_rows+=len(expected_x)
    x0,y0,m0=source_arrays(('meta_admission','meta_a'))
    x1,y1,m1=source_arrays(('meta_admission','meta_a','meta_b'))
    rebuilt={'e0':model_for(15).fit(x0,y0),
             'e1':model_for(15).fit(x1,y1),
             'leaf7':model_for(7).fit(x1,y1),
             'scrambled':model_for(15).fit(x1,scramble_within_task(y1,m1))}
    for name,model in rebuilt.items():
        assert source['model_sha256'][name]==sha(model_path(name))
        frozen=joblib.load(model_path(name))
        assert np.allclose(model.predict_proba(x1)[:,1],
                           frozen.predict_proba(x1)[:,1],atol=1e-12)
    assert source['source_tasks_e0']==len(m0)
    assert source['source_tasks_e1']==len(m1)
    assert source['candidate_labels_e1']==len(y1)
    return {'source_tasks_rebuilt':len(m1),'candidate_labels_rechecked':labels_checked,
            'public_feature_rows_rechecked':feature_rows,'models_retrained':len(rebuilt)}


def preparation_audit():
    manifest=json.loads((DEST/'bank_manifest.json').read_text())
    assert tuple(manifest['seeds'])==SEEDS and manifest['tasks']==576
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'candidate_reranker_transfer.py')
    assert manifest['source_manifest_sha256']==sha(DEST/'source_manifest.json')
    assert manifest['query_model_sha256']==sha(QUERY_MODEL)
    assert manifest['frozen_records_sha256']==sha(DEST/'frozen_records.json')
    assert manifest['frozen_allocations_sha256']==sha(DEST/'frozen_allocations.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    assert tasks==[{**t,'seed':seed} for seed in SEEDS
                   for t in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    generated_base,generated_wide,_=pools_for(tasks)
    assert base==generated_base and wide==generated_wide
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    public=[({'id':t['id'],'probe_inputs':[x for x,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    evaluators=evaluator_models();replay=updated_model()
    source=json.loads((DEST/'source_manifest.json').read_text())
    models={name:joblib.load(model_path(name)) for name in source['model_sha256']}
    records=json.loads((DEST/'frozen_records.json').read_text())
    rescored=0
    for task,record in zip(tasks,records):
        key=task['id'];block=public_block(task);pool=wide.get(key,base[key])
        assert key==record['id'] and digest(pool)==record['pool_sha256']
        old_model=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,old_order=rank(task,pool,old_model)
        assert old_order==record['orders']['old']
        assert np.allclose(scores,record['old_scores'],atol=1e-6)
        first=choose_probe(key,predicted[key],old_order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        assert first==record['probe']
        qfeatures=query_features(task,{'scores':scores,'order':old_order,
                       'first_probe':{'top20_entropy':first}},predicted[key])
        assert np.allclose(qfeatures,record['query_features'],atol=1e-6)
        x=candidate_features(task,pool,scores,old_order);rescored+=len(x)
        for name,model in models.items():
            p=model.predict_proba(x)[:,1]
            top=sorted(range(len(x)),key=lambda i:(-float(p[i]),i))
            order=[old_order[i] for i in top]+old_order[len(x):]
            assert order==record['orders'][name]
    allocator=json.loads(QUERY_MODEL.read_text())['e0']
    by_id={r['id']:r for r in records};allocations={}
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        rows=[{'id':r['id'],'seed':seed,'public_block':r['public_block'],
               'features':r['query_features']} for r in group]
        allocations[str(seed)]=sorted(allocate(rows,allocator))
    assert allocations==json.loads((DEST/'frozen_allocations.json').read_text())
    assert manifest['base_candidates']==sum(len(v) for v in base.values())
    assert manifest['extra_ast_candidates']==sum(len(v)-len(base[k]) for k,v in wide.items())
    assert manifest['top20_candidates_rescored']==rescored
    assert manifest['candidate_output_cells']==sum(len(wide.get(t['id'],base[t['id']]))*8
                                                   for t in tasks)
    return {'tasks_regenerated':len(tasks),'candidate_pools_regenerated':len(base),
            'top20_rescores_rechecked':rescored,
            'predicted_output_cells_rechecked':manifest['candidate_output_cells'],
            'allocations_rechecked':len(SEEDS)}


def score_audit():
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['bank_manifest_sha256']==sha(DEST/'bank_manifest.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    records=json.loads((DEST/'frozen_records.json').read_text())
    allocations=json.loads((DEST/'frozen_allocations.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
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
    assert outcomes==saved['tasks']
    summary=saved['summary'];assert summary['candidate_labels_checked']==checked
    by_id={o['id']:o for o in outcomes};banks=[]
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        selected=set(allocations[str(seed)])
        banks.append({'seed':seed,'full_reachable':sum(r['full_reachable'] for r in group),
          'top20_reachable':sum(r['top20_reachable'] for r in group),
          'noquery':{name:sum(r['zero'][name] for r in group) for name in NAMES},
          'budget_eight':{name:sum(r['one'][name] if r['id'] in selected
                               else r['zero'][name] for r in group) for name in NAMES},
          'one_each':{name:sum(r['one'][name] for r in group) for name in NAMES}})
    assert banks==saved['banks']
    totals={field:{name:sum(b[field][name] for b in banks) for name in NAMES}
            for field in ('noquery','budget_eight','one_each')}
    assert totals==summary['totals']
    assert summary['full_reachable']==sum(b['full_reachable'] for b in banks)
    assert summary['top20_reachable']==sum(b['top20_reachable'] for b in banks)
    diffs=[b['noquery']['e1']-b['noquery']['e0'] for b in banks]
    assert diffs==summary['e1_minus_e0_by_bank']
    gate=summary['gate'];assert gate['interval']==interval(diffs)
    assert gate['promote']==(sum(diffs)>=8 and sum(d>0 for d in diffs)>=8 and
        sum(d<0 for d in diffs)<=2 and interval(diffs)[0]>0 and
        totals['noquery']['e1']>totals['noquery']['leaf7'] and
        totals['noquery']['e1']>totals['noquery']['scrambled'] and
        totals['budget_eight']['e1']>=totals['budget_eight']['e0'])
    return {'candidate_labels_rechecked':checked,
            'bank_policy_scores_rechecked':len(SEEDS)*len(NAMES)*3}


def main():
    if (DEST/'audit.json').exists():raise RuntimeError('audit exists')
    parts={'source':source_audit(),'prepare':preparation_audit(),'score':score_audit()}
    write_json(DEST/'audit.json',{'passed':True,'parts':parts})
    print(json.dumps({'passed':True,'parts':parts},indent=2))


if __name__=='__main__':main()
