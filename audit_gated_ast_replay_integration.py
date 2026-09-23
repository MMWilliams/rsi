"""Regenerate and replay the full mixed-bank AST replay integration."""
from __future__ import annotations

import hashlib
import json

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from gated_ast_feedback import pools_for, public_block, FIXED, BLOCK_AST
from gated_ast_replay_integration import (DEST, PARENT, FIRST, SECOND, tasks_for,
                                          models, select)


def main():
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    base = json.loads((DEST / 'base_pools.json').read_text(encoding='utf-8'))
    ast_wide = json.loads((DEST / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    results = json.loads((DEST / 'results.json').read_text(encoding='utf-8'))
    assert manifest['runner_sha256'] == hashlib.sha256((ROOT / 'gated_ast_replay_integration.py').read_bytes()).hexdigest()
    assert manifest['model_sha256'] == {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                         for name, path in [('parent', PARENT), ('first', FIRST), ('second', SECOND)]}
    assert tasks_for() == tasks
    new_base, new_wide, _ = pools_for(tasks)
    assert new_base == base and new_wide == ast_wide
    data = models()
    checked = 0; outcomes = []
    for task, choice in zip(tasks, choices):
        key = task['id']; old = base[key]; wide = ast_wide.get(key, old)
        assert key == choice['id'] and public_block(task) == choice['public_block']
        assert choice['fixed_temperature'] == FIXED[choice['public_block']]
        assert digest(old) == choice['base_sha256'] and digest(wide) == choice['wide_sha256']
        assert select(task, old, data)['temp_0.25'] == choice['base_parent']
        assert select(task, wide, data) == choice['wide_choices']
        old_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in old]
        wide_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in wide]
        checked += len(old_labels) + len(wide_labels)
        selected = choice['wide_choices']; ast = choice['public_block'] == BLOCK_AST
        fixed = choice['fixed_temperature']
        outcomes.append({'id': key, 'seed': task['seed'], 'family': task['family'],
                         'base_reachable': any(old_labels), 'wide_reachable': any(wide_labels),
                         'base_parent': bool(old_labels[choice['base_parent']]),
                         'wide_parent': bool(wide_labels[selected['temp_0.25']]),
                         'global_second': bool(wide_labels[selected['specialist_2']]),
                         'gate_first': bool(wide_labels[selected['specialist_1' if ast else 'temp_0.25']]),
                         'gate_second': bool(wide_labels[selected['specialist_2' if ast else 'temp_0.25']]),
                         'fixed_map': bool(wide_labels[selected[fixed]]),
                         'fixed_plus_second': bool(wide_labels[selected['specialist_2' if ast else fixed]])})
    assert outcomes == results['tasks']
    audit = {'passed': True, 'tasks': len(tasks), 'candidate_labels_rechecked': checked,
             'base_and_wide_choice_sets_rechecked': len(tasks) * 2,
             'model_sha256': manifest['model_sha256']}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
