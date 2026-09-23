"""Fresh parent/child transfer for two AST query-value model families."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import pools_for, updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs, rank
from ast_query_allocation_development import features, fit, predict, allocate, fixed
from ast_value_feature_development import load_rows, expanded, rbf_fit, rbf_predict
from incremental_ast_improver import task_banks


DEST = ROOT/'runs/contextual-ast-improver-v2-20260918'
RANKER = ROOT/'analysis/ast-feedback-replay-model.json'
PROTOCOL = ROOT/'EXPERIMENT-contextual-ast-improver-v2.md'
DEVELOPMENT = ROOT/'analysis/ast-value-feature-development.json'
MIXED_A = tuple(range(902366,902369))
AST_A = tuple(range(902369,902372))
MIXED_T = tuple(range(902372,902378))
AST_T = tuple(range(902378,902384))
MODELS = ('ridge0','ridge1','ridge_scrambled','ridge_duplicate',
          'rbf0','rbf1','legacy100')
FIXED = ('one_each','random','entropy','disagreement')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def source_paths():
    from ast_value_feature_development import SENSOR,QUERY,MIXED,INCREMENTAL
    specs = ((SENSOR,'frozen_records.json'),(QUERY,'frozen_records.json'),
             (MIXED,'frozen_decisions.json'),
             (INCREMENTAL/'admission','frozen_records.json'),
             (INCREMENTAL/'transfer','frozen_records.json'))
    return [path/name for path,record in specs
            for name in ('sealed_bank.json',record,'predicted_probe_outputs.json','results.json')]


def source_tables():
    rows=load_rows()
    assert len(rows)==384 and len({r['task']['id'] for r in rows})==384
    first=rows[:288]; later=rows[288:]
    assert all(r['source']!='transfer' for r in first)
    assert all(r['source']=='transfer' for r in later)
    groups={'ridge0':first,'ridge1':rows,'rbf0':first,'rbf1':rows,
            'legacy100':first}
    scrambled=[dict(r) for r in rows]
    for stream in ('mixed','ast_only'):
        indices=[i for i in range(288,384) if rows[i]['stream']==stream]
        for target,source in zip(indices,indices[-1:]+indices[:-1]):
            scrambled[target]={**scrambled[target], 'correct':rows[source]['correct']}
    groups['ridge_scrambled']=scrambled
    groups['ridge_duplicate']=first+first[:96]
    return groups


def train(name,rows):
    if name.startswith('rbf'):
        x=np.stack([expanded(r) for r in rows])
        kind='rbf'; param=rbf_fit(x,*effects(rows),1.,1.)
    else:
        x=np.stack([features(r['task'],r['record'],r['matrix']) for r in rows])
        kind='linear'; param=fit(x,*effects(rows),100. if name=='legacy100' else 10.)
    return {'kind':kind,'params':[value.tolist() if isinstance(value,np.ndarray) else value
                                   for value in param], 'source_tasks':len(rows)}


def effects(rows):
    return (np.asarray([r['correct'][1]-r['correct'][0] for r in rows],float),
            np.asarray([r['correct'][2]-r['correct'][1] for r in rows],float))


def inference(model,tasks,records,predicted):
    lookup={r['id']:r for r in records}
    rows=[{'task':task,
           'record':{**lookup[task['id']],
                     'first_probe':{'top20_entropy':lookup[task['id']]['first_probe']}},
           'matrix':predicted[task['id']]} for task in tasks]
    params=[np.asarray(v,dtype=float) if isinstance(v,list) else v for v in model['params']]
    if model['kind']=='rbf':
        x=np.stack([expanded(r) for r in rows])
        return rbf_predict(params,x)
    x=np.stack([features(r['task'],r['record'],r['matrix']) for r in rows])
    return predict(params,x)


def stage_rows(stage):
    directory=DEST/stage
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    outcomes=json.loads((directory/'results.json').read_text())['tasks']
    assert all(t['id']==r['id']==o['id'] for t,r,o in zip(tasks,records,outcomes))
    rows=[]
    for task,record,outcome in zip(tasks,records,outcomes):
        rows.append({'task':task,
                     'record':{**record,'first_probe':{'top20_entropy':record['first_probe']}},
                     'matrix':predicted[task['id']],
                     'correct':[int(v) for v in outcome['correct_by_calls']],
                     'source':stage,'seed':task['seed'],'stream':task['stream']})
    return rows


def allocations(tasks,records,predicted,models,protected=None):
    result={}; lookup={r['id']:r for r in records}
    for seed in sorted({task['seed'] for task in tasks}):
        group=[task for task in tasks if task['seed']==seed]
        assert len(group)==8
        ids=[task['id'] for task in group]
        x=np.stack([features(task,{**lookup[task['id']],
                                  'first_probe':{'top20_entropy':lookup[task['id']]['first_probe']}},
                             predicted[task['id']]) for task in group])
        choices={name:dict(zip(ids,fixed(ids,x,8,name))) for name in FIXED}
        for name,model in models.items():
            p1,p2=inference(model,group,records,predicted)
            choices[name]=dict(zip(ids,allocate(p1,p2,8)))
        if protected is not None:
            for name in ('ridge1','rbf1'):
                choices['protected_'+name]=(choices[name] if protected[name]
                                             else choices['one_each'])
        assert all(sum(row.values())==8 for row in choices.values())
        result[str(seed)]=choices
    return result


def prepare_stage(stage,mixed,ast,models,protected=None):
    directory=DEST/stage
    if directory.exists(): raise RuntimeError(f'{stage} already prepared')
    start=time.perf_counter()
    tasks=task_banks(mixed,ast)
    pools,times=pools_for(tasks)
    public=[({'id':task['id'],'probe_inputs':[v for v,_ in task['hidden'][:8]]},
             pools[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted=dict(executor.map(predicted_outputs,public))
    ranker=updated_model(); records=[]
    for task in tasks:
        key=task['id']; rows=pools[key]
        scores,order=rank(task,rows,ranker)
        first=choose_probe(key,predicted[key],order,scores,
                           set(range(len(rows))),[],'top20_entropy')
        records.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                        'pool_sha256':digest(rows),'scores':scores,'order':order,
                        'first_probe':first})
    choice=allocations(tasks,records,predicted,models,protected)
    model_path=DEST/('parent_models.json' if stage=='admission' else 'child_models.json')
    manifest={'stage':stage,'protocol_sha256':sha(PROTOCOL),
              'runner_sha256':sha(ROOT/'contextual_ast_improver_v2.py'),
              'ranker_sha256':sha(RANKER),'model_sha256':sha(model_path),
              'protected_sha256':sha(DEST/'admission_gate.json') if protected is not None else None,
              'mixed_seeds':mixed,'ast_seeds':ast,'tasks':len(tasks),
              'calls_per_bank':8,'candidate_count':sum(len(v) for v in pools.values()),
              'predicted_output_cells':sum(len(v)*8 for v in pools.values()),
              'generation_seconds':sum(times.values()),
              'preparation_wall_seconds':time.perf_counter()-start}
    write_json(directory/'sealed_bank.json',tasks)
    write_json(directory/'candidate_pools.json',pools)
    write_json(directory/'predicted_probe_outputs.json',predicted)
    write_json(directory/'frozen_records.json',records)
    write_json(directory/'frozen_allocations.json',choice)
    write_json(directory/'manifest.json',manifest)
    return manifest


def prepare_parents():
    if DEST.exists(): raise RuntimeError('run already exists')
    source={'source_hashes':{str(p.relative_to(ROOT)):sha(p) for p in source_paths()},
            'development_sha256':sha(DEVELOPMENT),
            'protocol_sha256':sha(PROTOCOL)}
    tables=source_tables()
    models={name:train(name,tables[name]) for name in MODELS}
    write_json(DEST/'source_manifest.json',source)
    write_json(DEST/'parent_models.json',models)
    return prepare_stage('admission',MIXED_A,AST_A,models)


def score_stage(stage):
    directory=DEST/stage
    if (directory/'results.json').exists(): raise RuntimeError(f'{stage} already scored')
    manifest=json.loads((directory/'manifest.json').read_text())
    assert manifest['protocol_sha256']==sha(PROTOCOL)
    assert manifest['runner_sha256']==sha(ROOT/'contextual_ast_improver_v2.py')
    assert manifest['ranker_sha256']==sha(RANKER)
    assert manifest['model_sha256']==sha(DEST/('parent_models.json' if stage=='admission'
                                             else 'child_models.json'))
    if stage=='transfer': assert manifest['protected_sha256']==sha(DEST/'admission_gate.json')
    tasks=json.loads((directory/'sealed_bank.json').read_text())
    pools=json.loads((directory/'candidate_pools.json').read_text())
    predicted=json.loads((directory/'predicted_probe_outputs.json').read_text())
    records=json.loads((directory/'frozen_records.json').read_text())
    choice=json.loads((directory/'frozen_allocations.json').read_text())
    outcomes=[]
    for task,record in zip(tasks,records):
        key=task['id']; rows=pools[key]; matrix=predicted[key]
        assert key==record['id'] and record['pool_sha256']==digest(rows)
        labels=[bool(evaluate_program(row['program'],task['hidden'][8:])) for row in rows]
        order=record['order'];scores=record['scores']; used=[]
        remaining=set(range(len(rows))); correct=[bool(labels[order[0]])]
        for n in (1,2):
            j=record['first_probe'] if n==1 else choose_probe(
                key,matrix,order,scores,remaining,used,'top20_entropy')
            used.append(j)
            matched={i for i in remaining if matrix[i][j]==task['hidden'][j][1]}
            if matched: remaining=matched
            index=next((i for i in order if i in remaining),order[0])
            correct.append(bool(labels[index]))
        outcomes.append({'id':key,'seed':task['seed'],'stream':task['stream'],
                         'reachable':any(labels),'correct_by_calls':correct,
                         'query_indices':used})
    by_id={r['id']:r for r in outcomes}
    banks=[]
    for seed in sorted({task['seed'] for task in tasks}):
        group=[r for r in outcomes if r['seed']==seed]
        scores={name:sum(by_id[key]['correct_by_calls'][calls]
                         for key,calls in mapping.items())
                for name,mapping in choice[str(seed)].items()}
        banks.append({'seed':seed,'stream':group[0]['stream'],
                      'reachable':sum(r['reachable'] for r in group),
                      'no_query':sum(r['correct_by_calls'][0] for r in group),
                      'correct':scores})
    names=tuple(choice[str(banks[0]['seed'])])
    summary={'stage':stage,'tasks':len(tasks),
             'logical_calls_per_policy':8*len(banks),
             'acquisition_probe_calls':2*len(tasks) if stage=='admission' else 0,
             'reachable':sum(r['reachable'] for r in outcomes),
             'no_query':sum(b['no_query'] for b in banks),
             'correct':{name:sum(b['correct'][name] for b in banks) for name in names},
             'by_bank':banks}
    write_json(directory/'results.json',{'summary':summary,'tasks':outcomes})
    return summary


def admission_gate(summary):
    result={}
    for name in ('ridge1','rbf1'):
        differences=[b['correct'][name]-b['correct']['one_each']
                     for b in summary['by_bank']]
        result[name]={'differences':differences,'sum':sum(differences),
                      'losing_banks':sum(d<0 for d in differences),
                      'admit':sum(differences)>=2 and sum(d<0 for d in differences)<=1}
    return result


def train_children():
    if (DEST/'child_models.json').exists(): raise RuntimeError('children already exist')
    summary=json.loads((DEST/'admission/results.json').read_text())['summary']
    gate=admission_gate(summary)
    tables=source_tables(); extra=stage_rows('admission')
    children={name:train(name,tables[name]+extra) for name in MODELS}
    write_json(DEST/'admission_gate.json',gate)
    write_json(DEST/'child_models.json',children)
    write_json(DEST/'child_training.json',{'admission_result_sha256':sha(DEST/'admission/results.json'),
                                           'source_manifest_sha256':sha(DEST/'source_manifest.json'),
                                           'new_task_ids':[r['task']['id'] for r in extra]})
    return prepare_stage('transfer',MIXED_T,AST_T,children,
                         {name:gate[name]['admit'] for name in gate})


def interval(diffs):
    counts={0:1}
    for _ in diffs:
        nxt={}
        for total,count in counts.items():
            for d in diffs: nxt[total+d]=nxt.get(total+d,0)+count
        counts=nxt
    total=len(diffs)**len(diffs); cumulative=0; lower=upper=None
    for value,count in sorted(counts.items()):
        cumulative+=count
        if lower is None and cumulative/total>=.025:lower=value
        if upper is None and cumulative/total>=.975:upper=value
    return [lower,upper]


def summarize():
    admission=json.loads((DEST/'admission/results.json').read_text())['summary']
    transfer=json.loads((DEST/'transfer/results.json').read_text())['summary']
    gate=json.loads((DEST/'admission_gate.json').read_text())
    strongest=max(FIXED,key=lambda name:transfer['correct'][name])
    comparisons={}
    for family in ('ridge','rbf'):
        name0=family+'0'; name1=family+'1'
        diffs=[b['correct'][name1]-b['correct'][name0] for b in transfer['by_bank']]
        ci=interval(diffs)
        control_ok=(transfer['correct']['protected_'+name1]>
                    transfer['correct'][strongest])
        if family=='ridge':
            control_ok=control_ok and all(transfer['correct'][name1]>
                                          transfer['correct'][control]
                                          for control in ('ridge_scrambled','ridge_duplicate'))
        comparisons[family]={'child_minus_initial_by_bank':diffs,
                             'positive_banks':sum(d>0 for d in diffs),
                             'bank_bootstrap_95_sum':ci,
                             'protected_admitted':gate[name1]['admit'],
                             'passed':sum(d>0 for d in diffs)>=8 and ci[0]>0 and control_ok}
    return {'scope':'synthetic AST fixed-catalog improver','admission':admission,
            'transfer':transfer,'admission_gate':gate,
            'strongest_fixed':strongest,'comparisons':comparisons,
            'source_tasks':{'p0':288,'p1':384},
            'new_shared_admission_tasks':48,'new_shared_acquisition_outputs':96,
            'transfer_calls_per_policy':96}


def score_transfer():
    score_stage('transfer')
    summary=summarize()
    write_json(DEST/'summary.json',summary)
    return {'transfer':summary['transfer']['correct'],
            'admission_gate':summary['admission_gate'],
            'comparisons':summary['comparisons']}


if __name__=='__main__':
    actions={'prepare_parents':prepare_parents,'score_admission':lambda:score_stage('admission'),
             'train_children':train_children,'score_transfer':score_transfer}
    print(json.dumps(actions[sys.argv[1]](),indent=2))
