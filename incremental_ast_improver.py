"""Protected parent/admission/child transfer for AST query-value improvers."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from ast_feedback_replay_update import pools_for, updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs, rank
from ast_query_allocation_development import features, fit, predict, allocate, fixed, source_data


DEST = ROOT / 'runs/incremental-ast-improver-20260918'
QUERY = ROOT / 'runs/ast-query-allocation-transfer-20260918'
MIXED = ROOT / 'runs/full-mixed-ast-sensor-20260918'
RANKER = ROOT / 'analysis/ast-feedback-replay-model.json'
SOURCE = ROOT / 'analysis/ast-query-allocation-development.json'
ADMISSION_MIXED = tuple(range(902348, 902351))
ADMISSION_AST = tuple(range(902351, 902354))
TRANSFER_MIXED = tuple(range(902354, 902360))
TRANSFER_AST = tuple(range(902360, 902366))
PARENTS = ('i0', 'i1', 'scrambled', 'duplicate')
FIXED = ('one_each', 'random', 'entropy', 'disagreement')
LAMBDA = 100.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_banks(mixed_seeds, ast_seeds):
    tasks = []
    for seed in mixed_seeds:
        tasks.extend({**task, 'seed': seed, 'stream': 'mixed'}
                     for task in random_bank(seed, 48, FAMILIES, visible=1, hidden=23)
                     if task['family'] == 'ast_transition')
    for seed in ast_seeds:
        tasks.extend({**task, 'seed': seed, 'stream': 'ast_only'}
                     for task in random_bank(seed, 8, ('ast_transition',), visible=1, hidden=23))
    assert len(tasks) == 8 * (len(mixed_seeds) + len(ast_seeds))
    assert len({task['id'] for task in tasks}) == len(tasks)
    return tasks


def data_rows(tasks, records, predicted, outcomes, kind):
    lookup = {row['id']: row for row in records}
    labels = {row['id']: row for row in outcomes}
    assert len(lookup) == len(records) and len(labels) == len(outcomes)
    x = []; y1 = []; y2 = []; ids = []; streams = []
    for task in tasks:
        key = task['id']; record = lookup[key]; outcome = labels[key]
        if kind == 'query':
            call = outcome['correct_by_calls']
            record = {**record, 'first_probe': {'top20_entropy': record['first_probe']}}
        elif kind == 'mixed':
            c = outcome['correct']
            call = [c['ast_ranker'], c['top20_one'], c['top20_two']]
        else: raise ValueError(kind)
        x.append(features(task, record, predicted[key]))
        y1.append(int(call[1]) - int(call[0]))
        y2.append(int(call[2]) - int(call[1]))
        ids.append(key)
        streams.append(task['stream'] if 'stream' in task else 'mixed')
    return {'x': np.stack(x), 'y1': np.asarray(y1, dtype=float),
            'y2': np.asarray(y2, dtype=float), 'ids': ids, 'streams': streams}


def source_tables():
    original, x0, base, one, two = source_data()
    assert len(original) == 96 and LAMBDA == json.loads(SOURCE.read_text())['chosen_lambda']
    zero = {'x': x0, 'y1': one-base, 'y2': two-one,
            'ids': [t['id'] for t in original], 'streams': [t['stream'] for t in original]}
    qt = json.loads((QUERY/'sealed_bank.json').read_text())
    qr = json.loads((QUERY/'frozen_records.json').read_text())
    qp = json.loads((QUERY/'predicted_probe_outputs.json').read_text())
    qo = json.loads((QUERY/'results.json').read_text())['tasks']
    mt = [t for t in json.loads((MIXED/'sealed_bank.json').read_text())
          if t['family'] == 'ast_transition']
    mr = [r for r in json.loads((MIXED/'frozen_decisions.json').read_text())
          if 'order' in r]
    mp = json.loads((MIXED/'predicted_probe_outputs.json').read_text())
    mo = [r for r in json.loads((MIXED/'results.json').read_text())['tasks']
          if r['family'] == 'ast_transition']
    q = data_rows(qt, qr, qp, qo, 'query')
    m = data_rows(mt, mr, mp, mo, 'mixed')
    assert len(q['ids']) == 96 and len(m['ids']) == 48
    assert len(set(zero['ids'] + q['ids'] + m['ids'])) == 240
    added = join(q, m)
    scramble = {key: np.copy(added[key]) for key in ('y1', 'y2')}
    for stream in ('mixed', 'ast_only'):
        idx = np.asarray([i for i, s in enumerate(added['streams']) if s == stream])
        assert len(idx) >= 2
        for key in ('y1', 'y2'):
            scramble[key][idx] = np.roll(added[key][idx], 1)
    scrambled = {**added, **scramble}
    repeat_idx = np.arange(144) % 96
    repeated = {'x': zero['x'][repeat_idx], 'y1': zero['y1'][repeat_idx],
                'y2': zero['y2'][repeat_idx],
                'ids': [zero['ids'][i] for i in repeat_idx],
                'streams': [zero['streams'][i] for i in repeat_idx]}
    return {'i0': zero, 'i1': join(zero, added),
            'scrambled': join(zero, scrambled), 'duplicate': join(zero, repeated)}


def join(a, b):
    return {'x': np.concatenate([a['x'], b['x']]),
            'y1': np.concatenate([a['y1'], b['y1']]),
            'y2': np.concatenate([a['y2'], b['y2']]),
            'ids': a['ids'] + b['ids'], 'streams': a['streams'] + b['streams']}


def train(table):
    return fit(table['x'], table['y1'], table['y2'], LAMBDA)


def serialized(model):
    return {key: value.tolist() for key, value in zip(('mean', 'scale', 'w1', 'w2'), model)}


def unserialize(raw):
    return tuple(np.asarray(raw[key], dtype=float)
                 for key in ('mean', 'scale', 'w1', 'w2'))


def prepare_stage(stage, mixed, ast, models):
    directory = DEST / stage
    if directory.exists(): raise RuntimeError(f'{stage} already prepared')
    start = time.perf_counter()
    tasks = task_banks(mixed, ast)
    pools, generation_seconds = pools_for(tasks)
    public = [({'id': task['id'],
                'probe_inputs': [text for text, _ in task['hidden'][:8]]},
               pools[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted = dict(executor.map(predicted_outputs, public))
    ranker = updated_model()
    records = []
    for task in tasks:
        key = task['id']; rows = pools[key]
        scores, order = rank(task, rows, ranker)
        first = choose_probe(key, predicted[key], order, scores,
                             set(range(len(rows))), [], 'top20_entropy')
        records.append({'id': key, 'seed': task['seed'], 'stream': task['stream'],
                        'pool_sha256': digest(rows), 'scores': scores,
                        'order': order, 'first_probe': first})
    allocations = make_allocations(tasks, records, predicted, models)
    manifest = {'stage': stage, 'protocol': 'EXPERIMENT-incremental-ast-improver.md',
                'mixed_seeds': mixed, 'ast_seeds': ast, 'tasks': len(tasks),
                'calls_per_bank': 8, 'ranker_sha256': sha(RANKER),
                'runner_sha256': sha(ROOT/'incremental_ast_improver.py'),
                'sensor_sha256': sha(ROOT/'ast_probe_sensor_development.py'),
                'model_sha256': sha(DEST/('parent_models.json' if stage == 'admission'
                                          else 'child_models.json')),
                'candidate_count': sum(map(len, pools.values())),
                'predicted_output_cells': sum(len(rows)*8 for rows in pools.values()),
                'generation_seconds': sum(generation_seconds.values()),
                'preparation_wall_seconds': time.perf_counter()-start}
    write_json(directory/'sealed_bank.json', tasks)
    write_json(directory/'candidate_pools.json', pools)
    write_json(directory/'predicted_probe_outputs.json', predicted)
    write_json(directory/'frozen_records.json', records)
    write_json(directory/'frozen_allocations.json', allocations)
    write_json(directory/'manifest.json', manifest)
    return manifest


def make_allocations(tasks, records, predicted, models):
    by_id = {r['id']: r for r in records}; result = {}
    for seed in sorted({task['seed'] for task in tasks}):
        group = [task for task in tasks if task['seed'] == seed]
        assert len(group) == 8
        ids = [task['id'] for task in group]
        x = np.stack([features(task, {**by_id[task['id']],
                                      'first_probe': {'top20_entropy':
                                                      by_id[task['id']]['first_probe']}},
                               predicted[task['id']]) for task in group])
        choices = {}
        for name, model in models.items():
            u1, u2 = predict(model, x)
            choices[name] = dict(zip(ids, allocate(u1, u2, 8)))
        for name in FIXED:
            choices[name] = dict(zip(ids, fixed(ids, x, 8, name)))
        assert all(sum(choice.values()) == 8 for choice in choices.values())
        result[str(seed)] = choices
    return result


def score_stage(stage):
    directory = DEST / stage
    if (directory/'results.json').exists(): raise RuntimeError(f'{stage} already scored')
    manifest = json.loads((directory/'manifest.json').read_text())
    assert manifest['runner_sha256'] == sha(ROOT/'incremental_ast_improver.py')
    assert manifest['ranker_sha256'] == sha(RANKER)
    assert manifest['sensor_sha256'] == sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['model_sha256'] == sha(DEST/('parent_models.json' if stage == 'admission'
                                                else 'child_models.json'))
    tasks = json.loads((directory/'sealed_bank.json').read_text())
    pools = json.loads((directory/'candidate_pools.json').read_text())
    predicted = json.loads((directory/'predicted_probe_outputs.json').read_text())
    records = json.loads((directory/'frozen_records.json').read_text())
    allocations = json.loads((directory/'frozen_allocations.json').read_text())
    outcomes = []
    for task, record in zip(tasks, records):
        key = task['id']; rows = pools[key]; matrix = predicted[key]
        assert record['id'] == key and record['pool_sha256'] == digest(rows)
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in rows]
        order = record['order']; scores = record['scores']
        correctness = [bool(labels[order[0]])]; used = []; remaining = set(range(len(rows)))
        for n in (1, 2):
            j = record['first_probe'] if n == 1 else choose_probe(
                key, matrix, order, scores, remaining, used, 'top20_entropy')
            used.append(j)
            matched = {i for i in remaining if matrix[i][j] == task['hidden'][j][1]}
            if matched: remaining = matched
            index = next((i for i in order if i in remaining), order[0])
            correctness.append(bool(labels[index]))
        outcomes.append({'id': key, 'seed': task['seed'], 'stream': task['stream'],
                         'reachable': any(labels), 'correct_by_calls': correctness,
                         'query_indices': used})
    by_id = {row['id']: row for row in outcomes}
    by_bank = []
    for seed in sorted({task['seed'] for task in tasks}):
        group = [r for r in outcomes if r['seed'] == seed]
        scores = {name: sum(by_id[key]['correct_by_calls'][calls]
                            for key, calls in mapping.items())
                  for name, mapping in allocations[str(seed)].items()}
        by_bank.append({'seed': seed, 'stream': group[0]['stream'],
                        'reachable': sum(r['reachable'] for r in group),
                        'no_query': sum(r['correct_by_calls'][0] for r in group),
                        'correct': scores})
    names = (*PARENTS, *FIXED)
    summary = {'stage': stage, 'tasks': len(tasks),
               'reachable': sum(r['reachable'] for r in outcomes),
               'no_query': sum(b['no_query'] for b in by_bank),
               'logical_calls_per_policy': 8*len(by_bank),
               'acquisition_probe_calls': 2*len(tasks) if stage == 'admission' else 0,
               'correct': {name: sum(b['correct'][name] for b in by_bank) for name in names},
               'by_bank': by_bank}
    write_json(directory/'results.json', {'summary': summary, 'tasks': outcomes})
    return summary


def prepare_parents():
    if DEST.exists(): raise RuntimeError('run already exists')
    tables = source_tables()
    models = {name: train(tables[name]) for name in PARENTS}
    original = json.loads(SOURCE.read_text())['model']
    assert all(np.allclose(models['i0'][i], np.asarray(original[key]))
               for i, key in enumerate(('mean', 'scale', 'w1', 'w2')))
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in (
        SOURCE, RANKER, QUERY/'sealed_bank.json', QUERY/'frozen_records.json',
        QUERY/'predicted_probe_outputs.json', QUERY/'results.json',
        MIXED/'sealed_bank.json', MIXED/'frozen_decisions.json',
        MIXED/'predicted_probe_outputs.json', MIXED/'results.json')}
    write_json(DEST/'source_manifest.json', {'source_hashes': source_hashes,
                                              'source_tasks': {name: len(tables[name]['ids'])
                                                               for name in PARENTS},
                                              'lambda': LAMBDA})
    write_json(DEST/'parent_models.json', {name: serialized(model)
                                            for name, model in models.items()})
    return prepare_stage('admission', ADMISSION_MIXED, ADMISSION_AST, models)


def train_children():
    if (DEST/'child_models.json').exists(): raise RuntimeError('children already exist')
    assert (DEST/'admission/frozen_allocations.json').exists()
    results = json.loads((DEST/'admission/results.json').read_text())['tasks']
    tasks = json.loads((DEST/'admission/sealed_bank.json').read_text())
    records = json.loads((DEST/'admission/frozen_records.json').read_text())
    predicted = json.loads((DEST/'admission/predicted_probe_outputs.json').read_text())
    admission = data_rows(tasks, records, predicted, results, 'query')
    tables = source_tables()
    children = {name: train(join(tables[name], admission)) for name in PARENTS}
    write_json(DEST/'child_models.json', {name: serialized(model)
                                           for name, model in children.items()})
    write_json(DEST/'child_training.json', {'admission_task_ids': admission['ids'],
                                            'admission_results_sha256': sha(DEST/'admission/results.json'),
                                            'source_manifest_sha256': sha(DEST/'source_manifest.json'),
                                            'child_training_tasks': {name: len(tables[name]['ids'])+len(tasks)
                                                                     for name in PARENTS}})
    return prepare_stage('transfer', TRANSFER_MIXED, TRANSFER_AST, children)


def score_transfer():
    result = score_stage('transfer')
    write_json(DEST/'summary.json', summarize())
    return result


def summarize():
    admission = json.loads((DEST/'admission/results.json').read_text())['summary']
    transfer = json.loads((DEST/'transfer/results.json').read_text())['summary']
    diffs = [b['correct']['i1']-b['correct']['i0'] for b in transfer['by_bank']]
    strongest = max(FIXED, key=lambda name: transfer['correct'][name])
    # Exact equal-weight bank bootstrap of paired sums via discrete convolution.
    counts = {0: 1}
    for _ in diffs:
        next_counts = {}
        for total, count in counts.items():
            for d in diffs:
                next_counts[total+d] = next_counts.get(total+d, 0) + count
        counts = next_counts
    total = len(diffs)**len(diffs)
    cumulative = 0; lower = upper = None
    for value, count in sorted(counts.items()):
        cumulative += count
        if lower is None and cumulative/total >= .025: lower = value
        if upper is None and cumulative/total >= .975: upper = value
    gate = {'positive_banks': sum(d > 0 for d in diffs),
            'paired_differences': diffs, 'bootstrap_95_sum': [lower, upper],
            'strongest_fixed': strongest,
            'passed': sum(d > 0 for d in diffs) >= 8 and lower > 0
                      and transfer['correct']['i1'] >= transfer['correct'][strongest]}
    return {'scope': 'fixed AST query-allocation improver, synthetic string programs',
            'admission': admission, 'transfer': transfer, 'child_growth_gate': gate,
            'source_acquisition_tasks': {'i0': 96, 'i1': 240,
                                         'scrambled': 240, 'duplicate': 240},
            'new_admission_tasks_each': 48,
            'new_admission_probe_outputs_shared': 96,
            'transfer_logical_calls_per_policy': 96}


def main():
    actions = {'prepare_parents': prepare_parents,
               'score_admission': lambda: score_stage('admission'),
               'train_children': train_children, 'score_transfer': score_transfer}
    print(json.dumps(actions[sys.argv[1]](), indent=2))


if __name__ == '__main__': main()
