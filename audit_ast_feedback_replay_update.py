"""Replay updated AST evaluator's frozen two-stream transfer."""
from __future__ import annotations

import hashlib
import json

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from ast_feedback_replay_update import (DEST, OLD_MODEL, NEW_MODEL, target_tasks,
                                        pools_for, updated_model, select)


def main():
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    results = json.loads((DEST / 'results.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(OLD_MODEL.read_bytes()).hexdigest() == manifest['old_model_sha256']
    assert hashlib.sha256(NEW_MODEL.read_bytes()).hexdigest() == manifest['new_model_sha256']
    assert hashlib.sha256((ROOT / 'ast_feedback_replay_update.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    assert target_tasks() == tasks
    regenerated, _ = pools_for(tasks)
    assert regenerated == pools
    from temperature_withheld_families import inputs
    from ast_evaluator_feedback import model_inputs
    parent = inputs()
    data = {'parent': (parent[3]['0.25'], parent[1], parent[2]),
            'specialist_1': model_inputs(), 'specialist_2': updated_model()}
    rebuilt = []
    checked = 0
    for task, record in zip(tasks, choices):
        rows = pools[task['id']]
        assert task['id'] == record['id'] and digest(rows) == record['pool_sha256']
        assert select(task, rows, data) == record['selected']
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
        checked += len(labels)
        rebuilt.append({'id': task['id'], 'seed': task['seed'], 'stream': task['stream'],
                        'reachable': any(labels),
                        'correct': {name: bool(labels[index])
                                    for name, index in record['selected'].items()}})
    assert rebuilt == results['tasks']
    audit = {'passed': True, 'tasks': len(tasks), 'candidate_labels_rechecked': checked,
             'model_choice_sets_rechecked': len(tasks),
             'new_model_sha256': manifest['new_model_sha256']}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
