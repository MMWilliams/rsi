"""Reconstruct the matched-query AST sensor study."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import pools_for, updated_model
from ast_probe_sensor_development import MODES, choose_probe
from ast_probe_sensor_transfer import (DEST, MODEL, target_tasks,
                                       predicted_outputs, rank)


def main():
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    predicted = json.loads((DEST / 'predicted_probe_outputs.json').read_text(encoding='utf-8'))
    records = json.loads((DEST / 'frozen_records.json').read_text(encoding='utf-8'))
    results = json.loads((DEST / 'results.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == manifest['model_sha256']
    assert hashlib.sha256((ROOT / 'ast_probe_sensor_transfer.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    assert hashlib.sha256((ROOT / 'ast_probe_sensor_development.py').read_bytes()).hexdigest() == manifest['policy_sha256']
    assert target_tasks() == tasks
    regenerated, _ = pools_for(tasks)
    assert regenerated == pools
    public = [({'id': task['id'], 'probe_inputs': [text for text, _ in task['hidden'][:8]]},
               pools[task['id']]) for task in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs, public)) == predicted
    model = updated_model()
    outcomes = []; checked = 0
    for task, record in zip(tasks, records):
        key = task['id']; rows = pools[key]; matrix = predicted[key]
        assert key == record['id'] and digest(rows) == record['pool_sha256']
        scores, order = rank(task, rows, model)
        assert len(scores) == len(record['scores'])
        assert all(abs(a-b) < 1e-6 for a,b in zip(scores, record['scores']))
        assert order == record['order']
        first = {mode: choose_probe(key, matrix, order, scores,
                                    set(range(len(rows))), [], mode) for mode in MODES}
        assert first == record['first_probe']
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
        checked += len(labels)
        correct = {'baseline': bool(labels[order[0]])}; query_indices = {}
        for mode in MODES:
            remaining = set(range(len(rows))); used = []
            for n in (1,2):
                j = first[mode] if n == 1 else choose_probe(key,matrix,order,scores,remaining,used,mode)
                used.append(j)
                matched = {i for i in remaining if matrix[i][j] == task['hidden'][j][1]}
                if matched: remaining = matched
                index = next((i for i in order if i in remaining),order[0])
                correct[f'{mode}_{n}'] = bool(labels[index])
            query_indices[mode] = used
        outcomes.append({'id': key, 'seed': task['seed'], 'stream': task['stream'],
                         'reachable': any(labels), 'correct': correct,
                         'query_indices': query_indices})
    assert outcomes == results['tasks']
    audit = {'passed': True, 'tasks': len(tasks), 'candidate_labels_rechecked': checked,
             'predicted_output_cells_rechecked': sum(len(v)*8 for v in predicted.values()),
             'rank_and_first_query_records_rechecked': len(records),
             'model_sha256': manifest['model_sha256']}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
