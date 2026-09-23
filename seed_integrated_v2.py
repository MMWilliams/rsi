"""Equal-label feedback budgets and identical admission/deployment policies."""
from __future__ import annotations
import argparse,json,random,shutil,time,traceback,hashlib
from pathlib import Path
import numpy as np
from rsi.common import ROOT,Journal,digest,write_json,verify_journal
from rsi.retention_run import file_hash,seal_artifacts
from rsi.semantic_invention import evaluate_program
from seed_growth import METHODS,train,predict,pick,base_index
from seed_source_search import read,build_records,acquire,export_model,TACTICS
from seed_meta import extract_effects,state_features,choose_tactic
from seed_v2_banks import generate
from seed_confirmation import final_scores
from stitch_ten import source_candidates

SOURCE='runs/seed-source-search-20260917'
MODES=tuple('fixed_'+t for t in TACTICS)+('meta4','meta4_scrambled','meta4_online')
POLICIES=('argmax','margin')
GATES=('strict','proper_tie')
PRIMARY='fixed_novelty__argmax__proper_tie'


def bundle_index(record,scores,policy):
    preferred=pick(record,scores); base=base_index(record['rows'])
    if policy=='argmax': return preferred
    if policy!='margin': raise ValueError(policy)
    return preferred if base is None or (preferred is not None and scores[preferred]>scores[base]+.05) else base


def predictions(model,records,policy):
    result={}
    for record in records:
        scores=predict(model,record)
        result[record['id']]={'indices':{name:pick(record,values) for name,values in scores.items()},
            'base':base_index(record['rows']),'deployed':bundle_index(record,scores['ensemble'],policy),
            'probabilities':{name:value.tolist() for name,value in scores.items() if name!='guarded'}}
    return result


def admission(model,records,oracle,policy):
    chosen=predictions(model,records,policy); rows=[]; errors=[]
    for record in records:
        y=oracle(record['id']); row=chosen[record['id']]; ix=row['deployed']
        correct=bool(y[ix]) if ix is not None else False
        rows.append({'id':record['id'],'index':ix,'correct':correct,'block':record['features']['block']})
        if y: errors.append(sum((p-label)**2 for p,label in zip(row['probabilities']['ensemble'],y))/len(y))
    return {'correct':sum(r['correct'] for r in rows),'brier':sum(errors)/len(errors) if errors else 1.,'rows':rows}


def accept(old,new,gate):
    if new['correct']<old['correct']: return False
    blocks={r['block'] for r in old['rows']}
    if any(sum(r['correct'] for r in new['rows'] if r['block']==block)<
           sum(r['correct'] for r in old['rows'] if r['block']==block) for block in blocks): return False
    if new['correct']>old['correct']: return True
    return gate=='proper_tie' and new['brier']<=old['brier']-.001


def partial_record(record,indices):
    view={'id':record['id']+':'+digest(indices)[:12],'base_id':record['id'],'candidate_indices':indices,
          'public':record['public'],'rows':[record['rows'][i] for i in indices]}
    f=record['features']
    view['features']={key:(value[indices] if key in ('lexical','structural','behavior','boundary') else value) for key,value in f.items()}
    return view


def remaining_views(reservoir,purchased):
    return [partial_record(record,[i for i in range(len(record['rows'])) if i not in purchased.get(record['id'],{})])
            for record in reservoir if len(purchased.get(record['id'],{}))<len(record['rows'])]


def train_records(bootstrap,reservoir,purchased):
    result=list(bootstrap)
    for record in reservoir:
        known=purchased.get(record['id'],{})
        if known:
            ids=sorted(known); view=partial_record(record,ids); view['labels']=np.asarray([known[i] for i in ids],dtype=float)
            result.append(view)
    return result


def purchase(model,remaining,tactic,oracle,purchased,allowance=48):
    if sum(len(r['rows']) for r in remaining)<allowance: raise RuntimeError('insufficient remaining candidates for matched budget')
    ranked=acquire(model,remaining,'ensemble',tactic,count=len(remaining))
    if tactic=='uniform':
        mapping={r['id']:r for r in remaining}
        for row in ranked:
            row['score']=int.from_bytes(hashlib.sha256(('uniform531:'+mapping[row['id']]['base_id']).encode()).digest()[:8],'little')/2**64
        ranked.sort(key=lambda row:(-row['score'],mapping[row['id']]['base_id']))
    byid={r['id']:r for r in remaining}; queried=[]; spent=0
    for choice in ranked:
        if spent==allowance: break
        view=byid[choice['id']]; original=view['base_id']; count=min(allowance-spent,len(view['candidate_indices']))
        ids=view['candidate_indices'][:count]
        labels=oracle(original,ids)
        purchased.setdefault(original,{}).update(zip(ids,labels))
        queried.append({'id':original,'candidate_indices':ids,'labels':labels,'acquisition_score':choice['score']})
        spent+=count
    assert spent==allowance
    return queried


def loops(records,oracle,effects,telemetry=None):
    arms={}; states={}
    for mode in MODES:
        for policy in POLICIES:
            for gate in GATES:
                started=time.perf_counter()
                name='__'.join((mode,policy,gate)); known=[dict(e) for e in effects]
                if mode=='meta4_scrambled':
                    u=[e['utility'] for e in known]; random.Random(491).shuffle(u)
                    known=[dict(e,utility=value) for e,value in zip(known,u)]
                bootstrap=[]; bootstrap_cost=0
                for record in records['bootstrap']:
                    ids=list(range(len(record['rows']))); y=oracle(record['id'],ids)
                    bootstrap_cost+=len(ids); bootstrap.append({**record,'labels':np.asarray(y,dtype=float)})
                purchased={}; active=train(bootstrap)
                measured=admission(active,records['admission'],lambda key:oracle(key,None),policy)
                checkpoints=[]; selected_round=0
                for round in range(5):
                    chosen_tactic=None; queries=[]; admitted=None; child_measurement=None; effect_scores={}
                    if round:
                        remaining=remaining_views(records['reservoir'],purchased)
                        context=state_features(active,remaining,'ensemble',round-1,measured['correct'],len(records['admission']))
                        chosen_tactic=mode[6:] if mode.startswith('fixed_') else choose_tactic(known,'ensemble',context)[0]
                        if not mode.startswith('fixed_'): effect_scores=choose_tactic(known,'ensemble',context)[1]
                        queries=purchase(active,remaining,chosen_tactic,oracle,purchased)
                        child=train(train_records(bootstrap,records['reservoir'],purchased))
                        child_measurement=admission(child,records['admission'],lambda key:oracle(key,None),policy)
                        admitted=accept(measured,child_measurement,gate)
                        if mode=='meta4_online':
                            n=len(records['admission']); harmed=sum(a['correct'] and not b['correct'] for a,b in zip(measured['rows'],child_measurement['rows']))
                            known.append({'episode':'v2_online','round':round,'driver':'ensemble','tactic':chosen_tactic,'state':context,
                                'gain':(child_measurement['correct']-measured['correct'])/n,'harm':harmed/n,
                                'utility':(child_measurement['correct']-measured['correct']-.25*harmed)/n})
                        if admitted: active=child; measured=child_measurement; selected_round=round
                    final={split:predictions(active,panel,policy) for split,panel in records.items() if split.startswith('final_')}
                    checkpoints.append({'round':round,'tactic':chosen_tactic,'query_log':queries,'effect_scores':effect_scores,
                        'accepted':admitted,'selected_round':selected_round,'admission':measured,'candidate_admission':child_measurement,
                        'final_predictions':final,'improvement_labels':sum(map(len,purchased.values())),
                        'model_sha256':digest(export_model(active)),'controller_sha256':digest(known)})
                arms[name]={'mode':mode,'policy':policy,'gate':gate,'candidate_queries':bootstrap_cost+192,
                    'bootstrap_queries':bootstrap_cost,'improvement_queries':192,'checkpoints':checkpoints}
                states[name]={'model':export_model(active),'effects':known,'policy':policy,'gate':gate,'driver':'ensemble'}
                if telemetry is not None:
                    telemetry[name]={'wall_seconds':time.perf_counter()-started,'model_fits':5,
                        'improvement_oracle_labels':192,'bootstrap_oracle_labels':bootstrap_cost,
                        'common_admission_candidate_labels':sum(len(r['rows']) for r in records['admission']),
                        'admission_assessments':5}
                print('v2 frozen: '+name,flush=True)
    return {'driver':'ensemble','primary':PRIMARY,'arms':arms,'states':states}


def run(output,prepared):
    output.mkdir(parents=True,exist_ok=False); journal=Journal(output/'events.jsonl')
    try:
        assert read(ROOT/SOURCE/'audit.json')['status']=='passed'
        paths=sorted((ROOT/'rsi').glob('*.py'))+[ROOT/n for n in ('seed_growth.py','seed_casebanks.py','seed_source_search.py','seed_meta.py',
            'seed_v2_banks.py','seed_integrated_v2.py','seed_confirmation.py','stitch_ten.py','run_policy_transfer.py','run_ast_v66.py',
            'EXPERIMENT-seed-integration-v2.md')]+[ROOT/'vendor/trapdoor-loom'/n for n in ('dsl.py','parse.py','trapdoor.py')]
        hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
        for path in paths:
            dest=output/'source'/path.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,dest)
        write_json(output/'source_manifest.json',hashes)
        write_json(output/'source_provenance.json',{name:file_hash(ROOT/SOURCE/name) for name in
            ('results.json','audit.json','protected_banks.json','candidate_pools.json')})
        journal.append('preregistered',{'hashes':hashes,'primary':PRIMARY,'candidate_label_budget_per_round':48})
        for name,row in read(prepared/'artifact_manifest.json').items(): assert file_hash(prepared/name)==row['sha256']
        banks=generate(); assert digest(banks)==digest(read(prepared/'protected_banks.json'))
        pools=read(prepared/'candidate_pools.json')
        for rows in pools.values(): assert all('oracle_correct' not in row for row in rows)
        write_json(output/'protected_banks.json',banks); write_json(output/'candidate_pools.json',pools)
        write_json(output/'generation_times.json',read(prepared/'generation_times.json'))
        source=read(ROOT/SOURCE/'results.json'); source_records=build_records(read(ROOT/SOURCE/'protected_banks.json'),read(ROOT/SOURCE/'candidate_pools.json'))
        effects=extract_effects(source,source_records); write_json(output/'inherited_effects.json',effects)
        records=build_records(banks,pools); tasks={t['id']:t for ts in banks.values() for t in ts}
        final_ids={t['id'] for split,ts in banks.items() if split.startswith('final_') for t in ts}; opened={}
        def oracle(key,indices):
            if key in final_ids: raise RuntimeError('final labels requested before freeze')
            if indices is None: indices=list(range(len(pools[key])))
            known=opened.setdefault(key,{})
            for i in indices:
                if i not in known: known[i]=int(evaluate_program(pools[key][i]['program'],tasks[key]['visible']+tasks[key]['hidden']))
            return [known[i] for i in indices]
        telemetry={}
        frozen=loops(records,oracle,effects,telemetry); write_json(output/'frozen_loops.json',frozen)
        write_json(output/'loop_costs.json',telemetry)
        journal.append('all_loops_frozen',{'sha256':digest(frozen)})
        labels={key:[int(evaluate_program(row['program'],tasks[key]['visible']+tasks[key]['hidden'])) for row in pools[key]] for key in final_ids}
        write_json(output/'final_labels.json',labels); write_json(output/'opened_feedback_labels.json',opened)
        results=final_scores(frozen,records,labels); write_json(output/'results.json',results)
        assert all(file_hash(ROOT/name)==sha for name,sha in hashes.items())
        journal.append('completed',{'sha256':digest(results)}); seal_artifacts(output)
        return {'status':'completed','primary':PRIMARY,'primary_final':results[PRIMARY]['rounds'][-1],
            'scope':'one equal-candidate-label episode; independent replication remains required'}
    except BaseException as exc:
        write_json(output/'FAILED.json',{'message':str(exc),'traceback':traceback.format_exc()}); raise


def audit(output):
    assert not (output/'FAILED.json').exists()
    manifest=read(output/'artifact_manifest.json')
    actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p.name not in ('artifact_manifest.json','audit.json')}
    assert actual==set(manifest)
    for name,row in manifest.items(): assert file_hash(output/name)==row['sha256'],name
    for name,sha in read(output/'source_manifest.json').items(): assert file_hash(ROOT/name)==sha and file_hash(output/'source'/name)==sha,name
    for name,sha in read(output/'source_provenance.json').items(): assert file_hash(ROOT/SOURCE/name)==sha,name
    banks=generate(); assert digest(banks)==digest(read(output/'protected_banks.json'))
    pools=read(output/'candidate_pools.json'); tasks={t['id']:t for ts in banks.values() for t in ts}; labels={}; calls=0
    for split,ts in banks.items():
        for task in ts:
            unique={}
            for arm in ('v67','v73'):
                for row in source_candidates({'id':task['id'],'visible':task['visible']},arm,{},16): unique.setdefault(row['program'],row)
                calls+=1
            assert digest(list(unique.values()))==digest(pools[task['id']])
            labels[task['id']]=[int(evaluate_program(r['program'],task['visible']+task['hidden'])) for r in pools[task['id']]]
        print('v2 audit bank replayed: '+split,flush=True)
    for key,opened in read(output/'opened_feedback_labels.json').items():
        for index,label in opened.items(): assert labels[key][int(index)]==label
    source=read(ROOT/SOURCE/'results.json'); source_records=build_records(read(ROOT/SOURCE/'protected_banks.json'),read(ROOT/SOURCE/'candidate_pools.json'))
    effects=extract_effects(source,source_records); assert digest(effects)==digest(read(output/'inherited_effects.json'))
    final_ids={t['id'] for split,ts in banks.items() if split.startswith('final_') for t in ts}
    def oracle(key,indices):
        assert key not in final_ids
        return labels[key] if indices is None else [labels[key][i] for i in indices]
    records=build_records(banks,pools); frozen=loops(records,oracle,effects)
    assert digest(frozen)==digest(read(output/'frozen_loops.json'))
    for arm in frozen['arms'].values():
        assert [c['improvement_labels'] for c in arm['checkpoints']]==[0,48,96,144,192]
        for checkpoint in arm['checkpoints']:
            for row in checkpoint['admission']['rows']:
                # Admission indices already came from the same bundle_index path as final choices.
                assert row['index'] is None or 0<=row['index']<len(pools[row['id']])
    result=final_scores(frozen,records,labels); assert digest(result)==digest(read(output/'results.json'))
    events=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
    assert verify_journal(output/'events.jsonl')==3
    assert [e['kind'] for e in events]==['preregistered','all_loops_frozen','completed']
    assert events[1]['payload']['sha256']==digest(frozen) and events[2]['payload']['sha256']==digest(result)
    report={'status':'passed','candidate_calls_replayed':calls,'arms':len(frozen['arms']),
        'checkpoints_per_arm':5,'equal_improvement_labels_per_arm':192,'same_admission_deployment_rule':True,
        'scope':'one episode, shared host interpreter; no independent semantic oracle'}
    write_json(output/'audit.json',report); return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); parser.add_argument('--prepared'); parser.add_argument('--audit',action='store_true'); args=parser.parse_args()
    result=audit(ROOT/args.output) if args.audit else run(ROOT/args.output,ROOT/args.prepared)
    print(json.dumps(result,indent=2))
