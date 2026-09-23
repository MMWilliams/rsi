"""Regenerate and independently rescore the focused-feedback transfer run."""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES,random_bank
from gated_ast_feedback import pools_for,public_block,BLOCK_AST,FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_probe_sensor_development import choose_probe
from ast_query_allocation_development import features
from cross_family_query_value_development import choose as fixed_choose
from cross_family_meta_improver_development import source_rows,select,values
from cross_family_meta_improver_transfer import stage_rows,interval
from focused_feedback_development import fit_weighted,grouped
from focused_feedback_transfer import DEST,PROTOCOL,SOURCE,SEEDS,NAMES,sha,scramble


def source_audit():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'focused_feedback_transfer.py')
    assert manifest['trainer_sha256']==sha(ROOT/'focused_feedback_development.py')
    assert manifest['source_records_sha256']==sha(SOURCE/'frozen_records.json')
    assert manifest['source_results_sha256']==sha(SOURCE/'results.json')
    source=source_rows();feedback=stage_rows('admission')
    e0=fit_weighted(source,[1]*len(source))
    mistakes=set()
    for group in grouped(feedback):
        ids=select(group,e0)
        mistakes|={r['id'] for r in group if r['id'] in ids and r['gain']<=0}
    models={'e0':e0,
            'ordinary_e6':fit_weighted(source+feedback,[1]*(len(source)+len(feedback))),
            'focused_e6':fit_weighted(source+feedback,[1]*len(source)+
                                      [4 if r['id'] in mistakes else 1 for r in feedback]),
            'scrambled_e6':fit_weighted(source+scramble(feedback),
                                       [1]*(len(source)+len(feedback)))}
    assert len(mistakes)==manifest['feedback_mistakes']
    assert models==json.loads((DEST/'models.json').read_text())
    assert manifest['models_sha256']==sha(DEST/'models.json')
    return {'models_rebuilt':len(models),'feedback_mistakes':len(mistakes)}


def prepare_audit():
    manifest=json.loads((DEST/'bank_manifest.json').read_text())
    assert tuple(manifest['seeds'])==SEEDS and manifest['tasks']==576
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'focused_feedback_transfer.py')
    assert manifest['models_sha256']==sha(DEST/'models.json')
    assert manifest['source_manifest_sha256']==sha(DEST/'source_manifest.json')
    assert manifest['frozen_records_sha256']==sha(DEST/'frozen_records.json')
    assert manifest['frozen_allocations_sha256']==sha(DEST/'frozen_allocations.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    expected=[{**t,'seed':seed} for seed in SEEDS
              for t in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    assert tasks==expected
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    rebuilt_base,rebuilt_wide,_=pools_for(tasks)
    assert rebuilt_base==base and rebuilt_wide==wide
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    public=[({'id':t['id'],'probe_inputs':[x for x,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs,public))==predicted
    records=json.loads((DEST/'frozen_records.json').read_text())
    evaluators=evaluator_models();replay=updated_model()
    for task,record in zip(tasks,records):
        key=task['id'];block=public_block(task);pool=wide.get(key,base[key])
        assert key==record['id'] and block==record['public_block']
        assert digest(pool)==record['pool_sha256']
        model=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,order=rank(task,pool,model)
        assert order==record['order'] and np.allclose(scores,record['scores'],atol=1e-6)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(pool))),[],'top20_entropy')
        assert first==record['first_probe']
        x=features(task,{'scores':scores,'order':order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        assert np.allclose(x,record['features'],atol=1e-6)
    by_id={r['id']:r for r in records}
    models=json.loads((DEST/'models.json').read_text())
    allocations={}
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        allocations[str(seed)]={name:sorted(select(group,models[name])) for name in NAMES}
        for mode in ('transform_mutation','random'):
            allocations[str(seed)][mode]=sorted(fixed_choose(group,mode))
    assert allocations==json.loads((DEST/'frozen_allocations.json').read_text())
    assert manifest['base_candidates']==sum(len(v) for v in base.values())
    assert manifest['extra_ast_candidates']==sum(len(v)-len(base[k]) for k,v in wide.items())
    assert manifest['candidate_output_cells']==sum(len(wide.get(t['id'],base[t['id']]))*8
                                                   for t in tasks)
    return {'tasks_regenerated':len(tasks),
            'candidate_pools_regenerated':len(base),
            'candidate_output_cells_rechecked':manifest['candidate_output_cells'],
            'allocations_rechecked':len(SEEDS)*len(next(iter(allocations.values())))}


def score_audit():
    saved=json.loads((DEST/'results.json').read_text())
    assert saved['bank_manifest_sha256']==sha(DEST/'bank_manifest.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    records=json.loads((DEST/'frozen_records.json').read_text())
    choices=json.loads((DEST/'frozen_allocations.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        labels=[int(bool(evaluate_program(r['program'],task['hidden'][8:]))) for r in pool]
        checked+=len(labels)
        order=record['order'];first=record['first_probe']
        matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matching if matching else set(range(len(pool)))
        selected=next(i for i in order if i in remaining)
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'public_block':record['public_block'],
                         'reachable':int(any(labels)),'zero':labels[order[0]],
                         'one':labels[selected],'selected_after_query':selected})
    assert outcomes==saved['tasks']
    summary=saved['summary'];assert checked==summary['candidate_labels_checked']
    by_id={o['id']:o for o in outcomes}
    banks=[]
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        correct={name:sum(r['one'] if r['id'] in set(ids) else r['zero'] for r in group)
                 for name,ids in choices[str(seed)].items()}
        gains=sorted((r['one']-r['zero'] for r in group),reverse=True)
        banks.append({'seed':seed,'reachable':sum(r['reachable'] for r in group),
                      'no_query':sum(r['zero'] for r in group),
                      'one_each':sum(r['one'] for r in group),
                      'hindsight_eight':sum(r['zero'] for r in group)+sum(gains[:8]),
                      'correct':correct})
    assert banks==saved['banks']
    totals={name:sum(b['correct'][name] for b in banks) for name in banks[0]['correct']}
    assert totals==summary['totals']
    assert summary['no_query']==sum(b['no_query'] for b in banks)
    assert summary['one_each']==sum(b['one_each'] for b in banks)
    assert summary['hindsight_eight']==sum(b['hindsight_eight'] for b in banks)
    models=json.loads((DEST/'models.json').read_text())
    truth=np.asarray([o['one']-o['zero'] for o in outcomes],float)
    mse={name:float(np.mean((values(model,records)-truth)**2))
         for name,model in models.items()}
    assert np.allclose([mse[n] for n in NAMES],
                       [summary['forecast_mse'][n] for n in NAMES],atol=1e-12)
    diffs=[b['correct']['focused_e6']-b['correct']['e0'] for b in banks]
    assert diffs==summary['focused_minus_e0_by_bank']
    assert summary['gate']['interval']==interval(diffs)
    assert summary['gate']['promote']==(sum(diffs)>=8 and sum(d>0 for d in diffs)>=8
        and sum(d<0 for d in diffs)<=2 and interval(diffs)[0]>0
        and totals['focused_e6']>totals['ordinary_e6']
        and totals['focused_e6']>totals['scrambled_e6'])
    return {'candidate_labels_rechecked':checked,'bank_policy_scores_rechecked':len(SEEDS)*6,
            'forecast_models_rechecked':len(models)}


def main():
    if (DEST/'audit.json').exists():raise RuntimeError('audit exists')
    parts={'source':source_audit(),'prepare':prepare_audit(),'score':score_audit()}
    write_json(DEST/'audit.json',{'passed':True,'parts':parts})
    print(json.dumps({'passed':True,'parts':parts},indent=2))


if __name__=='__main__':main()
