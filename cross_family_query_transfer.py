"""Fresh fixed-total output-query allocation across six program mechanisms."""
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
from ast_query_allocation_development import features,fit,predict
from cross_family_query_value_development import (rows_for,matrix,choose,
    CONTROLS,SOURCES)


DEST=ROOT/'runs/cross-family-query-transfer-20260918'
PROTOCOL=ROOT/'EXPERIMENT-cross-family-query-transfer.md'
TEMP=ROOT/'analysis/temperature-ranker-development.json'
RANKER=ROOT/'analysis/ast-feedback-replay-model.json'
PANELS={'a':tuple(range(902408,902414)),
        'b':tuple(range(902414,902420))}
LEARNED=('family_mean','basic_10','family_10','interaction_10','interaction_100')
POLICIES=(*CONTROLS,*LEARNED)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for(panel):
    return [{**task,'seed':seed} for seed in PANELS[panel]
            for task in random_bank(seed,48,FAMILIES,visible=1,hidden=23)]


def train_models():
    rows=rows_for()
    y=np.asarray([r['gain'] for r in rows],float)
    models={}
    for name in LEARNED:
        if name=='family_mean':
            models[name]={'kind':'family_mean',
                          'rates':{f:(sum(r['gain'] for r in rows if r['family']==f)+1)/
                                   (sum(r['family']==f for r in rows)+2)
                                   for f in FAMILIES}}
        else:
            kind,penalty=name.rsplit('_',1)
            fitted=fit(matrix(rows,kind),y,np.zeros(len(rows)),float(penalty))
            models[name]={'kind':kind,'penalty':float(penalty),
                          'params':[v.tolist() for v in fitted]}
    return models


def model_values(model,rows):
    if model['kind']=='family_mean':
        return np.asarray([model['rates'][r['family']] for r in rows])
    params=tuple(np.asarray(v,float) for v in model['params'])
    return predict(params,matrix(rows,model['kind']))[0]


def allocations(tasks,records,models):
    by_id={r['id']:r for r in records};result={}
    for seed in sorted({t['seed'] for t in tasks}):
        group=[by_id[t['id']] for t in tasks if t['seed']==seed]
        assert len(group)==48
        choices={name:sorted(choose(group,name)) for name in CONTROLS}
        for name in LEARNED:
            values=model_values(models[name],group)
            choices[name]=sorted(choose(group,name,values))
        assert all(len(v)==8 for v in choices.values())
        result[str(seed)]=choices
    return result


def prepare_models():
    if DEST.exists():raise RuntimeError('run already exists')
    models=train_models()
    source={'protocol_sha256':sha(PROTOCOL),
            'development_sha256':sha(ROOT/'analysis/cross-family-query-value-development.json'),
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in SOURCES},
            'training_tasks':576}
    write_json(DEST/'source_manifest.json',source)
    write_json(DEST/'frozen_models.json',models)
    return {'models':tuple(models),'source_tasks':576,
            'model_sha256':sha(DEST/'frozen_models.json')}


def prepare_stage(panel):
    directory=DEST/panel
    if directory.exists():raise RuntimeError(f'{panel} already prepared')
    start=time.perf_counter()
    tasks=tasks_for(panel)
    base,wide,times=pools_for(tasks)
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             wide.get(t['id'],base[t['id']])) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    models=evaluator_models();replay=updated_model();records=[]
    for task in tasks:
        key=task['id'];block=public_block(task);rows=wide.get(key,base[key])
        model=replay if block==BLOCK_AST else models[FIXED[block]]
        scores,order=rank(task,rows,model)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(rows))),[],'top20_entropy')
        x=features(task,{'scores':scores,'order':order,
                         'first_probe':{'top20_entropy':first}},predicted[key])
        records.append({'id':key,'seed':task['seed'],'family':task['family'],
                        'public_block':block,'base_sha256':digest(base[key]),
                        'pool_sha256':digest(rows),'scores':scores,'order':order,
                        'first_probe':first,'features':x.tolist()})
    frozen=json.loads((DEST/'frozen_models.json').read_text())
    choices=allocations(tasks,records,frozen)
    manifest={'panel':panel,'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'cross_family_query_transfer.py'),
              'sensor_sha256':sha(ROOT/'ast_probe_sensor_development.py'),
              'temperature_sha256':sha(TEMP),'ranker_sha256':sha(RANKER),
              'models_sha256':sha(DEST/'frozen_models.json'),
              'seeds':PANELS[panel],'tasks':len(tasks),'calls_per_bank':8,
              'base_candidates':sum(len(v) for v in base.values()),
              'ast_wide_candidates':sum(len(v) for v in wide.values()),
              'candidate_output_cells':sum(len(wide.get(t['id'],base[t['id']]))*8
                                           for t in tasks),
              'generation_seconds':sum(times.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(directory/'sealed_bank.json',tasks)
    write_json(directory/'base_pools.json',base)
    write_json(directory/'ast_wide_pools.json',wide)
    write_json(directory/'predicted_probe_outputs.json',predicted)
    write_json(directory/'frozen_records.json',records)
    write_json(directory/'frozen_allocations.json',choices)
    write_json(directory/'manifest.json',manifest)
    return manifest


def score_stage(panel):
    directory=DEST/panel
    if (directory/'results.json').exists():raise RuntimeError(f'{panel} already scored')
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'cross_family_query_transfer.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['temperature_sha256']==sha(TEMP)
    assert manifest['ranker_sha256']==sha(RANKER)
    assert manifest['models_sha256']==sha(DEST/'frozen_models.json')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    base=json.loads((directory/'base_pools.json').read_text())
    wide=json.loads((directory/'ast_wide_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    choices=json.loads((directory/'frozen_allocations.json').read_text())
    outcomes=[];checked=0
    for task,record in zip(tasks,records):
        key=task['id'];pool=wide.get(key,base[key]);matrix=predicted[key]
        assert record['id']==key and record['pool_sha256']==digest(pool)
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
    by_id={r['id']:r for r in outcomes}
    banks=[]
    for seed in PANELS[panel]:
        group=[r for r in outcomes if r['seed']==seed]
        scores={name:sum(r['one'] if r['id'] in set(selected) else r['zero']
                         for r in group) for name,selected in choices[str(seed)].items()}
        hindsight=sum(r['zero'] for r in group)+sum(sorted(
            (int(r['one'])-int(r['zero']) for r in group),reverse=True)[:8])
        banks.append({'seed':seed,'no_query':sum(r['zero'] for r in group),
                      'one_each_all':sum(r['one'] for r in group),
                      'hindsight_8':hindsight,'correct':scores})
    summary={'panel':panel,'tasks':len(tasks),'candidate_labels_checked':checked,
             'reachable':sum(r['reachable'] for r in outcomes),
             'no_query':sum(b['no_query'] for b in banks),
             'one_each_all':sum(b['one_each_all'] for b in banks),
             'hindsight_8':sum(b['hindsight_8'] for b in banks),
             'logical_calls_per_policy':8*len(banks),
             'correct':{name:sum(b['correct'][name] for b in banks) for name in POLICIES},
             'by_family':{f:{'zero':sum(r['zero'] for r in outcomes if r['family']==f),
                             'one':sum(r['one'] for r in outcomes if r['family']==f),
                             'gains':sum(r['one'] and not r['zero'] for r in outcomes
                                         if r['family']==f),
                             'harms':sum(r['zero'] and not r['one'] for r in outcomes
                                         if r['family']==f)} for f in FAMILIES},
             'by_bank':banks}
    write_json(directory/'results.json',{'summary':summary,'tasks':outcomes})
    return summary


def interval(diffs):
    counts={0:1}
    for _ in diffs:
        nxt={}
        for total,count in counts.items():
            for d in diffs:nxt[total+d]=nxt.get(total+d,0)+count
        counts=nxt
    total=len(diffs)**len(diffs);cumulative=0;lower=upper=None
    for value,count in sorted(counts.items()):
        cumulative+=count
        if lower is None and cumulative/total>=.025:lower=value
        if upper is None and cumulative/total>=.975:upper=value
    return [lower,upper]


def summarize():
    panels={name:json.loads((DEST/name/'results.json').read_text())['summary']
            for name in PANELS}
    banks=panels['a']['by_bank']+panels['b']['by_bank']
    correct={name:sum(b['correct'][name] for b in banks) for name in POLICIES}
    fixed_best=max(CONTROLS,key=lambda name:correct[name])
    differences=[b['correct']['interaction_100']-b['correct'][fixed_best] for b in banks]
    ci=interval(differences)
    gate={'strongest_fixed':fixed_best,'differences':differences,
          'positive_banks':sum(d>0 for d in differences),
          'bank_bootstrap_95_sum':ci,
          'panels_nonnegative':all(panels[p]['correct']['interaction_100']>=
                                   panels[p]['correct'][fixed_best] for p in PANELS),
          'passed':sum(d>0 for d in differences)>=8 and ci[0]>0 and
                   all(panels[p]['correct']['interaction_100']>=
                       panels[p]['correct'][fixed_best] for p in PANELS)}
    return {'scope':'fresh fixed-total cross-family output-query transfer',
            'tasks':sum(p['tasks'] for p in panels.values()),
            'logical_calls_per_policy':sum(p['logical_calls_per_policy'] for p in panels.values()),
            'correct':correct,'no_query':sum(p['no_query'] for p in panels.values()),
            'one_each_all':sum(p['one_each_all'] for p in panels.values()),
            'hindsight_8':sum(p['hindsight_8'] for p in panels.values()),
            'reachable':sum(p['reachable'] for p in panels.values()),
            'by_panel':{name:{'correct':p['correct'],'reachable':p['reachable']}
                        for name,p in panels.items()},'primary_gate':gate,
            'by_bank':banks}


def final():
    summary=summarize()
    write_json(DEST/'summary.json',summary)
    return {'correct':summary['correct'],'primary_gate':summary['primary_gate'],
            'no_query':summary['no_query'],'hindsight_8':summary['hindsight_8']}


if __name__=='__main__':
    actions={'models':prepare_models,'prepare_a':lambda:prepare_stage('a'),
             'score_a':lambda:score_stage('a'),'prepare_b':lambda:prepare_stage('b'),
             'score_b':lambda:score_stage('b'),'final':final}
    print(json.dumps(actions[sys.argv[1]](),indent=2))
