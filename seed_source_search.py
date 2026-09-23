"""Factorial source discovery for feedback acquisition and evaluator integration."""
from __future__ import annotations
import argparse,json,shutil,time,traceback,hashlib
from pathlib import Path
import numpy as np
from rsi.common import ROOT,Journal,digest,write_json,verify_journal
from rsi.retention_run import file_hash,seal_artifacts
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import METHODS,representation,train,predict,pick,base_index
from stitch_ten import source_candidates

TACTICS=('uniform','uncertainty','disagreement','novelty','combined')
DRIVERS=('structural','behavior','ensemble')
GATES=('replace','strict','retention')


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def build_records(banks,pools):
    return {split:[{'id':task['id'],'public':{'id':task['id'],'visible':task['visible']},
        'rows':pools[task['id']], 'features':representation({'id':task['id'],'visible':task['visible']},pools[task['id']])}
        for task in tasks] for split,tasks in banks.items()}


def query_values(model,record,driver):
    scores=predict(model,record)
    if not len(record['rows']): return {'uncertainty':0.,'disagreement':0.,'novelty':0.}
    p=scores[driver]
    disagreement=float(np.mean(np.std(np.vstack([scores[n] for n in ('lexical','structural','behavior')]),axis=0)))
    distances=[]
    for vector in record['features']['behavior']:
        distances.append(float(np.min(np.mean(np.abs(model['memory']-vector),axis=1))))
    return {'uncertainty':float(np.mean(4*p*(1-p))),'disagreement':disagreement,
            'novelty':float(np.mean(distances))}


def acquire(model,remaining,driver,tactic,count=4):
    values={record['id']:query_values(model,record,driver) for record in remaining}
    minima={key:min(row[key] for row in values.values()) for key in ('disagreement','novelty')}
    maxima={key:max(row[key] for row in values.values()) for key in minima}
    ranked=[]
    for record in remaining:
        if tactic=='uniform':
            value=int.from_bytes(hashlib.sha256(('uniform531:'+record['id']).encode()).digest()[:8],'little')/2**64
        elif tactic=='combined':
            value=sum((values[record['id']][key]-minima[key])/max(1e-12,maxima[key]-minima[key]) for key in minima)/2
        else: value=values[record['id']][tactic]
        ranked.append({'id':record['id'],'score':value,'diagnostics':values[record['id']]})
    ranked.sort(key=lambda row:(-row['score'],row['id']))
    return ranked[:count]


def judge(model,records,oracle):
    result={name:{'correct':0,'rows':[]} for name in ('base',*METHODS)}
    for record in records:
        predictions=predict(model,record); labels=oracle(record['id'])
        for name in result:
            ix=base_index(record['rows']) if name=='base' else pick(record,predictions[name])
            correct=bool(labels[ix]) if ix is not None else False
            result[name]['correct']+=int(correct)
            result[name]['rows'].append({'id':record['id'],'index':ix,'correct':correct,
                'block':record['features']['block'],
                'probabilities':predictions[name].tolist() if name not in ('base','guarded') else None})
    return result


def gate_allowed(old,new,gate):
    if gate=='replace': return True
    if new['correct']<=old['correct']: return False
    if gate=='strict': return True
    groups=sorted({row['block'] for row in old['rows']})
    return all(sum(r['correct'] for r in new['rows'] if r['block']==b)>=
               sum(r['correct'] for r in old['rows'] if r['block']==b) for b in groups)


def export_model(model):
    return {key:value.tolist() for key,value in model.items() if not key.startswith('_')}


def study(records,oracle):
    episodes={}; selected_models={}; query_log=[]
    for driver in DRIVERS:
        for tactic in TACTICS:
            name=driver+'__'+tactic
            def labelled(record,round):
                y=oracle(record['id'])
                query_log.append({'arm':name,'round':round,'id':record['id'],'candidate_queries':len(y)})
                return {**record,'labels':np.array(y,dtype=float)}
            feedback=[labelled(record,0) for record in records['bootstrap']]
            remaining=list(records['reservoir']); checkpoints=[]; retained={gate:0 for gate in GATES}; models=[]
            for round in range(5):
                selected=[]
                if round:
                    selected=acquire(models[-1],remaining,driver,tactic)
                    chosen={row['id'] for row in selected}
                    feedback += [labelled(record,round) for record in remaining if record['id'] in chosen]
                    remaining=[record for record in remaining if record['id'] not in chosen]
                model=train(feedback); models.append(model)
                admission=judge(model,records['admission'],oracle)
                decisions={}
                if round:
                    for gate in GATES:
                        old=checkpoints[retained[gate]]['admission'][driver]
                        accepted=gate_allowed(old,admission[driver],gate)
                        decisions[gate]={'accepted':accepted,'parent_checkpoint':retained[gate]}
                        if accepted: retained[gate]=round
                checkpoints.append({'round':round,'feedback_tasks':len(feedback),'query_selection':selected,
                    'admission':admission,'gates':decisions,'retained':dict(retained),
                    'model':export_model(model),'feedback_ids':[r['id'] for r in feedback]})
            episodes[name]={'driver':driver,'tactic':tactic,'checkpoints':checkpoints,
                            'candidate_queries':sum(row['candidate_queries'] for row in query_log if row['arm']==name)}
            selected_models[name]={gate:export_model(models[index]) for gate,index in retained.items()}
            print('source arm closed: '+name,flush=True)
    ranked=[]
    for name,episode in episodes.items():
        for gate,index in episode['checkpoints'][-1]['retained'].items():
            selected=episode['checkpoints'][index]['admission'][episode['driver']]
            initial=episode['checkpoints'][0]['admission'][episode['driver']]
            harms=sum(old['correct'] and not new['correct'] for old,new in zip(initial['rows'],selected['rows']))
            ranked.append({'name':name,'gate':gate,'checkpoint':index,'admission_correct':selected['correct'],
                'initial_correct':initial['correct'],'regressions':harms,'candidate_queries':episode['candidate_queries']})
    ranked.sort(key=lambda row:(-row['admission_correct'],row['regressions'],row['candidate_queries'],
                                row['name'],('retention','strict','replace').index(row['gate'])))
    return {'scope':'source discovery/admission only','episodes':episodes,'ranking':ranked,'selected':ranked[0],
            'selected_models':selected_models,'query_log':query_log}


def generate():
    return {'bootstrap':random_bank(205001,6),'reservoir':random_bank(205002,48),'admission':random_bank(205003,18)}


def run(output):
    output.mkdir(parents=True,exist_ok=False); journal=Journal(output/'events.jsonl')
    try:
        paths=sorted((ROOT/'rsi').glob('*.py'))+[ROOT/n for n in ('seed_growth.py','seed_casebanks.py','seed_source_search.py',
            'stitch_ten.py','run_policy_transfer.py','run_ast_v66.py','EXPERIMENT-seed-source-search.md')]
        paths += [ROOT/'vendor/trapdoor-loom'/n for n in ('dsl.py','parse.py','trapdoor.py')]
        hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
        for path in paths:
            dest=output/'source'/path.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,dest)
        write_json(output/'source_manifest.json',hashes)
        journal.append('preregistered',{'hashes':hashes,'drivers':DRIVERS,'tactics':TACTICS,'gates':GATES})
        banks=generate(); write_json(output/'protected_banks.json',banks)
        public_hashes=[digest(t['visible']) for tasks in banks.values() for t in tasks]
        if len(set(public_hashes))!=len(public_hashes): raise RuntimeError('duplicate visible example set')
        pools={}; times={'v67':0.,'v73':0.}
        for split,tasks in banks.items():
            for task in tasks:
                public={'id':task['id'],'visible':task['visible']}; unique={}
                for arm in ('v67','v73'):
                    start=time.perf_counter(); rows=source_candidates(public,arm,{},16); times[arm]+=time.perf_counter()-start
                    for row in rows: unique.setdefault(row['program'],row)
                pools[task['id']]=list(unique.values())
            print('public source bank generated: '+split,flush=True)
        write_json(output/'candidate_pools.json',pools); write_json(output/'generation_times.json',times)
        tasks={t['id']:t for rows in banks.values() for t in rows}; labels={}
        def oracle(taskid):
            if taskid not in labels:
                task=tasks[taskid]
                labels[taskid]=[int(evaluate_program(r['program'],task['visible']+task['hidden'])) for r in pools[taskid]]
            return labels[taskid]
        start=time.perf_counter(); result=study(build_records(banks,pools),oracle)
        write_json(output/'results.json',result); write_json(output/'opened_source_labels.json',labels)
        write_json(output/'fit_time.json',{'seconds':time.perf_counter()-start})
        if any(file_hash(ROOT/name)!=sha for name,sha in hashes.items()): raise RuntimeError('source changed')
        journal.append('completed',{'sha256':digest(result)}); seal_artifacts(output)
        return {'status':'completed','selected':result['selected'],'ranked_top10':result['ranking'][:10]}
    except BaseException as exc:
        write_json(output/'FAILED.json',{'message':str(exc),'traceback':traceback.format_exc()}); raise


def audit(output):
    assert not (output/'FAILED.json').exists()
    manifest=read(output/'artifact_manifest.json')
    actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p.name not in ('artifact_manifest.json','audit.json')}
    assert actual==set(manifest)
    for name,row in manifest.items(): assert file_hash(output/name)==row['sha256'],name
    for name,sha in read(output/'source_manifest.json').items():
        assert file_hash(ROOT/name)==sha and file_hash(output/'source'/name)==sha,name
    banks=generate(); assert digest(banks)==digest(read(output/'protected_banks.json'))
    pools=read(output/'candidate_pools.json'); calls=0
    for split,tasks in banks.items():
        for task in tasks:
            unique={}
            for arm in ('v67','v73'):
                for row in source_candidates({'id':task['id'],'visible':task['visible']},arm,{},16): unique.setdefault(row['program'],row)
                calls+=1
            assert digest(list(unique.values()))==digest(pools[task['id']])
        print('audit candidate bank replayed: '+split,flush=True)
    tasks={t['id']:t for rows in banks.values() for t in rows}
    labels={key:[int(evaluate_program(r['program'],tasks[key]['visible']+tasks[key]['hidden'])) for r in rows] for key,rows in pools.items()}
    for key,value in read(output/'opened_source_labels.json').items(): assert labels[key]==value
    replay=study(build_records(banks,pools),lambda key:labels[key])
    assert digest(replay)==digest(read(output/'results.json'))
    assert verify_journal(output/'events.jsonl')==2
    report={'status':'passed','candidate_calls_replayed':calls,'episodes_replayed':15,'checkpoints_replayed':75,
            'scope':'source discovery only; shared host interpreter; no independent oracle proof'}
    write_json(output/'audit.json',report); return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); parser.add_argument('--audit',action='store_true'); args=parser.parse_args()
    print(json.dumps((audit if args.audit else run)(ROOT/args.output),indent=2))
