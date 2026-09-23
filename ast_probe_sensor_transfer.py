"""Fresh one- and two-output-query evaluator transfer on wide AST pools."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from ast_feedback_replay_update import pools_for
from ast_probe_sensor_development import MODES, choose_probe
from active_probe_diagnostic import program_output


DEST = ROOT / 'runs/ast-probe-sensor-transfer-20260918'
MODEL = ROOT / 'analysis/ast-feedback-replay-model.json'
MIXED_SEEDS = tuple(range(902318, 902324))
AST_SEEDS = tuple(range(902324, 902330))


def target_tasks():
    tasks = []
    for seed in MIXED_SEEDS:
        for task in random_bank(seed, 48, FAMILIES, visible=1, hidden=23):
            if task['family'] == 'ast_transition':
                tasks.append({**task, 'seed': seed, 'stream': 'mixed'})
    for seed in AST_SEEDS:
        tasks.extend({**task, 'seed': seed, 'stream': 'ast_only'}
                     for task in random_bank(seed, 8, ('ast_transition',), visible=1, hidden=23))
    return tasks


def predicted_outputs(item):
    public, rows = item
    return public['id'], [[program_output(row['program'], probe)
                           for probe in public['probe_inputs']] for row in rows]


def rank(task, rows, model_data):
    import numpy as np
    import torch
    from ast_evaluator_feedback import features
    model, mean, scale = model_data
    x = np.asarray(features(task, rows), dtype=np.float32)
    with torch.no_grad():
        scores = model(torch.from_numpy((x - mean) / scale)).numpy()
    order = sorted(range(len(rows)), key=lambda i: (-float(scores[i]),
                   len(rows[i]['program']), rows[i]['program']))
    return scores.tolist(), order


def prepare():
    if DEST.exists():
        raise RuntimeError('fresh transfer directory already exists')
    tasks = target_tasks()
    start = time.perf_counter()
    pools, elapsed = pools_for(tasks)
    public = [({'id': task['id'],
                'probe_inputs': [text for text, _ in task['hidden'][:8]]}, pools[task['id']])
              for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        predicted = dict(executor.map(predicted_outputs, public))
    from ast_feedback_replay_update import updated_model
    model = updated_model()
    records = []
    for task in tasks:
        key = task['id']; rows = pools[key]
        scores, order = rank(task, rows, model)
        matrix = predicted[key]
        first = {mode: choose_probe(key, matrix, order, scores,
                                    set(range(len(rows))), [], mode)
                 for mode in MODES}
        records.append({'id': key, 'seed': task['seed'], 'stream': task['stream'],
                        'pool_sha256': digest(rows), 'scores': scores, 'order': order,
                        'first_probe': first})
    manifest = {'protocol': 'EXPERIMENT-ast-probe-sensor-transfer.md',
                'mixed_seeds': MIXED_SEEDS, 'ast_only_seeds': AST_SEEDS,
                'tasks': len(tasks), 'query_modes': MODES,
                'model_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256((ROOT / 'ast_probe_sensor_transfer.py').read_bytes()).hexdigest(),
                'policy_sha256': hashlib.sha256((ROOT / 'ast_probe_sensor_development.py').read_bytes()).hexdigest(),
                'candidate_count': sum(len(rows) for rows in pools.values()),
                'generation_seconds': sum(elapsed.values()),
                'preparation_wall_seconds': time.perf_counter() - start}
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'candidate_pools.json', pools)
    write_json(DEST / 'predicted_probe_outputs.json', predicted)
    write_json(DEST / 'frozen_records.json', records)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', **manifest}, indent=2))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('results already exist')
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == manifest['model_sha256']
    assert hashlib.sha256((ROOT / 'ast_probe_sensor_transfer.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    assert hashlib.sha256((ROOT / 'ast_probe_sensor_development.py').read_bytes()).hexdigest() == manifest['policy_sha256']
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    predicted = json.loads((DEST / 'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    records = json.loads((DEST / 'frozen_records.json').read_text(encoding='utf-8'))
    outcomes = []
    for task, record in zip(tasks, records):
        key = task['id']; rows = pools[key]; matrix = predicted[key]
        assert key == record['id'] and digest(rows) == record['pool_sha256']
        assert len(matrix) == len(rows)
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
        order = record['order']; scores = record['scores']
        selected = {'baseline': bool(labels[order[0]])}; query_indices = {}
        for mode in MODES:
            remaining = set(range(len(rows))); used = []
            for n in (1, 2):
                j = (record['first_probe'][mode] if n == 1 else
                     choose_probe(key, matrix, order, scores, remaining, used, mode))
                used.append(j)
                true_output = task['hidden'][j][1]
                matched = {i for i in remaining if matrix[i][j] == true_output}
                if matched:
                    remaining = matched
                index = next((i for i in order if i in remaining), order[0])
                selected[f'{mode}_{n}'] = bool(labels[index])
            query_indices[mode] = used
        outcomes.append({'id': key, 'seed': task['seed'], 'stream': task['stream'],
                         'reachable': any(labels), 'correct': selected,
                         'query_indices': query_indices})
    names = tuple(outcomes[0]['correct'])
    def agg(group):
        return {'tasks': len(group), 'reachable': sum(r['reachable'] for r in group),
                'correct': {name: sum(r['correct'][name] for r in group) for name in names}}
    summary = {'scope': 'fresh matched-query AST evaluator sensor transfer',
               'overall': agg(outcomes),
               'by_stream': {stream: agg([r for r in outcomes if r['stream'] == stream])
                             for stream in ('mixed', 'ast_only')},
               'by_bank': [{'seed': seed, 'stream': 'mixed' if seed in MIXED_SEEDS else 'ast_only',
                            **agg([r for r in outcomes if r['seed'] == seed])}
                           for seed in (*MIXED_SEEDS, *AST_SEEDS)],
               'top20_minus_minimax_one_by_bank': [
                   sum(r['correct']['top20_entropy_1'] - r['correct']['minimax_1']
                       for r in outcomes if r['seed'] == seed)
                   for seed in (*MIXED_SEEDS, *AST_SEEDS)]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
