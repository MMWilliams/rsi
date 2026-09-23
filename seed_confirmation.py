"""Fresh same-base transfer of learned feedback-controller knowledge."""
from __future__ import annotations
import argparse,json,random,shutil,time,traceback
from pathlib import Path
import numpy as np
from rsi.common import ROOT,Journal,digest,write_json,verify_journal
from rsi.retention_run import file_hash,seal_artifacts
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank,shifted_ast_bank
from seed_growth import METHODS,train,predict,pick,base_index
from seed_source_search import TACTICS,read,build_records,acquire,judge,gate_allowed,export_model
from seed_meta import extract_effects,state_features,choose_tactic
from stitch_ten import source_candidates

SOURCE='runs/seed-source-search-20260917'
MODES=tuple('fixed_'+t for t in TACTICS)+('meta0','meta2','meta4','meta4_scrambled','meta4_online')


def generate():
    return {'bootstrap':random_bank(206001,6),'reservoir':random_bank(206002,48),'admission':random_bank(206003,18),
        'final_mixed':random_bank(206004,24),'final_ast':random_bank(206005,12,('ast_transition',)),
        'final_changed':shifted_ast_bank(206006,12)}


def prepare_candidates(output):
    """Generate public pools independently while source verification is running."""
    output.mkdir(parents=True,exist_ok=False)
    banks=generate(); pools={}; times={'v67':0.,'v73':0.}
    write_json(output/'protected_banks.json',banks)
    for split,tasks in banks.items():
        for task in tasks:
            unique={}
            for arm in ('v67','v73'):
                start=time.perf_counter(); rows=source_candidates({'id':task['id'],'visible':task['visible']},arm,{},16); times[arm]+=time.perf_counter()-start
                for row in rows: unique.setdefault(row['program'],row)
            pools[task['id']]=list(unique.values())
        print('public confirmation preparation: '+split,flush=True)
    write_json(output/'candidate_pools.json',pools); write_json(output/'generation_times.json',times)
    seal_artifacts(output)
    return {'status':'prepared','tasks':sum(map(len,banks.values())),'labels_opened':0}


def freeze_predictions(model,records,driver):
    result={}
    for record in records:
        scores=predict(model,record); base=base_index(record['rows'])
        indices={name:pick(record,values) for name,values in scores.items()}
        candidate=indices[driver]
        deployed=candidate if base is None or (candidate is not None and scores[driver][candidate]>scores[driver][base]+.05) else base
        result[record['id']]={'indices':indices,'base':base,'deployed':deployed,
            'probabilities':{name:values.tolist() for name,values in scores.items() if name!='guarded'}}
    return result


def run_loops(records,oracle,source,effects):
    selected=source['selected']; driver=source['episodes'][selected['name']]['driver']; gate=selected['gate']
    output={}; calls=[]; final_states={}
    for mode in MODES:
        known=[] if mode=='meta0' else [dict(e) for e in effects if e['round']<=(2 if mode=='meta2' else 4)]
        if mode=='meta4_scrambled':
            utilities=[e['utility'] for e in known]; random.Random(491).shuffle(utilities)
            known=[dict(e,utility=u) for e,u in zip(known,utilities)]
        def query(record,round):
            labels=oracle(record['id']); calls.append({'mode':mode,'round':round,'id':record['id'],'candidate_queries':len(labels)})
            return {**record,'labels':np.asarray(labels,dtype=float)}
        feedback=[query(record,0) for record in records['bootstrap']]
        remaining=list(records['reservoir']); active=train(feedback); admission=judge(active,records['admission'],oracle)
        checkpoints=[]; selected_round=0
        for round in range(5):
            action=None; scores={}; queries=[]; accepted=None; child_admission=None
            if round:
                state=state_features(active,remaining,driver,round-1,admission[driver]['correct'],len(records['admission']))
                action=mode[6:] if mode.startswith('fixed_') else choose_tactic(known,driver,state)[0]
                if not mode.startswith('fixed_'): scores=choose_tactic(known,driver,state)[1]
                queries=acquire(active,remaining,driver,action)
                ids={r['id'] for r in queries}
                feedback += [query(record,round) for record in remaining if record['id'] in ids]
                remaining=[r for r in remaining if r['id'] not in ids]
                child=train(feedback); child_admission=judge(child,records['admission'],oracle)
                accepted=gate_allowed(admission[driver],child_admission[driver],gate)
                if mode=='meta4_online':
                    old=admission[driver]; new=child_admission[driver]; n=len(records['admission'])
                    harmed=sum(a['correct'] and not b['correct'] for a,b in zip(old['rows'],new['rows']))
                    known.append({'episode':'confirmation_online','round':round,'driver':driver,'tactic':action,
                        'state':state,'gain':(new['correct']-old['correct'])/n,'harm':harmed/n,
                        'utility':(new['correct']-old['correct']-.25*harmed)/n})
                if accepted: active=child; admission=child_admission; selected_round=round
            predictions={split:freeze_predictions(active,panel,driver) for split,panel in records.items() if split.startswith('final_')}
            checkpoints.append({'round':round,'action':action,'effect_predictions':scores,'queries':queries,
                'accepted':accepted,'selected_round':selected_round,'feedback_ids':[r['id'] for r in feedback],
                'admission':admission,'candidate_admission':child_admission,'final_predictions':predictions,
                'model_sha256':digest(export_model(active)),'controller_sha256':digest(known)})
        output[mode]={'checkpoints':checkpoints,'candidate_queries':sum(r['candidate_queries'] for r in calls if r['mode']==mode)}
        final_states[mode]={'model':export_model(active),'effects':known,'driver':driver,'gate':gate,
            'provenance':'frozen before final oracle opened; confirmation outcome does not select this state'}
        print('confirmation loop frozen: '+mode,flush=True)
    return {'driver':driver,'gate':gate,'source_selected':selected,'arms':output,'feedback_query_log':calls,'states':final_states}


def final_scores(frozen,records,labels):
    output={}
    for mode,arm in frozen['arms'].items():
        rows=[]
        for checkpoint in arm['checkpoints']:
            panels={}
            for split,predictions in checkpoint['final_predictions'].items():
                counts={name:0 for name in ('base','deployed',*METHODS)}; brier=[]; reachable=0; task_rows=[]
                for record in records[split]:
                    y=labels[record['id']]; pred=predictions[record['id']]
                    def correct(ix): return bool(y[ix]) if ix is not None else False
                    row={'id':record['id'],'base':correct(pred['base']),'deployed':correct(pred['deployed']),
                         **{name:correct(ix) for name,ix in pred['indices'].items()}}
                    for name in counts: counts[name]+=int(row[name])
                    reachable+=int(any(y))
                    if y:
                        p=pred['probabilities'][frozen['driver']]
                        brier.append(sum((a-b)**2 for a,b in zip(p,y))/len(y))
                    task_rows.append(row)
                panels[split]={'n':len(records[split]),'counts':counts,'reachable':reachable,
                    'driver_brier':sum(brier)/len(brier) if brier else None,'tasks':task_rows}
            rows.append({'round':checkpoint['round'],'accepted':checkpoint['accepted'],'panels':panels})
        output[mode]={'candidate_queries':arm['candidate_queries'],'rounds':rows}
    return output


def run(output,prepared=None):
    output.mkdir(parents=True,exist_ok=False); journal=Journal(output/'events.jsonl')
    try:
        assert read(ROOT/SOURCE/'audit.json')['status']=='passed'
        source=read(ROOT/SOURCE/'results.json')
        source_records=build_records(read(ROOT/SOURCE/'protected_banks.json'),read(ROOT/SOURCE/'candidate_pools.json'))
        effects=extract_effects(source,source_records)
        paths=sorted((ROOT/'rsi').glob('*.py'))+[ROOT/n for n in ('seed_growth.py','seed_casebanks.py','seed_source_search.py',
            'seed_meta.py','seed_confirmation.py','stitch_ten.py','run_policy_transfer.py','run_ast_v66.py','EXPERIMENT-seed-confirmation.md',
            'SEED-CONFIRMATION-METRICS-ADDENDUM.md')]
        paths += [ROOT/'vendor/trapdoor-loom'/n for n in ('dsl.py','parse.py','trapdoor.py')]
        hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}
        for path in paths:
            dest=output/'source'/path.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,dest)
        write_json(output/'source_manifest.json',hashes); write_json(output/'inherited_effects.json',effects)
        provenance={name:file_hash(ROOT/SOURCE/name) for name in ('results.json','audit.json','protected_banks.json','candidate_pools.json')}
        write_json(output/'source_provenance.json',provenance)
        journal.append('preregistered',{'source':SOURCE,'source_provenance':provenance,'selected':source['selected'],'hashes':hashes})
        banks=generate(); write_json(output/'protected_banks.json',banks)
        public_hashes=[digest(t['visible']) for tasks in banks.values() for t in tasks]
        assert len(set(public_hashes))==len(public_hashes)
        old_public={digest(t['visible']) for tasks in read(ROOT/SOURCE/'protected_banks.json').values() for t in tasks}
        assert not set(public_hashes)&old_public
        pools={}; times={'v67':0.,'v73':0.}
        if prepared is not None:
            for name,row in read(prepared/'artifact_manifest.json').items(): assert file_hash(prepared/name)==row['sha256']
            assert digest(banks)==digest(read(prepared/'protected_banks.json'))
            pools=read(prepared/'candidate_pools.json'); times=read(prepared/'generation_times.json')
            assert all('oracle_correct' not in row for rows in pools.values() for row in rows)
        else:
            for split,tasks in banks.items():
                for task in tasks:
                    unique={}
                    for arm in ('v67','v73'):
                        start=time.perf_counter(); rows=source_candidates({'id':task['id'],'visible':task['visible']},arm,{},16); times[arm]+=time.perf_counter()-start
                        for row in rows: unique.setdefault(row['program'],row)
                    pools[task['id']]=list(unique.values())
                print('confirmation candidate bank closed: '+split,flush=True)
        write_json(output/'candidate_pools.json',pools); write_json(output/'generation_times.json',times)
        records=build_records(banks,pools); tasks={t['id']:t for ts in banks.values() for t in ts}
        allowed={t['id'] for split,ts in banks.items() if not split.startswith('final_') for t in ts}; feedback_labels={}
        def feedback_oracle(key):
            if key not in allowed: raise RuntimeError('final label requested before freeze')
            if key not in feedback_labels:
                task=tasks[key]; feedback_labels[key]=[int(evaluate_program(r['program'],task['visible']+task['hidden'])) for r in pools[key]]
            return feedback_labels[key]
        frozen=run_loops(records,feedback_oracle,source,effects)
        write_json(output/'frozen_loops.json',frozen); write_json(output/'feedback_labels.json',feedback_labels)
        journal.append('all_loops_frozen',{'sha256':digest(frozen)})
        labels={}
        for split,ts in banks.items():
            if split.startswith('final_'):
                for task in ts: labels[task['id']]=[int(evaluate_program(r['program'],task['visible']+task['hidden'])) for r in pools[task['id']]]
        write_json(output/'final_labels.json',labels)
        result=final_scores(frozen,records,labels); write_json(output/'results.json',result)
        assert all(file_hash(ROOT/name)==sha for name,sha in hashes.items())
        journal.append('completed',{'sha256':digest(result)}); seal_artifacts(output)
        return {'status':'completed','driver':frozen['driver'],'gate':frozen['gate'],
            'final':{mode:{panel:row['counts'] for panel,row in arm['rounds'][-1]['panels'].items()} for mode,arm in result.items()}}
    except BaseException as exc:
        write_json(output/'FAILED.json',{'message':str(exc),'traceback':traceback.format_exc()}); raise


def audit(output):
    assert not (output/'FAILED.json').exists()
    manifest=read(output/'artifact_manifest.json')
    present={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p.name not in ('artifact_manifest.json','audit.json')}
    assert present==set(manifest)
    for name,row in manifest.items(): assert file_hash(output/name)==row['sha256'],name
    for name,sha in read(output/'source_manifest.json').items():
        assert file_hash(ROOT/name)==sha and file_hash(output/'source'/name)==sha,name
    for name,sha in read(output/'source_provenance.json').items(): assert file_hash(ROOT/SOURCE/name)==sha,name
    source=read(ROOT/SOURCE/'results.json')
    source_records=build_records(read(ROOT/SOURCE/'protected_banks.json'),read(ROOT/SOURCE/'candidate_pools.json'))
    effects=extract_effects(source,source_records); assert digest(effects)==digest(read(output/'inherited_effects.json'))
    banks=generate(); assert digest(banks)==digest(read(output/'protected_banks.json'))
    pools=read(output/'candidate_pools.json'); calls=0; all_labels={}
    for split,ts in banks.items():
        for task in ts:
            unique={}
            for arm in ('v67','v73'):
                for row in source_candidates({'id':task['id'],'visible':task['visible']},arm,{},16): unique.setdefault(row['program'],row)
                calls+=1
            assert digest(list(unique.values()))==digest(pools[task['id']])
            all_labels[task['id']]=[int(evaluate_program(r['program'],task['visible']+task['hidden'])) for r in pools[task['id']]]
        print('confirmation audit bank replayed: '+split,flush=True)
    records=build_records(banks,pools); final_ids={t['id'] for split,ts in banks.items() if split.startswith('final_') for t in ts}
    def oracle(key):
        assert key not in final_ids
        return all_labels[key]
    frozen=run_loops(records,oracle,source,effects); assert digest(frozen)==digest(read(output/'frozen_loops.json'))
    for key,y in read(output/'final_labels.json').items(): assert all_labels[key]==y
    result=final_scores(frozen,records,all_labels); assert digest(result)==digest(read(output/'results.json'))
    events=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
    assert verify_journal(output/'events.jsonl')==3
    assert [r['kind'] for r in events]==['preregistered','all_loops_frozen','completed']
    assert events[1]['payload']['sha256']==digest(frozen) and events[2]['payload']['sha256']==digest(result)
    report={'status':'passed','candidate_calls_replayed':calls,'controller_arms':len(MODES),'checkpoints_per_arm':5,
        'scope':'one confirmation episode, same host interpreter; no independent semantic oracle'}
    write_json(output/'audit.json',report); return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); parser.add_argument('--audit',action='store_true')
    parser.add_argument('--prepare-only',action='store_true'); parser.add_argument('--prepared'); args=parser.parse_args()
    result=audit(ROOT/args.output) if args.audit else prepare_candidates(ROOT/args.output) if args.prepare_only else run(ROOT/args.output,ROOT/args.prepared if args.prepared else None)
    print(json.dumps(result,indent=2))
