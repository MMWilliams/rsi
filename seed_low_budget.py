"""Low-label improver comparison and first-edit effect evaluation."""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np

import seed_improver_transfer as core
from rsi.common import ROOT, digest, verify_journal, write_json
from rsi.retention_run import file_hash
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import train
from seed_source_search import read, build_records, export_model
from seed_meta import state_features, choose_tactic
from seed_integrated_v2 import admission, accept, predictions, remaining_views, purchase, train_records
from seed_confirmation import final_scores
from seed_replicate import pool_all
from seed_transfer_banks import changed_bank


OFFSETS = (9000,10000,11000,12000,13000,14000)
FROZEN_STATE = ROOT/'analysis/seed-low-budget-states.json'
DONOR_TACTICS = ('uniform','uncertainty','disagreement','novelty','combined')
SEQUENCE = ('disagreement','disagreement','uncertainty','combined')
ARMS = (('I0','learned'),('I0_full_scrambled','learned'),('static_sequence','schedule'),
        ('B0','learned'),('I4','learned')) + tuple(('fixed_'+t,t) for t in DONOR_TACTICS)
ORIGINAL_INHERITED = core.inherited_states
ORIGINAL_PATHS = core.source_paths
ORIGINAL_PROVENANCE = core.donor_provenance


def banks(offset):
    assert offset in OFFSETS
    return {'bootstrap':random_bank(207001+offset,2),
            'reservoir':random_bank(207002+offset,48),
            'admission':random_bank(207003+offset,36),
            'final_mixed':random_bank(207004+offset,24),
            'final_ast':random_bank(207005+offset,12,('ast_transition',)),
            'final_changed':changed_bank(207006+offset,12)}


def balanced_effects():
    """Five first-step actions on the same initial state in each prior donor."""
    effects = []
    for donor in core.DONORS:
        root = ROOT/'runs'/donor
        assert read(root/'audit.json')['status'] == 'passed'
        frozen = read(root/'frozen_loops.json')
        records = build_records(read(root/'protected_banks.json'),read(root/'candidate_pools.json'))
        opened = read(root/'opened_feedback_labels.json')
        bootstrap = []
        for record in records['bootstrap']:
            labels = np.asarray([opened[record['id']][str(i)] for i in range(len(record['rows']))],dtype=float)
            bootstrap.append({**record,'labels':labels})
        initial = train(bootstrap)
        initial_sha = digest(export_model(initial))
        first = frozen['arms']['fixed_uniform__argmax__proper_tie']['checkpoints'][0]
        assert first['model_sha256'] == initial_sha
        state = state_features(initial,remaining_views(records['reservoir'],{}),
                               'ensemble',0,first['admission']['correct'],len(records['admission']))
        for tactic in DONOR_TACTICS:
            arm = frozen['arms']['fixed_'+tactic+'__argmax__proper_tie']['checkpoints']
            assert arm[0]['model_sha256'] == initial_sha
            assert digest(arm[0]['admission']) == digest(first['admission'])
            old,child = arm[0]['admission'],arm[1]['candidate_admission']
            n = len(records['admission'])
            harmed = sum(a['correct'] and not b['correct'] for a,b in zip(old['rows'],child['rows']))
            effects.append({'episode':donor+'_balanced_first','round':1,'driver':'ensemble',
                            'tactic':tactic,'state':state,
                            'gain':(child['correct']-old['correct'])/n,
                            'harm':harmed/n,
                            'utility':(child['correct']-old['correct']-.25*harmed)/n})
    assert len(effects) == 15
    return effects


def inherited_states():
    previous = ORIGINAL_INHERITED()
    source = [dict(row) for row in previous['I0']]
    scrambled = [dict(row) for row in source]
    values = [row['utility'] for row in scrambled]
    random.Random(942).shuffle(values)
    for row,value in zip(scrambled,values): row['utility'] = value
    assert [row['utility'] for row in source] != [row['utility'] for row in scrambled]
    result = {'I0':source,'I0_full_scrambled':scrambled,'static_sequence':[],
              'B0':source+balanced_effects(),'I4':previous['I4']}
    result.update({'fixed_'+t:[] for t in DONOR_TACTICS})
    return result


def source_paths():
    return ORIGINAL_PATHS()+[ROOT/'seed_low_budget.py',ROOT/'EXPERIMENT-seed-low-budget-control.md']


def donor_provenance():
    result = ORIGINAL_PROVENANCE()
    for donor in core.DONORS:
        for name in ('opened_feedback_labels.json','protected_banks.json','candidate_pools.json'):
            path = ROOT/'runs'/donor/name
            result[path.relative_to(ROOT).as_posix()] = file_hash(path)
    return result


def loops(records,oracle,states,telemetry=None):
    arms = {}; saved = {}
    for name,mode in ARMS:
        started = time.perf_counter()
        known = [dict(row) for row in states[name]]
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
                if mode == 'learned': chosen,scores = choose_tactic(known,'ensemble',context)
                elif mode == 'schedule': chosen = SEQUENCE[round_index-1]
                else: chosen = mode
                acquired = purchase(active,remaining,chosen,oracle,purchased,allowance=16)
                child = train(train_records(bootstrap,records['reservoir'],purchased))
                child_measurement = admission(child,records['admission'],lambda key:oracle(key,None),'argmax')
                admitted = accept(measured,child_measurement,'proper_tie')
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
        arms[name] = {'mode':name,'policy':'argmax','gate':'proper_tie',
                      'candidate_queries':bootstrap_queries+64,
                      'bootstrap_queries':bootstrap_queries,'improvement_queries':64,
                      'checkpoints':checkpoints}
        saved[name] = {'model':export_model(active),'effects':known,
                       'policy':'argmax','gate':'proper_tie','driver':'ensemble'}
        if telemetry is not None:
            telemetry[name] = {'wall_seconds':time.perf_counter()-started,'model_fits':5,
                               'improvement_oracle_labels':64,'bootstrap_oracle_labels':bootstrap_queries,
                               'common_admission_candidate_labels':sum(len(r['rows']) for r in records['admission']),
                               'admission_assessments':5}
        print('low-budget frozen: '+name,flush=True)
    return {'driver':'ensemble','primary':'I0','arms':arms,'states':saved}


def configure():
    """Reuse the sealed prep/run shell; replace only this study's declared parts."""
    core.banks = banks
    core.FROZEN_STATE = FROZEN_STATE
    core.inherited_states = inherited_states
    core.source_paths = source_paths
    core.donor_provenance = donor_provenance
    core.loops = loops
    core.ARMS = tuple((name,mode,'proper_tie') for name,mode in ARMS)
    core.PRIMARY = 'I0'


def audit(output):
    assert not (output/'FAILED.json').exists()
    manifest = read(output/'artifact_manifest.json')
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()
              and p.name not in ('artifact_manifest.json','audit.json')}
    assert actual == set(manifest)
    for name,row in manifest.items(): assert file_hash(output/name) == row['sha256'],name
    for name,sha in read(output/'source_manifest.json').items():
        assert file_hash(ROOT/name) == sha and file_hash(output/'source'/name) == sha,name
    for name,sha in read(output/'donor_provenance.json').items(): assert file_hash(ROOT/name) == sha,name
    states = read(FROZEN_STATE)
    assert digest(states) == digest(inherited_states())
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
    def oracle(key,indices):
        assert key not in final_ids
        return labels[key] if indices is None else [labels[key][i] for i in indices]
    records = build_records(task_banks,pools)
    frozen = loops(records,oracle,states)
    assert digest(frozen) == digest(read(output/'frozen_loops.json'))
    for arm in frozen['arms'].values():
        assert [c['improvement_labels'] for c in arm['checkpoints']] == [0,16,32,48,64]
    result = final_scores(frozen,records,labels)
    assert digest(result) == digest(read(output/'results.json'))
    assert verify_journal(output/'events.jsonl') == 3
    events = [json.loads(line) for line in (output/'events.jsonl').read_text().splitlines()]
    assert [e['kind'] for e in events] == ['preregistered','all_loops_frozen','completed']
    assert events[1]['payload']['sha256'] == digest(frozen)
    assert events[2]['payload']['sha256'] == digest(result)
    report = {'status':'passed','offset':config['seed_offset'],
              'candidate_calls_replayed':2*len(pools),'arms':len(ARMS),'checkpoints_per_arm':5,
              'equal_improvement_labels_per_arm':64,
              'same_base_first_edit_tactics':list(DONOR_TACTICS),
              'scope':'same host interpreter; no independent semantic oracle'}
    write_json(output/'audit.json',report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output')
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--offset',type=int)
    parser.add_argument('--prepared')
    parser.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    configure()
    output = ROOT/args.output
    result = core.prepare(output,args.offset) if args.prepare else audit(output) if args.audit else core.run(output,ROOT/args.prepared)
    print(json.dumps(result,indent=2))
