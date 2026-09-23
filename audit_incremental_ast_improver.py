"""Independent reconstruction of frozen AST parent/child allocation transfer."""
from __future__ import annotations

import json
import hashlib
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import pools_for, updated_model
from ast_probe_sensor_development import choose_probe
from ast_probe_sensor_transfer import predicted_outputs, rank
from incremental_ast_improver import (DEST, QUERY, MIXED, RANKER, SOURCE, PARENTS,
    FIXED, ADMISSION_MIXED, ADMISSION_AST, TRANSFER_MIXED, TRANSFER_AST,
    task_banks, source_tables, train, join, data_rows, serialized, unserialize,
    make_allocations, sha, summarize)


def checked_stage(stage, mixed, ast, models):
    directory = DEST/stage
    manifest = json.loads((directory/'manifest.json').read_text())
    tasks = json.loads((directory/'sealed_bank.json').read_text())
    pools = json.loads((directory/'candidate_pools.json').read_text())
    predicted = json.loads((directory/'predicted_probe_outputs.json').read_text())
    records = json.loads((directory/'frozen_records.json').read_text())
    allocations = json.loads((directory/'frozen_allocations.json').read_text())
    results = json.loads((directory/'results.json').read_text())
    assert tasks == task_banks(mixed, ast)
    assert manifest['runner_sha256'] == sha(ROOT/'incremental_ast_improver.py')
    assert manifest['ranker_sha256'] == sha(RANKER)
    assert manifest['sensor_sha256'] == sha(ROOT/'ast_probe_sensor_development.py')
    assert manifest['model_sha256'] == sha(DEST/('parent_models.json' if stage == 'admission'
                                               else 'child_models.json'))
    regenerated, _ = pools_for(tasks)
    assert regenerated == pools
    public = [({'id': t['id'], 'probe_inputs': [v for v, _ in t['hidden'][:8]]},
               pools[t['id']]) for t in tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        assert dict(executor.map(predicted_outputs, public)) == predicted
    ranker = updated_model()
    for task, record in zip(tasks, records):
        key = task['id']; rows = pools[key]
        assert key == record['id'] and digest(rows) == record['pool_sha256']
        scores, order = rank(task, rows, ranker)
        assert order == record['order']
        assert np.allclose(scores, record['scores'], atol=1e-6)
        assert choose_probe(key, predicted[key], order, scores,
                            set(range(len(rows))), [], 'top20_entropy') == record['first_probe']
    assert make_allocations(tasks, records, predicted, models) == allocations
    reconstructed = []; checked = 0
    for task, record in zip(tasks, records):
        key = task['id']; rows = pools[key]; matrix = predicted[key]
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
        checked += len(labels)
        order = record['order']; scores = record['scores']
        correct = [bool(labels[order[0]])]; used = []; remaining = set(range(len(rows)))
        for step in (1, 2):
            j = record['first_probe'] if step == 1 else choose_probe(
                key, matrix, order, scores, remaining, used, 'top20_entropy')
            used.append(j)
            matching = {i for i in remaining if matrix[i][j] == task['hidden'][j][1]}
            if matching: remaining = matching
            chosen = next((i for i in order if i in remaining), order[0])
            correct.append(bool(labels[chosen]))
        reconstructed.append({'id': key, 'seed': task['seed'], 'stream': task['stream'],
                              'reachable': any(labels), 'correct_by_calls': correct,
                              'query_indices': used})
    assert reconstructed == results['tasks']
    by_id = {row['id']: row for row in reconstructed}
    for bank in results['summary']['by_bank']:
        allocation = allocations[str(bank['seed'])]
        for name in (*PARENTS, *FIXED):
            mapping = allocation[name]
            assert sum(mapping.values()) == 8
            assert bank['correct'][name] == sum(
                by_id[key]['correct_by_calls'][calls] for key, calls in mapping.items())
    return {'tasks': len(tasks), 'candidate_labels_rechecked': checked,
            'predicted_output_cells_rechecked': sum(len(rows)*8 for rows in predicted.values()),
            'banks_rechecked': len(mixed)+len(ast)}


def main():
    assert not (DEST/'audit.json').exists()
    source = json.loads((DEST/'source_manifest.json').read_text())
    for path, expected in source['source_hashes'].items():
        assert sha(ROOT/path) == expected
    tables = source_tables()
    parent = {name: train(tables[name]) for name in PARENTS}
    frozen_parent = json.loads((DEST/'parent_models.json').read_text())
    assert {name: serialized(model) for name, model in parent.items()} == frozen_parent
    admission = checked_stage('admission', ADMISSION_MIXED, ADMISSION_AST, parent)
    tasks = json.loads((DEST/'admission/sealed_bank.json').read_text())
    records = json.loads((DEST/'admission/frozen_records.json').read_text())
    predicted = json.loads((DEST/'admission/predicted_probe_outputs.json').read_text())
    outcomes = json.loads((DEST/'admission/results.json').read_text())['tasks']
    shared = data_rows(tasks, records, predicted, outcomes, 'query')
    children = {name: train(join(tables[name], shared)) for name in PARENTS}
    frozen_children = json.loads((DEST/'child_models.json').read_text())
    assert {name: serialized(model) for name, model in children.items()} == frozen_children
    child_training = json.loads((DEST/'child_training.json').read_text())
    assert child_training['admission_task_ids'] == shared['ids']
    assert child_training['admission_results_sha256'] == sha(DEST/'admission/results.json')
    transfer = checked_stage('transfer', TRANSFER_MIXED, TRANSFER_AST, children)
    assert summarize() == json.loads((DEST/'summary.json').read_text())
    result = {'passed': True, 'source_files_rechecked': len(source['source_hashes']),
              'parent_models_retrained': len(parent), 'child_models_retrained': len(children),
              'admission': admission, 'transfer': transfer}
    write_json(DEST/'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
