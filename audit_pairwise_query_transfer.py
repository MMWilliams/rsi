"""Independent task, candidate, allocation and oracle replay for pairwise transfer."""
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
from cross_family_meta_improver_development import source_rows,fit_method,values
from cross_family_meta_improver_transfer import stage_rows,interval
from focused_feedback_development import fit_weighted
from pairwise_query_ranking_development import train_pairwise
from pairwise_query_transfer import DEST,PROTOCOL,SEEDS,NAMES,META,sha,scrambled,choose


def source_audit():
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'pairwise_query_transfer.py')
    assert manifest['trainer_sha256']==sha(ROOT/'pairwise_query_ranking_development.py')
    assert all(sha(ROOT/path)==digest for path,digest in manifest['source_sha256'].items())
    assert tuple(manifest['seeds'])==SEEDS and tuple(manifest['names'])==NAMES
    source=source_rows();admission=stage_rows('admission')
    added=admission+stage_rows('a')+stage_rows('b')
    assert len(source)==manifest['source_rows']==576
    assert len(added)==manifest['feedback_rows']==864
    e0=fit_weighted(source,[1]*len(source))
    rebuilt={'e0':e0,'p0':train_pairwise(source,.001,False,e0),
             'p6':train_pairwise(source+admission,.001,False,e0),
             'p18':train_pairwise(source+added,.001,False,e0),
             'scrambled_p18':train_pairwise(source+scrambled(added),.001,False,e0),
             'ridge18_10':fit_method(source+added,'interaction_10'),
             'ridge18_100':fit_method(source+added,'interaction_100')}
    assert rebuilt==json.loads((DEST/'models.json').read_text())
    assert sha(DEST/'models.json')==manifest['models_sha256']
    return {'models_rebuilt':len(rebuilt),'source_rows':len(source),
            'feedback_rows':len(added)}


def preparation_audit():
    manifest=json.loads((DEST/'bank_manifest.json').read_text())
    assert tuple(manifest['seeds'])==SEEDS and manifest['tasks']==576
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'pairwise_query_transfer.py')
    assert manifest['source_manifest_sha256']==sha(DEST/'source_manifest.json')
    assert manifest['models_sha256']==sha(DEST/'models.json')
    assert manifest['frozen_allocations_sha256']==sha(DEST/'frozen_allocations.json')
    assert manifest['frozen_records_sha256']==sha(DEST/'frozen_records.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    expected=[{**t,'seed':seed} for seed in SEEDS
              for t in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    assert tasks==expected
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    regenerated_base,regenerated_wide,_=pools_for(tasks)
    assert base==regenerated_base and wide==regenerated_wide
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
        feature=features(task,{'scores':scores,'order':order,
                               'first_probe':{'top20_entropy':first}},predicted[key])
        assert np.allclose(feature,record['features'],atol=1e-6)
    lookup={r['id']:r for r in records}
    models=json.loads((DEST/'models.json').read_text())
    allocations={}
    for seed in SEEDS:
        group=[lookup[t['id']] for t in tasks if t['seed']==seed]
        allocations[str(seed)]={name:sorted(choose(group,models[name])) for name in NAMES}
        for mode in ('transform_mutation','random'):
            allocations[str(seed)][mode]=sorted(fixed_choose(group,mode))
    assert allocations==json.loads((DEST/'frozen_allocations.json').read_text())
    assert manifest['base_candidates']==sum(len(v) for v in base.values())
    assert manifest['extra_ast_candidates']==sum(len(v)-len(base[k]) for k,v in wide.items())
    assert manifest['candidate_output_cells']==sum(len(wide.get(t['id'],base[t['id']]))*8
                                                   for t in tasks)
    return {'tasks_regenerated':len(tasks),'candidate_pools_regenerated':len(base),
            'predicted_output_cells_rechecked':manifest['candidate_output_cells'],
            'bank_policy_allocations_rechecked':len(SEEDS)*(len(NAMES)+2)}


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
    lookup={o['id']:o for o in outcomes};banks=[]
    for seed in SEEDS:
        group=[lookup[t['id']] for t in tasks if t['seed']==seed]
        correct={name:sum(r['one'] if r['id'] in set(ids) else r['zero'] for r in group)
                 for name,ids in allocations[str(seed)].items()}
        gains=sorted((r['one']-r['zero'] for r in group),reverse=True)
        banks.append({'seed':seed,'reachable':sum(r['reachable'] for r in group),
                      'no_query':sum(r['zero'] for r in group),
                      'one_each':sum(r['one'] for r in group),
                      'hindsight_eight':sum(r['zero'] for r in group)+sum(gains[:8]),
                      'correct':correct})
    assert banks==saved['banks']
    totals={name:sum(b['correct'][name] for b in banks) for name in banks[0]['correct']}
    assert totals==summary['totals']
    assert summary['reachable']==sum(b['reachable'] for b in banks)
    assert summary['no_query']==sum(b['no_query'] for b in banks)
    assert summary['one_each']==sum(b['one_each'] for b in banks)
    assert summary['hindsight_eight']==sum(b['hindsight_eight'] for b in banks)
    models=json.loads((DEST/'models.json').read_text())
    truth=np.asarray([o['one']-o['zero'] for o in outcomes],float)
    mse={name:float(np.mean((values(model,records)-truth)**2))
         for name,model in models.items() if model['kind']!='pairwise'}
    assert np.allclose([mse[k] for k in mse],
                       [summary['forecast_mse'][k] for k in mse],atol=1e-12)
    family_calls={name:{family:sum(r['family']==family and
        r['id'] in {key for ids in allocations.values() for key in ids[name]}
        for r in outcomes) for family in FAMILIES} for name in allocations[str(SEEDS[0])].keys()}
    assert family_calls==summary['family_calls']
    diffs=[b['correct']['p18']-b['correct']['p0'] for b in banks]
    assert diffs==summary['p18_minus_p0_by_bank']
    gate=summary['gate']
    assert gate['sum']==sum(diffs) and gate['interval']==interval(diffs)
    assert gate['positive_banks']==sum(d>0 for d in diffs)
    assert gate['losing_banks']==sum(d<0 for d in diffs)
    assert gate['promote']==(sum(diffs)>=8 and sum(d>0 for d in diffs)>=8 and
        sum(d<0 for d in diffs)<=2 and interval(diffs)[0]>0 and
        totals['p18']>totals['scrambled_p18'] and
        totals['p18']>max(totals['ridge18_10'],totals['ridge18_100']))
    return {'candidate_labels_rechecked':checked,
            'bank_policy_scores_rechecked':len(SEEDS)*(len(NAMES)+2),
            'forecast_models_rechecked':len(mse)}


def main():
    if (DEST/'audit.json').exists():raise RuntimeError('audit exists')
    parts={'source':source_audit(),'prepare':preparation_audit(),'score':score_audit()}
    write_json(DEST/'audit.json',{'passed':True,'parts':parts})
    print(json.dumps({'passed':True,'parts':parts},indent=2))


if __name__=='__main__':main()
