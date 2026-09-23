"""Prospective fixed-pool evaluator growth test with feedback controls."""
from __future__ import annotations

import hashlib
import json
import sys
import time
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


DEST=ROOT/'runs/focused-feedback-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-focused-feedback-transfer.md'
SOURCE=ROOT/'runs/cross-family-meta-improver-transfer-20260918/admission'
SEEDS=tuple(range(902486,902498))
NAMES=('e0','ordinary_e6','focused_e6','scrambled_e6')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def scramble(rows):
    result=[dict(r) for r in rows]
    for block in sorted({r['public_block'] for r in rows}):
        indexes=[i for i,r in enumerate(rows) if r['public_block']==block]
        for target,donor in zip(indexes,indexes[-1:]+indexes[:-1]):
            result[target]['gain']=rows[donor]['gain']
    return result


def freeze_source():
    if DEST.exists():raise RuntimeError('run exists')
    source=source_rows();feedback=stage_rows('admission')
    assert len(source)==576 and len(feedback)==288
    e0=fit_weighted(source,[1]*len(source))
    mistakes=set()
    for group in grouped(feedback):
        chosen=select(group,e0)
        mistakes.update(r['id'] for r in group if r['id'] in chosen and r['gain']<=0)
    models={'e0':e0,
            'ordinary_e6':fit_weighted(source+feedback,[1]*(len(source)+len(feedback))),
            'focused_e6':fit_weighted(source+feedback,[1]*len(source)+
                                      [4 if r['id'] in mistakes else 1 for r in feedback]),
            'scrambled_e6':fit_weighted(source+scramble(feedback),
                                       [1]*(len(source)+len(feedback)))}
    manifest={'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'focused_feedback_transfer.py'),
              'trainer_sha256':sha(ROOT/'focused_feedback_development.py'),
              'source_rows':len(source),'feedback_rows':len(feedback),
              'feedback_mistakes':len(mistakes),
              'source_records_sha256':sha(SOURCE/'frozen_records.json'),
              'source_results_sha256':sha(SOURCE/'results.json'),
              'source_features_sha256':sha(ROOT/'analysis/cross-family-probe-prior-development.json'),
              'seeds':SEEDS}
    write_json(DEST/'models.json',models)
    manifest['models_sha256']=sha(DEST/'models.json')
    write_json(DEST/'source_manifest.json',manifest)
    print(json.dumps(manifest,indent=2))


def freeze_banks():
    if (DEST/'frozen_allocations.json').exists():raise RuntimeError('already prepared')
    manifest=json.loads((DEST/'source_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'focused_feedback_transfer.py')
    assert manifest['models_sha256']==sha(DEST/'models.json')
    start=time.perf_counter()
    tasks=[{**t,'seed':seed} for seed in SEEDS
           for t in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]
    base,wide,times=pools_for(tasks)
    public=[({'id':t['id'],'probe_inputs':[text for text,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    evaluators=evaluator_models();replay=updated_model()
    records=[]
    for task in tasks:
        key=task['id'];block=public_block(task);pool=wide.get(key,base[key])
        model=replay if block==BLOCK_AST else evaluators[FIXED[block]]
        scores,order=rank(task,pool,model)
        first=choose_probe(key,predicted[key],order,scores,set(range(len(pool))),[],
                           'top20_entropy')
        x=features(task,{'scores':scores,'order':order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        records.append({'id':key,'seed':task['seed'],'family':task['family'],
                        'public_block':block,'pool_sha256':digest(pool),
                        'scores':scores,'order':order,'first_probe':first,
                        'features':x.tolist()})
    by_id={r['id']:r for r in records}
    models=json.loads((DEST/'models.json').read_text())
    allocations={}
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        allocations[str(seed)]={name:sorted(select(group,models[name])) for name in NAMES}
        for mode in ('transform_mutation','random'):
            allocations[str(seed)][mode]=sorted(fixed_choose(group,mode))
        assert all(len(ids)==8 for ids in allocations[str(seed)].values())
    bank_manifest={'seeds':SEEDS,'tasks':len(tasks),'calls_per_bank':8,
                   'protocol_sha256':sha(PROTOCOL),
                   'runner_sha256':sha(ROOT/'focused_feedback_transfer.py'),
                   'source_manifest_sha256':sha(DEST/'source_manifest.json'),
                   'models_sha256':sha(DEST/'models.json'),
                   'base_candidates':sum(len(v) for v in base.values()),
                   'extra_ast_candidates':sum(len(v)-len(base[k]) for k,v in wide.items()),
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
    bank_manifest['frozen_allocations_sha256']=sha(DEST/'frozen_allocations.json')
    bank_manifest['frozen_records_sha256']=sha(DEST/'frozen_records.json')
    write_json(DEST/'bank_manifest.json',bank_manifest)
    print(json.dumps(bank_manifest,indent=2))


def score_banks():
    if (DEST/'results.json').exists():raise RuntimeError('already scored')
    manifest=json.loads((DEST/'bank_manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'focused_feedback_transfer.py')
    assert manifest['models_sha256']==sha(DEST/'models.json')
    assert manifest['frozen_allocations_sha256']==sha(DEST/'frozen_allocations.json')
    assert manifest['frozen_records_sha256']==sha(DEST/'frozen_records.json')
    tasks=json.loads((DEST/'sealed_bank.json').read_text())
    base=json.loads((DEST/'base_pools.json').read_text())
    wide=json.loads((DEST/'ast_wide_pools.json').read_text())
    predicted=json.loads((DEST/'predicted_probe_outputs.json').read_text())
    records=json.loads((DEST/'frozen_records.json').read_text())
    choices=json.loads((DEST/'frozen_allocations.json').read_text())
    outcomes=[];labels_checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        assert key==record['id'] and digest(pool)==record['pool_sha256']
        labels=[int(bool(evaluate_program(row['program'],task['hidden'][8:]))) for row in pool]
        labels_checked+=len(labels)
        order=record['order'];first=record['first_probe']
        matching={i for i in range(len(pool)) if matrix[i][first]==task['hidden'][first][1]}
        remaining=matching if matching else set(range(len(pool)))
        selected=next(i for i in order if i in remaining)
        outcomes.append({'id':key,'seed':task['seed'],'family':task['family'],
                         'public_block':record['public_block'],
                         'reachable':int(any(labels)),'zero':labels[order[0]],
                         'one':labels[selected],'selected_after_query':selected})
    by_id={o['id']:o for o in outcomes};banks=[]
    for seed in SEEDS:
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        scores={name:sum(r['one'] if r['id'] in set(ids) else r['zero'] for r in group)
                for name,ids in choices[str(seed)].items()}
        gains=sorted((r['one']-r['zero'] for r in group),reverse=True)
        banks.append({'seed':seed,'reachable':sum(r['reachable'] for r in group),
                      'no_query':sum(r['zero'] for r in group),
                      'one_each':sum(r['one'] for r in group),
                      'hindsight_eight':sum(r['zero'] for r in group)+sum(gains[:8]),
                      'correct':scores})
    models=json.loads((DEST/'models.json').read_text())
    forecast={name:float(np.mean((values(model,records)-np.asarray(
        [o['one']-o['zero'] for o in outcomes],float))**2))
              for name,model in models.items()}
    diffs=[b['correct']['focused_e6']-b['correct']['e0'] for b in banks]
    totals={name:sum(b['correct'][name] for b in banks) for name in banks[0]['correct']}
    gate={'sum':sum(diffs),'positive_banks':sum(d>0 for d in diffs),
          'losing_banks':sum(d<0 for d in diffs),'interval':interval(diffs)}
    gate['promote']=(gate['sum']>=8 and gate['positive_banks']>=8 and
                     gate['losing_banks']<=2 and gate['interval'][0]>0 and
                     totals['focused_e6']>totals['ordinary_e6'] and
                     totals['focused_e6']>totals['scrambled_e6'])
    summary={'tasks':len(tasks),'banks':len(banks),'calls_per_policy':8*len(banks),
             'candidate_labels_checked':labels_checked,'totals':totals,
             'no_query':sum(b['no_query'] for b in banks),
             'one_each':sum(b['one_each'] for b in banks),
             'hindsight_eight':sum(b['hindsight_eight'] for b in banks),
             'reachable':sum(b['reachable'] for b in banks),
             'forecast_mse':forecast,'focused_minus_e0_by_bank':diffs,'gate':gate}
    write_json(DEST/'results.json',{'summary':summary,'banks':banks,'tasks':outcomes,
                                    'bank_manifest_sha256':sha(DEST/'bank_manifest.json')})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    {'source':freeze_source,'prepare':freeze_banks,'score':score_banks}[sys.argv[1]]()
