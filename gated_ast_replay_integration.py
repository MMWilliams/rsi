"""Full six-mechanism transfer of replay-updated AST specialist."""
from __future__ import annotations

import hashlib
import json
import sys
import time

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from gated_ast_feedback import pools_for, public_block, FIXED, BLOCK_AST


DEST = ROOT / 'runs/gated-ast-replay-integration-20260917'
SEEDS = tuple(range(902312, 902318))
PER_BANK = 48
PARENT = ROOT / 'analysis/temperature-ranker-development.json'
FIRST = ROOT / 'analysis/ast-feedback-model.json'
SECOND = ROOT / 'analysis/ast-feedback-replay-model.json'


def models():
    from temperature_withheld_families import inputs
    from ast_evaluator_feedback import model_inputs
    from ast_feedback_replay_update import updated_model
    parent = inputs()
    return {'temp_0.25': (parent[3]['0.25'], parent[1], parent[2]),
            'temp_0.5': (parent[3]['0.5'], parent[1], parent[2]),
            'temp_1.0': (parent[3]['1.0'], parent[1], parent[2]),
            'specialist_1': model_inputs(),
            'specialist_2': updated_model()}


def select(task, rows, data):
    import numpy as np
    import torch
    from ast_evaluator_feedback import features
    from mixed_evaluator_transfer import choose
    x = np.asarray(features(task, rows), dtype=np.float32)
    output = {}
    with torch.no_grad():
        for name, (model, mean, scale) in data.items():
            logits = model(torch.from_numpy((x - mean) / scale)).numpy()
            output[name] = choose(logits, rows)
    return output


def tasks_for():
    return [{**task, 'seed': seed} for seed in SEEDS
            for task in random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]


def prepare():
    if DEST.exists():
        raise RuntimeError('fresh integration directory already exists')
    tasks = tasks_for()
    start = time.perf_counter()
    base, ast_wide, elapsed = pools_for(tasks)
    data = models()
    choices = []
    for task in tasks:
        key = task['id']; old = base[key]; wide = ast_wide.get(key, old)
        block = public_block(task)
        assert block in FIXED and old and wide
        choices.append({'id': key, 'seed': task['seed'], 'public_block': block,
                        'base_sha256': digest(old), 'wide_sha256': digest(wide),
                        'base_parent': select(task, old, data)['temp_0.25'],
                        'wide_choices': select(task, wide, data),
                        'fixed_temperature': FIXED[block]})
    manifest = {'protocol': 'EXPERIMENT-gated-ast-replay-integration.md',
                'seeds': SEEDS, 'per_bank': PER_BANK,
                'model_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for name, path in [('parent', PARENT), ('first', FIRST), ('second', SECOND)]},
                'runner_sha256': hashlib.sha256((ROOT / 'gated_ast_replay_integration.py').read_bytes()).hexdigest(),
                'base_candidates': sum(len(rows) for rows in base.values()),
                'ast_wide_candidates': sum(len(rows) for rows in ast_wide.values()),
                'generation_seconds': sum(elapsed.values()),
                'preparation_wall_seconds': time.perf_counter() - start}
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'base_pools.json', base)
    write_json(DEST / 'ast_wide_pools.json', ast_wide)
    write_json(DEST / 'frozen_choices.json', choices)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', **manifest}, indent=2))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('results already exist')
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['runner_sha256'] == hashlib.sha256((ROOT / 'gated_ast_replay_integration.py').read_bytes()).hexdigest()
    assert manifest['model_sha256'] == {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                         for name, path in [('parent', PARENT), ('first', FIRST), ('second', SECOND)]}
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    base = json.loads((DEST / 'base_pools.json').read_text(encoding='utf-8'))
    ast_wide = json.loads((DEST / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    outcomes = []
    for task, choice in zip(tasks, choices):
        key = task['id']; old = base[key]; wide = ast_wide.get(key, old)
        assert key == choice['id'] and public_block(task) == choice['public_block']
        assert digest(old) == choice['base_sha256'] and digest(wide) == choice['wide_sha256']
        old_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in old]
        wide_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in wide]
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
    fields = ('base_parent', 'wide_parent', 'global_second', 'gate_first',
              'gate_second', 'fixed_map', 'fixed_plus_second')
    def agg(rows):
        return {'tasks': len(rows), 'base_reachable': sum(r['base_reachable'] for r in rows),
                'wide_reachable': sum(r['wide_reachable'] for r in rows),
                **{field: sum(r[field] for r in rows) for field in fields}}
    summary = {'scope': 'fresh full mixed integration of replay AST specialist',
               'overall': agg(outcomes),
               'by_family': {family: agg([r for r in outcomes if r['family'] == family])
                             for family in FAMILIES},
               'by_bank': [{'seed': seed, **agg([r for r in outcomes if r['seed'] == seed])}
                           for seed in SEEDS],
               'fixed_plus_second_minus_fixed_by_bank': [
                   sum(r['fixed_plus_second'] - r['fixed_map'] for r in outcomes if r['seed'] == seed)
                   for seed in SEEDS],
               'gate_second_minus_gate_first_by_bank': [
                   sum(r['gate_second'] - r['gate_first'] for r in outcomes if r['seed'] == seed)
                   for seed in SEEDS]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
