"""Replay the frozen AST feedback transfer from public tasks through final labels."""
from __future__ import annotations

import hashlib
import json

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from ast_evaluator_feedback import DEST, MODEL_OUT, SEEDS, PER_BANK, CAP, pools_for, model_inputs, select_model


def main():
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    results = json.loads((DEST / 'results.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(MODEL_OUT.read_bytes()).hexdigest() == manifest['model_sha256']
    assert hashlib.sha256((ROOT / 'ast_evaluator_feedback.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    rebuilt = [{**task, 'seed': seed} for seed in SEEDS
               for task in random_bank(seed, PER_BANK, ('ast_transition',), visible=1, hidden=23)]
    assert rebuilt == tasks
    regenerated, _ = pools_for(tasks)
    for task in tasks:
        assert regenerated[task['id']] == pools[task['id']]
    from temperature_withheld_families import inputs, decision
    parent = inputs(); child = model_inputs()
    rebuilt_results = []
    checked = 0
    for task, choice in zip(tasks, choices):
        assert task['id'] == choice['id']
        available = pools[task['id']]
        old, wide = available['128'], available[str(CAP)]
        assert {key: digest(value) for key, value in available.items()} == choice['pool_sha256']
        assert decision(task, old, parent)['selected'] == choice['old']
        assert decision(task, wide, parent)['selected'] == choice['wide']
        assert select_model(task, wide, child) == choice['updated']
        labels = {key: [bool(evaluate_program(row['program'], task['hidden'][8:]))
                        for row in value] for key, value in available.items()}
        checked += sum(len(v) for v in available.values())
        rebuilt_results.append({'id': task['id'], 'seed': task['seed'],
                                'old_reachable': any(labels['128']),
                                'wide_reachable': any(labels[str(CAP)]),
                                'old': {name: bool(labels['128'][i]) for name, i in choice['old'].items()},
                                'wide': {name: bool(labels[str(CAP)][i]) for name, i in choice['wide'].items()},
                                'updated': bool(labels[str(CAP)][choice['updated']])})
    assert rebuilt_results == results['tasks']
    audit = {'passed': True, 'tasks': len(tasks), 'candidate_labels_rechecked': checked,
             'choices_rechecked': len(tasks) * (len(choices[0]['old']) + len(choices[0]['wide']) + 1),
             'model_sha256': manifest['model_sha256']}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
