"""Protected sequential AST query feedback with parent/child checkpoints."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT,digest,write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import pools_for,updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs,rank
from ast_query_allocation_development import features,predict,allocate,fixed
from ast_value_feature_development import load_rows
from adaptive_ast_query_development import train,simulate,initial_features
from contextual_ast_improver_v2 import stage_rows as prior_stage_rows
from incremental_ast_improver import task_banks


DEST=ROOT/'runs/adaptive-ast-improver-20260918'
PROTOCOL=ROOT/'EXPERIMENT-adaptive-ast-improver.md'
DEVELOPMENT=ROOT/'analysis/adaptive-ast-query-development.json'
RANKER=ROOT/'analysis/ast-feedback-replay-model.json'
PREVIOUS=ROOT/'runs/contextual-ast-improver-v2-20260918'
MIXED_A=tuple(range(902384,902387))
AST_A=tuple(range(902387,902390))
MIXED_T=tuple(range(902390,902396))
AST_T=tuple(range(902396,902402))
MODELS=('conditional0','conditional1','scrambled','duplicate')
FIXED=('one_each','random','entropy','disagreement')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tables():
    rows=load_rows()
    added=prior_stage_rows('admission')+prior_stage_rows('transfer')
    assert len(rows)==384 and len(added)==144
    assert len({r['task']['id'] for r in rows+added})==528
    scrambled=[dict(r) for r in added]
    for stream in ('mixed','ast_only'):
        idx=[i for i,r in enumerate(added) if r['stream']==stream]
        for target,source in zip(idx,idx[-1:]+idx[:-1]):
            scrambled[target]={**scrambled[target],'correct':added[source]['correct']}
    return {'conditional0':rows,'conditional1':rows+added,
            'scrambled':rows+scrambled,'duplicate':rows+rows[:144]}


def serialize(model,source_tasks):
    return {'source_tasks':source_tasks,
            'prior':[v.tolist() for v in model[0]],
            'conditional':[v.tolist() for v in model[1]]}


def unserialize(raw):
    return (tuple(np.asarray(v,dtype=float) for v in raw['prior']),
            tuple(np.asarray(v,dtype=float) for v in raw['conditional']))


def models_for(tables):
    return {name:serialize(train(tables[name]),len(tables[name])) for name in MODELS}


def source_files():
    from contextual_ast_improver_v2 import source_paths
    paths=source_paths()
    for stage in ('admission','transfer'):
        directory=PREVIOUS/stage
        paths.extend(directory/name for name in ('sealed_bank.json','frozen_records.json',
                    'predicted_probe_outputs.json','results.json'))
    return paths


def stage_rows(stage):
    directory=DEST/stage
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert all(t['id']==r['id']==o['id'] for t,r,o in zip(tasks,records,outcomes))
    return [{'task':task,
             'record':{**record,'first_probe':{'top20_entropy':record['first_probe']}},
             'matrix':predicted[task['id']],
             'correct':[int(v) for v in outcome['correct_by_calls']],
             'seed':task['seed'],'stream':task['stream'],'source':stage}
            for task,record,outcome in zip(tasks,records,outcomes)]


def static_allocations(tasks,records,predicted,models):
    by_id={r['id']:r for r in records};result={}
    for seed in sorted({t['seed'] for t in tasks}):
        group=[t for t in tasks if t['seed']==seed]
        assert len(group)==8
        ids=[t['id'] for t in group]
        rows=[{'task':task,
               'record':{**by_id[task['id']],
                         'first_probe':{'top20_entropy':by_id[task['id']]['first_probe']}},
               'matrix':predicted[task['id']]} for task in group]
        x=np.stack([initial_features(row) for row in rows])
        choices={name:dict(zip(ids,fixed(ids,x,8,name))) for name in FIXED}
        for name,model_name in (('static0','conditional0'),('static1','conditional1')):
            p1,p2=predict(unserialize(models[model_name])[0],x)
            choices[name]=dict(zip(ids,allocate(p1,p2,8)))
        result[str(seed)]=choices
    return result


def prepare_stage(stage,mixed,ast,models):
    directory=DEST/stage
    if directory.exists():raise RuntimeError(f'{stage} already prepared')
    start=time.perf_counter()
    tasks=task_banks(mixed,ast)
    pools,times=pools_for(tasks)
    public=[({'id':t['id'],'probe_inputs':[v for v,_ in t['hidden'][:8]]},
             pools[t['id']]) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    ranker=updated_model();records=[]
    for task in tasks:
        key=task['id'];rows=pools[key]
        scores,order=rank(task,rows,ranker)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(rows))),[],'top20_entropy')
        records.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                        'pool_sha256':digest(rows),'scores':scores,'order':order,
                        'first_probe':first})
    static=static_allocations(tasks,records,predicted,models)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    manifest={'stage':stage,'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'adaptive_ast_improver.py'),
              'sensor_sha256':sha(ROOT/'ast_probe_sensor_development.py'),
              'ranker_sha256':sha(RANKER),'models_sha256':sha(model_path),
              'gate_sha256':sha(DEST/'admission_gate.json') if stage=='transfer' else None,
              'mixed_seeds':mixed,'ast_seeds':ast,'tasks':len(tasks),
              'calls_per_bank':8,'candidate_count':sum(len(v) for v in pools.values()),
              'predicted_output_cells':sum(len(v)*8 for v in pools.values()),
              'generation_seconds':sum(times.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(directory/'sealed_bank.json',tasks)
    write_json(directory/'candidate_pools.json',pools)
    write_json(directory/'predicted_probe_outputs.json',predicted)
    write_json(directory/'frozen_records.json',records)
    write_json(directory/'frozen_static_allocations.json',static)
    write_json(directory/'manifest.json',manifest)
    return manifest


def prepare_parents():
    if DEST.exists():raise RuntimeError('run already exists')
    tables=source_tables()
    parent=models_for(tables)
    manifest={'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in source_files()},
              'protocol_sha256':sha(PROTOCOL),
              'development_sha256':sha(DEVELOPMENT),
              'source_tasks':{name:len(tables[name]) for name in MODELS}}
    write_json(DEST/'source_manifest.json',manifest)
    write_json(DEST/'parent_models.json',parent)
    return prepare_stage('admission',MIXED_A,AST_A,parent)


def outcome(task,record,rows,matrix):
    key=task['id'];order=record['order'];scores=record['scores']
    labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
    correct=[bool(labels[order[0]])];remaining=set(range(len(rows)));used=[]
    for n in (1,2):
        j=record['first_probe'] if n==1 else choose_probe(
            key,matrix,order,scores,remaining,used,'top20_entropy')
        used.append(j)
        matched={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
        if matched:remaining=matched
        selected=next((i for i in order if i in remaining),order[0])
        correct.append(bool(labels[selected]))
    return {'id':key,'seed':task['seed'],'stream':task['stream'],
            'reachable':any(labels),'correct_by_calls':correct,'query_indices':used}


def score_stage(stage):
    directory=DEST/stage
    if (directory/'results.json').exists():raise RuntimeError(f'{stage} already scored')
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'adaptive_ast_improver.py')
    assert manifest['sensor_sha256']==sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['ranker_sha256']==sha(RANKER)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    assert manifest['models_sha256']==sha(model_path)
    if stage=='transfer':assert manifest['gate_sha256']==sha(DEST/'admission_gate.json')
    models=json.loads(model_path.read_text())
    gate=json.loads((DEST/'admission_gate.json').read_text()) if stage=='transfer' else None
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    pools=json.loads((directory/'candidate_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    static=json.loads((directory/'frozen_static_allocations.json').read_text())
    outcomes=[]
    for task,record in zip(tasks,records):
        key=task['id'];rows=pools[key]
        assert key==record['id'] and record['pool_sha256']==digest(rows)
        outcomes.append(outcome(task,record,rows,predicted[key]))
    by_id={o['id']:o for o in outcomes}
    banks=[];traces={}
    for seed in sorted({t['seed'] for t in tasks}):
        group=[t for t in tasks if t['seed']==seed]
        bank=[{'task':t,'record':{**records[tasks.index(t)],
                                  'first_probe':{'top20_entropy':records[tasks.index(t)]['first_probe']}},
               'matrix':predicted[t['id']],'correct':[0,0,0]} for t in group]
        scores={name:sum(by_id[key]['correct_by_calls'][count]
                         for key,count in mapping.items())
                for name,mapping in static[str(seed)].items()}
        trace_bank={}
        for name,model_name,mode in (
            ('conditional0','conditional0','conditional'),
            ('conditional1','conditional1','conditional'),
            ('scrambled','scrambled','conditional'),
            ('duplicate','duplicate','conditional'),
            ('prior1','conditional1','prior')):
            simulation=simulate(bank,unserialize(models[model_name]),mode)
            actions=dict(zip([t['id'] for t in group],simulation['actions']))
            scores[name]=sum(by_id[key]['correct_by_calls'][count]
                             for key,count in actions.items())
            trace_bank[name]={'actions':actions,'trace':simulation['trace']}
        if gate is not None:
            scores['protected_conditional1']=(scores['conditional1']
                if gate['admit'] else scores['one_each'])
        traces[str(seed)]=trace_bank
        bank_outcomes=[by_id[t['id']] for t in group]
        banks.append({'seed':seed,'stream':group[0]['stream'],
                      'reachable':sum(o['reachable'] for o in bank_outcomes),
                      'no_query':sum(o['correct_by_calls'][0] for o in bank_outcomes),
                      'correct':scores})
    names=tuple(banks[0]['correct'])
    summary={'stage':stage,'tasks':len(tasks),
             'logical_calls_per_policy':8*len(banks),
             'acquisition_probe_calls':2*len(tasks) if stage=='admission' else 0,
             'reachable':sum(o['reachable'] for o in outcomes),
             'no_query':sum(b['no_query'] for b in banks),
             'correct':{name:sum(b['correct'][name] for b in banks) for name in names},
             'by_bank':banks}
    write_json(directory/'adaptive_traces.json',traces)
    write_json(directory/'results.json',{'summary':summary,'tasks':outcomes})
    return summary


def gate_for(summary):
    differences=[b['correct']['conditional1']-b['correct']['one_each']
                 for b in summary['by_bank']]
    return {'differences':differences,'sum':sum(differences),
            'positive_banks':sum(d>0 for d in differences),
            'losing_banks':sum(d<0 for d in differences),
            'admit':sum(differences)>=3 and sum(d>0 for d in differences)>=2
                    and sum(d<0 for d in differences)<=1}


def train_children():
    if (DEST/'child_models.json').exists():raise RuntimeError('children already exist')
    tables=source_tables();extra=stage_rows('admission')
    children=models_for({name:tables[name]+extra for name in MODELS})
    summary=json.loads((DEST/'admission/results.json').read_text())['summary']
    gate=gate_for(summary)
    write_json(DEST/'admission_gate.json',gate)
    write_json(DEST/'child_models.json',children)
    write_json(DEST/'child_training.json',{
        'admission_results_sha256':sha(DEST/'admission/results.json'),
        'source_manifest_sha256':sha(DEST/'source_manifest.json'),
        'new_task_ids':[r['task']['id'] for r in extra]})
    return {'gate':gate,'child_tasks':{name:children[name]['source_tasks'] for name in MODELS}}


def prepare_transfer():
    models=json.loads((DEST/'child_models.json').read_text())
    assert (DEST/'admission_gate.json').exists()
    return prepare_stage('transfer',MIXED_T,AST_T,models)


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
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    transfer=json.loads((DEST/'transfer/results.json').read_text())['summary']
    gate=json.loads((DEST/'admission_gate.json').read_text())
    fixed_best=max(FIXED,key=lambda name:transfer['correct'][name])
    diffs=[b['correct']['conditional1']-b['correct']['conditional0']
           for b in transfer['by_bank']]
    ci=interval(diffs)
    passed=sum(d>0 for d in diffs)>=8 and ci[0]>0 and gate['admit']
    passed=passed and transfer['correct']['protected_conditional1']>transfer['correct'][fixed_best]
    passed=passed and all(transfer['correct']['conditional1']>transfer['correct'][n]
                          for n in ('scrambled','duplicate'))
    return {'scope':'synthetic AST sequential fixed-design improver',
            'admission':admission,'transfer':transfer,'admission_gate':gate,
            'strongest_fixed':fixed_best,
            'child_growth':{'by_bank':diffs,'positive_banks':sum(d>0 for d in diffs),
                            'bank_bootstrap_95_sum':ci,'passed':passed},
            'source_tasks':{'p0':384,'p1':528},
            'new_admission_tasks_shared':48,'new_acquisition_outputs_shared':96,
            'transfer_calls_per_policy':96}


def score_transfer():
    score_stage('transfer')
    result=summarize()
    write_json(DEST/'summary.json',result)
    return {'correct':result['transfer']['correct'],
            'admission_gate':result['admission_gate'],
            'child_growth':result['child_growth']}


if __name__=='__main__':
    actions={'prepare_parents':prepare_parents,'score_admission':lambda:score_stage('admission'),
             'train_children':train_children,'prepare_transfer':prepare_transfer,
             'score_transfer':score_transfer}
    print(json.dumps(actions[sys.argv[1]](),indent=2))
