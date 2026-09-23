"""Independent source, preparation and oracle replay for cross-family query transfer."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_family_query_value_development import SOURCES,choose,CONTROLS
from cross_family_query_transfer import (DEST,PROTOCOL,TEMP,RANKER,PANELS,
    LEARNED,POLICIES,sha,tasks_for,train_models,model_values,allocations,summarize)
from seed_casebanks import FAMILIES


def source():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['development_sha256']==sha(ROOT/'analysis/cross-family-query-value-development.json')
    assert manifest['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in SOURCES}
    assert train_models()==json.loads((DEST/'frozen_models.json').read_text())
    result={'passed':True,'source_tasks':576,'source_files_rechecked':len(SOURCES),
            'models_retrained':len(LEARNED)}
    write_json(DEST/'audit_source.json',result)
    print(json.dumps(result,indent=2))


def read(panel):
    directory=DEST/panel
    return tuple(json.loads((directory/name).read_text()) for name in (
        'manifest.json','sealed_bank.json','base_pools.json','ast_wide_pools.json',
        'predicted_probe_outputs.json','frozen_records.json','frozen_allocations.json'))


def check_manifest(manifest):
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'cross_family_query_transfer.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['temperature_sha256']==sha(TEMP)
    assert manifest['ranker_sha256']==sha(RANKER)
    assert manifest['models_sha256']==sha(DEST/'frozen_models.json')


def prepare(panel):
    manifest,tasks,base,wide,predicted,records,choices=read(panel)
    check_manifest(manifest)
    assert tasks==tasks_for(panel)
    regenerated,regenerated_wide,_=pools_for(tasks)
    assert regenerated==base and regenerated_wide==wide
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    evaluators=evaluator_models();replay=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];block=public_block(task);rows=wide.get(key,base[key])
        assert key==record['id'] and block==record['public_block']
        assert record['base_sha256']==digest(base[key])
        assert record['pool_sha256']==digest(rows)
        model=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,order=rank(task,rows,model)
        assert order==record['order'] and np.allclose(scores,record['scores'],atol=1e-6)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(rows))),[],'top20_entropy')
        assert first==record['first_probe']
        x=features(task,{'scores':scores,'order':order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        assert np.allclose(x,record['features'],atol=1e-6)
    models=json.loads((DEST/'frozen_models.json').read_text())
    assert allocations(tasks,records,models)==choices
    result={'passed':True,'panel':panel,'tasks':len(tasks),
            'base_candidates_rechecked':sum(len(v) for v in base.values()),
            'ast_wide_candidates_rechecked':sum(len(v) for v in wide.values()),
            'predicted_output_cells_rechecked':sum(len(wide.get(t['id'],base[t['id']]))*8
                                                 for t in tasks),
            'allocations_rechecked':len(PANELS[panel])*len(POLICIES)}
    write_json(DEST/f'audit_prepare_{panel}.json',result)
    print(json.dumps(result,indent=2))


def score(panel):
    manifest,tasks,base,wide,predicted,records,choices=read(panel)
    check_manifest(manifest)
    saved=json.loads((DEST/panel/'results.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:]))
                for row in pool]
        checked+=len(labels)
        order=record['order'];first=record['first_probe']
        matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matching if matching else set(range(len(pool)))
        selected=next(i for i in order if i in remaining)
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'reachable':any(labels),'zero':bool(labels[order[0]]),
                         'one':bool(labels[selected]),'selected_after_query':selected})
    assert outcomes==saved['tasks']
    for bank in saved['summary']['by_bank']:
        group=[r for r in outcomes if r['seed']==bank['seed']]
        assert len(group)==48
        assert bank['no_query']==sum(r['zero'] for r in group)
        assert bank['one_each_all']==sum(r['one'] for r in group)
        hindsight=sum(r['zero'] for r in group)+sum(sorted(
            (int(r['one'])-int(r['zero']) for r in group),reverse=True)[:8])
        assert bank['hindsight_8']==hindsight
        for policy,ids in choices[str(bank['seed'])].items():
            assert len(ids)==8 and len(set(ids))==8
            selected=set(ids)
            actual=sum(r['one'] if r['id'] in selected else r['zero'] for r in group)
            assert actual==bank['correct'][policy]
    for family in FAMILIES:
        group=[r for r in outcomes if r['family']==family]
        report=saved['summary']['by_family'][family]
        assert report['zero']==sum(r['zero'] for r in group)
        assert report['one']==sum(r['one'] for r in group)
        assert report['gains']==sum(r['one'] and not r['zero'] for r in group)
        assert report['harms']==sum(r['zero'] and not r['one'] for r in group)
    result={'passed':True,'panel':panel,'tasks':len(tasks),
            'candidate_labels_rechecked':checked,
            'bank_policy_scores_rechecked':len(PANELS[panel])*len(POLICIES)}
    write_json(DEST/f'audit_score_{panel}.json',result)
    print(json.dumps(result,indent=2))


def final():
    names=('source','prepare_a','score_a','prepare_b','score_b')
    parts={name:json.loads((DEST/f'audit_{name}.json').read_text()) for name in names}
    assert all(part['passed'] for part in parts.values())
    assert summarize()==json.loads((DEST/'summary.json').read_text())
    result={'passed':True,**parts}
    write_json(DEST/'audit.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    actions={'source':source,'prepare_a':lambda:prepare('a'),
             'score_a':lambda:score('a'),'prepare_b':lambda:prepare('b'),
             'score_b':lambda:score('b'),'final':final}
    actions[sys.argv[1]]()
