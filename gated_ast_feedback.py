"""Fresh mixed-bank integration of retained evaluator and AST specialist."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from stitch_ten import source_candidates


DEST = ROOT / 'runs/gated-ast-feedback-20260917'
MODEL = ROOT / 'analysis/ast-feedback-model.json'
PARENT = ROOT / 'analysis/temperature-ranker-development.json'
SEEDS = tuple(range(902294, 902300))
PER_BANK = 48
BLOCK_AST = 0x800
SOURCE_MAP = {'transform_transition': ('v65', 'v67'),
              'ast_transition': ('v67', 'v73'),
              'novel_operator_transition': ('v67', 'v69'),
              'stack_transition': ('v67', 'v70'),
              'mutation_transition': ('v70', 'v72'),
              'self_edit_transition': ('v70', 'v73')}
FIXED = {0x700: 'temp_0.5', 0x800: 'temp_0.25', 0x900: 'temp_0.25',
         0xA00: 'temp_0.25', 0xC00: 'temp_0.25', 0xD00: 'temp_0.5'}


def public_block(task):
    chars = [ord(char) for text, _ in task['visible'] for char in text]
    return (min(chars) // 256) * 256 if chars else -1


def generate(task):
    public = {'id': task['id'], 'visible': task['visible']}
    arms = SOURCE_MAP[task['family']]
    start = time.perf_counter()
    base = {}
    for arm in arms:
        for row in source_candidates(public, arm, {}, 128):
            base.setdefault(row['program'], row)
    wide = None
    if task['family'] == 'ast_transition':
        wide = {}
        for arm in arms:
            for row in source_candidates(public, arm, {}, 512):
                wide.setdefault(row['program'], row)
        wide = list(wide.values())
    return task['id'], list(base.values()), wide, time.perf_counter() - start


def pools_for(tasks):
    with ProcessPoolExecutor(max_workers=8) as executor:
        items = list(executor.map(generate, tasks))
    return ({key: base for key, base, _, _ in items},
            {key: wide for key, _, wide, _ in items if wide is not None},
            {key: seconds for key, _, _, seconds in items})


def models():
    from temperature_withheld_families import inputs
    from ast_evaluator_feedback import model_inputs
    return inputs(), model_inputs()


def select_all(task, rows, data):
    import numpy as np
    import torch
    import seed_growth
    from mixed_probe_diagnostic import bool_safe_structure
    from mixed_evaluator_transfer import choose
    seed_growth.structure = bool_safe_structure
    parent, child = data
    _, mean, scale, parents, _ = parent
    specialist, child_mean, child_scale = child
    public = {'id': task['id'], 'visible': task['visible']}
    x = np.asarray(seed_growth.representation(public, rows)['structural'], dtype=np.float32)
    result = {}
    with torch.no_grad():
        for temperature, model in parents.items():
            logits = model(torch.from_numpy((x - mean) / scale)).numpy()
            result[f'temp_{temperature}'] = choose(logits, rows)
        logits = specialist(torch.from_numpy((x - child_mean) / child_scale)).numpy()
        result['ast_specialist'] = choose(logits, rows)
    return result


def prepare():
    if DEST.exists():
        raise RuntimeError('fresh run directory already exists')
    tasks = [{**task, 'seed': seed} for seed in SEEDS
             for task in random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]
    start = time.perf_counter()
    base, ast_wide, seconds = pools_for(tasks)
    data = models()
    choices = []
    for task in tasks:
        key = task['id']
        block = public_block(task)
        assert block in FIXED
        original = base[key]
        wide = ast_wide.get(key, original)
        assert original and wide
        base_choice = select_all(task, original, data)['temp_0.25']
        selected = select_all(task, wide, data)
        choices.append({'id': key, 'seed': task['seed'], 'public_block': block,
                        'base_sha256': digest(original), 'wide_sha256': digest(wide),
                        'base_parent': base_choice, 'wide_choices': selected,
                        'fixed_temperature': FIXED[block]})
    manifest = {'protocol': 'EXPERIMENT-gated-ast-feedback.md',
                'seeds': SEEDS, 'per_bank': PER_BANK, 'ast_block': BLOCK_AST,
                'fixed_block_temperature': FIXED,
                'model_sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                'parent_sha256': hashlib.sha256(PARENT.read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256((ROOT / 'gated_ast_feedback.py').read_bytes()).hexdigest(),
                'preparation_wall_seconds': time.perf_counter() - start,
                'generation_seconds': sum(seconds.values()),
                'base_candidates': sum(len(rows) for rows in base.values()),
                'ast_wide_candidates': sum(len(rows) for rows in ast_wide.values())}
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
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == manifest['model_sha256']
    assert hashlib.sha256(PARENT.read_bytes()).hexdigest() == manifest['parent_sha256']
    assert hashlib.sha256((ROOT / 'gated_ast_feedback.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    base = json.loads((DEST / 'base_pools.json').read_text(encoding='utf-8'))
    ast_wide = json.loads((DEST / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    outcomes = []
    for task, choice in zip(tasks, choices):
        key = task['id']
        original = base[key]
        wide = ast_wide.get(key, original)
        assert key == choice['id'] and public_block(task) == choice['public_block']
        assert digest(original) == choice['base_sha256'] and digest(wide) == choice['wide_sha256']
        base_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in original]
        wide_labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in wide]
        picked = choice['wide_choices']
        updated = choice['public_block'] == BLOCK_AST
        fixed = choice['fixed_temperature']
        outcomes.append({'id': key, 'seed': task['seed'], 'family': task['family'],
                         'base_reachable': any(base_labels), 'wide_reachable': any(wide_labels),
                         'base_parent': bool(base_labels[choice['base_parent']]),
                         'wide_parent': bool(wide_labels[picked['temp_0.25']]),
                         'global_specialist': bool(wide_labels[picked['ast_specialist']]),
                         'gated_specialist': bool(wide_labels[picked['ast_specialist' if updated else 'temp_0.25']]),
                         'fixed_map': bool(wide_labels[picked[fixed]]),
                         'gated_fixed_map': bool(wide_labels[picked['ast_specialist' if updated else fixed]])})
    fields = ('base_parent', 'wide_parent', 'global_specialist', 'gated_specialist',
              'fixed_map', 'gated_fixed_map')
    def aggregate(rows):
        return {'tasks': len(rows), 'base_reachable': sum(r['base_reachable'] for r in rows),
                'wide_reachable': sum(r['wide_reachable'] for r in rows),
                **{field: sum(r[field] for r in rows) for field in fields}}
    summary = {'scope': 'fresh mixed-bank gated AST specialist integration',
               'overall': aggregate(outcomes),
               'by_family': {family: aggregate([r for r in outcomes if r['family'] == family])
                             for family in FAMILIES},
               'by_bank': [{'seed': seed, **aggregate([r for r in outcomes if r['seed'] == seed])}
                           for seed in SEEDS],
               'gated_minus_parent_by_bank': [sum(r['gated_specialist'] - r['wide_parent']
                                                  for r in outcomes if r['seed'] == seed)
                                              for seed in SEEDS],
               'gated_fixed_minus_fixed_by_bank': [sum(r['gated_fixed_map'] - r['fixed_map']
                                                       for r in outcomes if r['seed'] == seed)
                                                   for seed in SEEDS]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
