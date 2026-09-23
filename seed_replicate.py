"""Independent v2 episode replication with bounded parallel candidate preparation."""
from __future__ import annotations
import argparse,json,shutil,time,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from rsi.common import ROOT,Journal,digest,write_json,verify_journal
from rsi.retention_run import file_hash,seal_artifacts
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_v2_banks import changed_bank
from seed_source_search import read,build_records
from seed_meta import extract_effects
from seed_integrated_v2 import loops,PRIMARY
from seed_confirmation import final_scores
from stitch_ten import source_candidates

SOURCE='runs/seed-source-search-20260917'


def banks_for(offset):
    return {'bootstrap':random_bank(207001+offset,6),'reservoir':random_bank(207002+offset,48),
        'admission':random_bank(207003+offset,36),'final_mixed':random_bank(207004+offset,24),
        'final_ast':random_bank(207005+offset,12,('ast_transition',)),'final_changed':changed_bank(207006+offset,12)}


def task_pool(public):
    unique={}; times={}
    for arm in ('v67','v73'):
        start=time.perf_counter(); rows=source_candidates(public,arm,{},16); times[arm]=time.perf_counter()-start
        for row in rows: unique.setdefault(row['program'],row)
    return public['id'],list(unique.values()),times


def pool_all(banks,workers=4):
    public=[{'id':t['id'],'visible':t['visible']} for tasks in banks.values() for t in tasks]
    pools={}; times={'v67':0.,'v73':0.}; started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for count,(key,rows,elapsed) in enumerate(executor.map(task_pool,public),1):
            pools[key]=rows
            for arm,value in elapsed.items(): times[arm]+=value
            if count%12==0: print(f'candidate tasks closed: {count}/{len(public)}',flush=True)
    return pools,{'parallel_wall_seconds':time.perf_counter()-started,'workers':workers,
                  'summed_worker_wall_seconds_by_source':times}


def prepare(output,offset):
    output.mkdir(parents=True,exist_ok=False); banks=banks_for(offset)
    visible=[digest(t['visible']) for tasks in banks.values() for t in tasks]
    assert len(visible)==len(set(visible))
    write_json(output/'config.json',{'seed_offset':offset,'workers':4})
    write_json(output/'protected_banks.json',banks)
    pools,times=pool_all(banks)
    write_json(output/'candidate_pools.json',pools); write_json(output/'generation_times.json',times)
    seal_artifacts(output)
    return {'status':'prepared','seed_offset':offset,'oracle_labels_opened':0}


def source_files():
    names=('seed_growth.py','seed_casebanks.py','seed_source_search.py','seed_meta.py','seed_v2_banks.py',
        'seed_integrated_v2.py','seed_confirmation.py','seed_replicate.py','stitch_ten.py','run_policy_transfer.py',
        'run_ast_v66.py','EXPERIMENT-seed-integration-v2.md','EXPERIMENT-seed-v2-replication.md')
    return sorted((ROOT/'rsi').glob('*.py'))+[ROOT/name for name in names]+[ROOT/'vendor/trapdoor-loom'/n for n in ('dsl.py','parse.py','trapdoor.py')]


def source_effects():
    result=read(ROOT/SOURCE/'results.json')
    records=build_records(read(ROOT/SOURCE/'protected_banks.json'),read(ROOT/SOURCE/'candidate_pools.json'))
    return extract_effects(result,records)


def run(output,prepared):
    output.mkdir(parents=True,exist_ok=False); journal=Journal(output/'events.jsonl')
    try:
        assert read(ROOT/SOURCE/'audit.json')['status']=='passed'
        cfg=read(prepared/'config.json'); offset=cfg['seed_offset']; banks=banks_for(offset)
        for name,row in read(prepared/'artifact_manifest.json').items(): assert file_hash(prepared/name)==row['sha256']
        assert digest(banks)==digest(read(prepared/'protected_banks.json'))
        hashes={p.relative_to(ROOT).as_posix():file_hash(p) for p in source_files()}
        for name in hashes:
            dest=output/'source'/name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,dest)
        write_json(output/'source_manifest.json',hashes); write_json(output/'config.json',cfg)
        provenance={name:file_hash(ROOT/SOURCE/name) for name in ('results.json','audit.json','protected_banks.json','candidate_pools.json')}
        write_json(output/'source_provenance.json',provenance)
        journal.append('preregistered',{'config':cfg,'primary':PRIMARY,'hashes':hashes,'source_provenance':provenance})
        pools=read(prepared/'candidate_pools.json'); assert all('oracle_correct' not in r for rows in pools.values() for r in rows)
        write_json(output/'protected_banks.json',banks); write_json(output/'candidate_pools.json',pools)
        write_json(output/'generation_times.json',read(prepared/'generation_times.json'))
        records=build_records(banks,pools); tasks={t['id']:t for ts in banks.values() for t in ts}
        effects=source_effects(); write_json(output/'inherited_effects.json',effects)
        final_ids={t['id'] for split,ts in banks.items() if split.startswith('final_') for t in ts}; opened={}
        def oracle(key,indices):
            if key in final_ids: raise RuntimeError('early final label request')
            if indices is None: indices=list(range(len(pools[key])))
            known=opened.setdefault(key,{})
            for index in indices:
                if index not in known: known[index]=int(evaluate_program(pools[key][index]['program'],tasks[key]['visible']+tasks[key]['hidden']))
            return [known[index] for index in indices]
        telemetry={}; frozen=loops(records,oracle,effects,telemetry)
        write_json(output/'frozen_loops.json',frozen); write_json(output/'loop_costs.json',telemetry)
        journal.append('all_loops_frozen',{'sha256':digest(frozen)})
        labels={key:[int(evaluate_program(row['program'],tasks[key]['visible']+tasks[key]['hidden'])) for row in pools[key]] for key in final_ids}
        write_json(output/'final_labels.json',labels); write_json(output/'opened_feedback_labels.json',opened)
        results=final_scores(frozen,records,labels); write_json(output/'results.json',results)
        assert all(file_hash(ROOT/name)==sha for name,sha in hashes.items())
        journal.append('completed',{'sha256':digest(results)}); seal_artifacts(output)
        primary=results[PRIMARY]
        return {'status':'completed','seed_offset':offset,'primary':PRIMARY,
                'primary_curve':[sum(p['counts']['deployed'] for p in c['panels'].values()) for c in primary['rounds']]}
    except BaseException as exc:
        write_json(output/'FAILED.json',{'message':str(exc),'traceback':traceback.format_exc()}); raise


def audit(output):
    assert not (output/'FAILED.json').exists()
    manifest=read(output/'artifact_manifest.json')
    actual={p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file() and p.name not in ('artifact_manifest.json','audit.json')}
    assert actual==set(manifest)
    for name,row in manifest.items(): assert file_hash(output/name)==row['sha256']
    for name,sha in read(output/'source_manifest.json').items(): assert file_hash(ROOT/name)==sha and file_hash(output/'source'/name)==sha
    for name,sha in read(output/'source_provenance.json').items(): assert file_hash(ROOT/SOURCE/name)==sha
    banks=banks_for(read(output/'config.json')['seed_offset']); assert digest(banks)==digest(read(output/'protected_banks.json'))
    pools,_=pool_all(banks); assert digest(pools)==digest(read(output/'candidate_pools.json'))
    tasks={t['id']:t for ts in banks.values() for t in ts}
    labels={key:[int(evaluate_program(row['program'],tasks[key]['visible']+tasks[key]['hidden'])) for row in rows] for key,rows in pools.items()}
    final_ids={t['id'] for split,ts in banks.items() if split.startswith('final_') for t in ts}
    for key,values in read(output/'opened_feedback_labels.json').items():
        for index,value in values.items(): assert labels[key][int(index)]==value
    def oracle(key,indices):
        assert key not in final_ids
        return labels[key] if indices is None else [labels[key][index] for index in indices]
    effects=source_effects(); assert digest(effects)==digest(read(output/'inherited_effects.json'))
    records=build_records(banks,pools); frozen=loops(records,oracle,effects)
    assert digest(frozen)==digest(read(output/'frozen_loops.json'))
    for arm in frozen['arms'].values(): assert [r['improvement_labels'] for r in arm['checkpoints']]==[0,48,96,144,192]
    result=final_scores(frozen,records,labels); assert digest(result)==digest(read(output/'results.json'))
    events=[json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
    assert verify_journal(output/'events.jsonl')==3
    assert events[1]['kind']=='all_loops_frozen' and events[1]['payload']['sha256']==digest(frozen)
    assert events[2]['kind']=='completed' and events[2]['payload']['sha256']==digest(result)
    report={'status':'passed','seed_offset':read(output/'config.json')['seed_offset'],'candidate_calls_replayed':2*len(pools),
        'arms':32,'checkpoints_per_arm':5,'equal_improvement_labels_per_arm':192,
        'scope':'independent seed episode; same host interpreter'}
    write_json(output/'audit.json',report); return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output'); parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--offset',type=int); parser.add_argument('--prepared'); parser.add_argument('--audit',action='store_true'); args=parser.parse_args()
    result=prepare(ROOT/args.output,args.offset) if args.prepare else audit(ROOT/args.output) if args.audit else run(ROOT/args.output,ROOT/args.prepared)
    print(json.dumps(result,indent=2))
