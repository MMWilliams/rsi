"""Fresh same-base transfer of frozen improver checkpoints."""
from __future__ import annotations

import argparse
import json
import random
import shutil
import time
import traceback
from pathlib import Path

import numpy as np

from rsi.common import ROOT, Journal, digest, verify_journal, write_json
from rsi.retention_run import file_hash, seal_artifacts
from rsi.semantic_invention import evaluate_program
from seed_growth import train
from seed_source_search import read, build_records, export_model
from seed_meta import state_features, choose_tactic
from seed_integrated_v2 import admission, accept, predictions, remaining_views, purchase, train_records
from seed_confirmation import final_scores
from seed_replicate import pool_all
from seed_transfer_banks import banks


DONORS = ('seed-integration-v2-20260917', 'seed-v2-replica-1', 'seed-v2-replica-2')
DONOR_ARM = 'meta4_online__argmax__proper_tie'
FROZEN_STATE = ROOT/'analysis/seed-transfer-inherited-states.json'
ARMS = (
    ('I0', 'learned', 'proper_tie'),
    ('I2', 'learned', 'proper_tie'),
    ('I4', 'learned', 'proper_tie'),
    ('I4_scrambled', 'learned', 'proper_tie'),
    ('empty', 'learned', 'proper_tie'),
    ('I0_online', 'online', 'proper_tie'),
    ('I4_online', 'online', 'proper_tie'),
    ('fixed_uniform', 'uniform', 'proper_tie'),
    ('fixed_novelty', 'novelty', 'proper_tie'),
    ('fixed_disagreement', 'disagreement', 'proper_tie'),
    ('fixed_combined', 'combined', 'proper_tie'),
    ('fixed_uncertainty_strict', 'uncertainty', 'strict'),
)
PRIMARY = 'I4'


def source_paths():
    return sorted((ROOT/'rsi').glob('*.py')) + [ROOT/name for name in (
        'seed_growth.py','seed_casebanks.py','seed_source_search.py','seed_meta.py',
        'seed_v2_banks.py','seed_integrated_v2.py','seed_confirmation.py','seed_replicate.py',
        'seed_transfer_banks.py','seed_improver_transfer.py','stitch_ten.py',
        'run_policy_transfer.py','run_ast_v66.py','EXPERIMENT-seed-improver-transfer.md',
        'EXPERIMENT-seed-integration-v2.md','EXPERIMENT-seed-v2-replication.md')] + [
        ROOT/'vendor/trapdoor-loom'/name for name in ('dsl.py','parse.py','trapdoor.py')]


def donor_provenance():
    paths = [ROOT/'runs'/name/'frozen_loops.json' for name in DONORS]
    paths += [ROOT/'runs'/name/'audit.json' for name in DONORS]
    paths += [ROOT/'runs/seed-source-search-20260917'/name for name in
              ('results.json','audit.json','candidate_pools.json','protected_banks.json')]
    paths.append(FROZEN_STATE)
    return {p.relative_to(ROOT).as_posix():file_hash(p) for p in paths}


def inherited_states():
    source = read(ROOT/'runs/seed-integration-v2-20260917/inherited_effects.json')
    assert len(source) == 60
    extras = {2:[], 4:[]}
    for donor in DONORS:
        path = ROOT/'runs'/donor
        assert read(path/'audit.json')['status'] == 'passed'
        state = read(path/'frozen_loops.json')['states'][DONOR_ARM]['effects']
        assert digest(state[:60]) == digest(source)
        assert len(state) == 64
        for depth in (2,4):
            extras[depth].extend({**record,'donor':donor} for record in state[60:60+depth])
    four = source + extras[4]
    scrambled = [dict(record) for record in four]
    values = [record['utility'] for record in scrambled[60:]]
    random.Random(941).shuffle(values)
    for record,value in zip(scrambled[60:],values): record['utility'] = value
    return {'I0':source, 'I2':source+extras[2], 'I4':four,
            'I4_scrambled':scrambled, 'empty':[], 'I0_online':source,
            'I4_online':four, **{'fixed_'+name:[] for name in
              ('uniform','novelty','disagreement','combined')},
            'fixed_uncertainty_strict':[]}


def prepare(output, offset):
    output.mkdir(parents=True, exist_ok=False)
    task_banks = banks(offset)
    assert len({digest(t['visible']) for tasks in task_banks.values() for t in tasks}) == sum(map(len,task_banks.values()))
    write_json(output/'config.json', {'seed_offset':offset,'workers':4})
    write_json(output/'protected_banks.json', task_banks)
    pools,timing = pool_all(task_banks, workers=4)
    assert all('oracle_correct' not in row for rows in pools.values() for row in rows)
    write_json(output/'candidate_pools.json', pools)
    write_json(output/'generation_times.json', timing)
    seal_artifacts(output)
    return {'status':'prepared','seed_offset':offset,'tasks':sum(map(len,task_banks.values())),
            'oracle_labels_opened':0}


def loops(records, oracle, states, telemetry=None):
    arms = {}; saved = {}
    for name, tactic, gate in ARMS:
        started = time.perf_counter()
        known = [dict(record) for record in states[name]]
        bootstrap = []; bootstrap_queries = 0
        for record in records['bootstrap']:
            ids = list(range(len(record['rows'])))
            labels = oracle(record['id'],ids)
            bootstrap_queries += len(ids)
            bootstrap.append({**record,'labels':np.asarray(labels,dtype=float)})
        purchased = {}; active = train(bootstrap)
        measured = admission(active,records['admission'],lambda key:oracle(key,None),'argmax')
        checkpoints = []
        for round_index in range(5):
            chosen = None; scores = {}; acquired = []; admitted = None; child_measurement = None
            if round_index:
                remaining = remaining_views(records['reservoir'],purchased)
                context = state_features(active,remaining,'ensemble',round_index-1,
                                         measured['correct'],len(records['admission']))
                if tactic in ('learned','online'):
                    chosen,scores = choose_tactic(known,'ensemble',context)
                else:
                    chosen = tactic
                acquired = purchase(active,remaining,chosen,oracle,purchased,allowance=48)
                child = train(train_records(bootstrap,records['reservoir'],purchased))
                child_measurement = admission(child,records['admission'],lambda key:oracle(key,None),'argmax')
                admitted = accept(measured,child_measurement,gate)
                if tactic == 'online':
                    n = len(records['admission'])
                    harmed = sum(a['correct'] and not b['correct'] for a,b in
                                 zip(measured['rows'],child_measurement['rows']))
                    known.append({'episode':'transfer_online','round':round_index,'driver':'ensemble',
                                  'tactic':chosen,'state':context,
                                  'gain':(child_measurement['correct']-measured['correct'])/n,
                                  'harm':harmed/n,
                                  'utility':(child_measurement['correct']-measured['correct']-.25*harmed)/n})
                if admitted: active,measured = child,child_measurement
            final = {split:predictions(active,panel,'argmax') for split,panel in records.items()
                     if split.startswith('final_')}
            checkpoints.append({'round':round_index,'tactic':chosen,'query_log':acquired,
                                'effect_scores':scores,'accepted':admitted,
                                'admission':measured,'candidate_admission':child_measurement,
                                'final_predictions':final,
                                'improvement_labels':sum(map(len,purchased.values())),
                                'model_sha256':digest(export_model(active)),
                                'controller_sha256':digest(known)})
        arms[name] = {'mode':name,'policy':'argmax','gate':gate,
                      'candidate_queries':bootstrap_queries+192,
                      'bootstrap_queries':bootstrap_queries,'improvement_queries':192,
                      'checkpoints':checkpoints}
        saved[name] = {'model':export_model(active),'effects':known,
                       'policy':'argmax','gate':gate,'driver':'ensemble'}
        if telemetry is not None:
            telemetry[name] = {'wall_seconds':time.perf_counter()-started,
                               'model_fits':5,'improvement_oracle_labels':192,
                               'bootstrap_oracle_labels':bootstrap_queries,
                               'common_admission_candidate_labels':sum(len(r['rows']) for r in records['admission']),
                               'admission_assessments':5}
        print('transfer frozen: '+name,flush=True)
    return {'driver':'ensemble','primary':PRIMARY,'arms':arms,'states':saved}


def run(output, prepared):
    output.mkdir(parents=True, exist_ok=False)
    journal = Journal(output/'events.jsonl')
    try:
        manifest = read(prepared/'artifact_manifest.json')
        for name,row in manifest.items(): assert file_hash(prepared/name) == row['sha256']
        config = read(prepared/'config.json')
        task_banks = banks(config['seed_offset'])
        assert digest(task_banks) == digest(read(prepared/'protected_banks.json'))
        hashes = {p.relative_to(ROOT).as_posix():file_hash(p) for p in source_paths()}
        for name in hashes:
            destination = output/'source'/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name,destination)
        provenance = donor_provenance()
        states = read(FROZEN_STATE)
        assert digest(states) == digest(inherited_states())
        write_json(output/'source_manifest.json',hashes)
        write_json(output/'donor_provenance.json',provenance)
        write_json(output/'inherited_states.json',states)
        write_json(output/'config.json',config)
        journal.append('preregistered',{'config':config,'primary':PRIMARY,
                                        'source_hashes':hashes,'donor_hashes':provenance,
                                        'inherited_sha256':digest(states)})
        pools = read(prepared/'candidate_pools.json')
        assert all('oracle_correct' not in r for rows in pools.values() for r in rows)
        write_json(output/'protected_banks.json',task_banks)
        write_json(output/'candidate_pools.json',pools)
        write_json(output/'generation_times.json',read(prepared/'generation_times.json'))
        records = build_records(task_banks,pools)
        tasks = {t['id']:t for group in task_banks.values() for t in group}
        final_ids = {t['id'] for split,group in task_banks.items() if split.startswith('final_') for t in group}
        opened = {}
        def oracle(key, indices):
            if key in final_ids: raise RuntimeError('early final label request')
            if indices is None: indices = list(range(len(pools[key])))
            known = opened.setdefault(key,{})
            for index in indices:
                if index not in known:
                    known[index] = int(evaluate_program(pools[key][index]['program'],
                                                       tasks[key]['visible']+tasks[key]['hidden']))
            return [known[index] for index in indices]
        telemetry = {}
        frozen = loops(records,oracle,states,telemetry)
        write_json(output/'frozen_loops.json',frozen)
        write_json(output/'loop_costs.json',telemetry)
        journal.append('all_loops_frozen',{'sha256':digest(frozen)})
        labels = {key:[int(evaluate_program(row['program'],tasks[key]['visible']+tasks[key]['hidden']))
                       for row in pools[key]] for key in final_ids}
        write_json(output/'final_labels.json',labels)
        write_json(output/'opened_feedback_labels.json',opened)
        result = final_scores(frozen,records,labels)
        write_json(output/'results.json',result)
        assert all(file_hash(ROOT/name)==sha for name,sha in hashes.items())
        assert all(file_hash(ROOT/name)==sha for name,sha in provenance.items())
        journal.append('completed',{'sha256':digest(result)})
        seal_artifacts(output)
        primary = result[PRIMARY]
        return {'status':'completed','offset':config['seed_offset'],
                'primary_curve':[sum(p['counts']['deployed'] for p in c['panels'].values())
                                 for c in primary['rounds']]}
    except BaseException as exc:
        write_json(output/'FAILED.json',{'message':str(exc),'traceback':traceback.format_exc()})
        raise


def audit(output):
    assert not (output/'FAILED.json').exists()
    manifest = read(output/'artifact_manifest.json')
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()
              and p.name not in ('artifact_manifest.json','audit.json')}
    assert actual == set(manifest)
    for name,row in manifest.items(): assert file_hash(output/name) == row['sha256'], name
    for name,sha in read(output/'source_manifest.json').items():
        assert file_hash(ROOT/name) == sha and file_hash(output/'source'/name) == sha, name
    for name,sha in read(output/'donor_provenance.json').items(): assert file_hash(ROOT/name) == sha, name
    states = read(FROZEN_STATE)
    assert digest(states) == digest(inherited_states())
    assert digest(states) == digest(read(output/'inherited_states.json'))
    config = read(output/'config.json')
    task_banks = banks(config['seed_offset'])
    assert digest(task_banks) == digest(read(output/'protected_banks.json'))
    pools,_ = pool_all(task_banks,workers=4)
    assert digest(pools) == digest(read(output/'candidate_pools.json'))
    tasks = {t['id']:t for group in task_banks.values() for t in group}
    labels = {key:[int(evaluate_program(row['program'],tasks[key]['visible']+tasks[key]['hidden']))
                   for row in rows] for key,rows in pools.items()}
    for key,values in read(output/'opened_feedback_labels.json').items():
        for index,value in values.items(): assert labels[key][int(index)] == value
    final_ids = {t['id'] for split,group in task_banks.items() if split.startswith('final_') for t in group}
    def oracle(key, indices):
        assert key not in final_ids
        return labels[key] if indices is None else [labels[key][i] for i in indices]
    records = build_records(task_banks,pools)
    frozen = loops(records,oracle,states)
    assert digest(frozen) == digest(read(output/'frozen_loops.json'))
    for arm in frozen['arms'].values():
        assert [c['improvement_labels'] for c in arm['checkpoints']] == [0,48,96,144,192]
    result = final_scores(frozen,records,labels)
    assert digest(result) == digest(read(output/'results.json'))
    assert verify_journal(output/'events.jsonl') == 3
    events = [json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
    assert [e['kind'] for e in events] == ['preregistered','all_loops_frozen','completed']
    assert events[1]['payload']['sha256'] == digest(frozen)
    assert events[2]['payload']['sha256'] == digest(result)
    report = {'status':'passed','offset':config['seed_offset'],
              'candidate_calls_replayed':2*len(pools),'arms':len(ARMS),'checkpoints_per_arm':5,
              'equal_improvement_labels_per_arm':192,'scope':'same host interpreter; no independent semantic oracle'}
    write_json(output/'audit.json',report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--offset',type=int)
    parser.add_argument('--prepared')
    parser.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    output = ROOT/args.output
    result = prepare(output,args.offset) if args.prepare else audit(output) if args.audit else run(output,ROOT/args.prepared)
    print(json.dumps(result,indent=2))
