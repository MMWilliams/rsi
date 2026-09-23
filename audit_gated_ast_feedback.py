"""Reconstruct fresh mixed AST integration from generated tasks to final labels."""
from __future__ import annotations

import hashlib
import json

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from gated_ast_feedback import (DEST, MODEL, PARENT, SEEDS, PER_BANK, BLOCK_AST,
                                FIXED, pools_for, models, public_block, select_all)


def main():
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    base = json.loads((DEST / 'base_pools.json').read_text(encoding='utf-8'))
    ast_wide = json.loads((DEST / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    results = json.loads((DEST / 'results.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == manifest['model_sha256']
    assert hashlib.sha256(PARENT.read_bytes()).hexdigest() == manifest['parent_sha256']
    assert hashlib.sha256((ROOT / 'gated_ast_feedback.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    recreated = [{**task, 'seed': seed} for seed in SEEDS
                 for task in random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]
    assert recreated == tasks
    regen_base, regen_wide, _ = pools_for(tasks)
    assert regen_base == base and regen_wide == ast_wide
    data = models()
    outcomes = []
    checks = 0
    for task, record in zip(tasks, choices):
        key = task['id']; old = base[key]; wide = ast_wide.get(key, old)
        assert key == record['id'] and public_block(task) == record['public_block']
        assert record['fixed_temperature'] == FIXED[record['public_block']]
        assert digest(old) == record['base_sha256'] and digest(wide) == record['wide_sha256']
        assert select_all(task, old, data)['temp_0.25'] == record['base_parent']
        assert select_all(task, wide, data) == record['wide_choices']
        old_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in old]
        wide_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in wide]
        checks += len(old_labels) + len(wide_labels)
        selected = record['wide_choices']
        on_ast = record['public_block'] == BLOCK_AST
        fixed = record['fixed_temperature']
        outcomes.append({'id': key, 'seed': task['seed'], 'family': task['family'],
                         'base_reachable': any(old_labels), 'wide_reachable': any(wide_labels),
                         'base_parent': bool(old_labels[record['base_parent']]),
                         'wide_parent': bool(wide_labels[selected['temp_0.25']]),
                         'global_specialist': bool(wide_labels[selected['ast_specialist']]),
                         'gated_specialist': bool(wide_labels[selected['ast_specialist' if on_ast else 'temp_0.25']]),
                         'fixed_map': bool(wide_labels[selected[fixed]]),
                         'gated_fixed_map': bool(wide_labels[selected['ast_specialist' if on_ast else fixed]])})
    assert outcomes == results['tasks']
    audit = {'passed': True, 'tasks': len(tasks), 'candidate_labels_rechecked': checks,
             'base_and_wide_choice_sets_rechecked': len(tasks) * 2,
             'model_sha256': manifest['model_sha256']}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
