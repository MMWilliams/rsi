"""Replay verified AST feedback, then freeze two-stream transfer choices."""
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


FIRST = ROOT / 'runs/ast-feedback-transfer-20260917'
SECOND = ROOT / 'runs/gated-ast-feedback-20260917'
OLD_MODEL = ROOT / 'analysis/ast-feedback-model.json'
NEW_MODEL = ROOT / 'analysis/ast-feedback-replay-model.json'
DEST = ROOT / 'runs/ast-feedback-replay-transfer-20260917'
MIXED_SEEDS = tuple(range(902300, 902306))
AST_SEEDS = tuple(range(902306, 902312))
CAP = 512


def generate(task):
    public = {'id': task['id'], 'visible': task['visible']}
    start = time.perf_counter()
    unique = {}
    for arm in ('v67', 'v73'):
        for row in source_candidates(public, arm, {}, CAP):
            unique.setdefault(row['program'], row)
    return task['id'], list(unique.values()), time.perf_counter() - start


def pools_for(tasks):
    with ProcessPoolExecutor(max_workers=8) as executor:
        items = list(executor.map(generate, tasks))
    return ({key: rows for key, rows, _ in items},
            {key: seconds for key, _, seconds in items})


def source_rows():
    first_tasks = json.loads((FIRST / 'sealed_bank.json').read_text(encoding='utf-8'))
    first_pools = json.loads((FIRST / 'candidate_pools.json').read_text(encoding='utf-8'))
    second_tasks = [task for task in json.loads((SECOND / 'sealed_bank.json').read_text(encoding='utf-8'))
                    if task['family'] == 'ast_transition']
    second_pools = json.loads((SECOND / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    return ([(task, first_pools[task['id']][str(CAP)], 'ast_only') for task in first_tasks] +
            [(task, second_pools[task['id']], 'mixed') for task in second_tasks])


def updated_model():
    import numpy as np
    import torch
    from listwise_evaluator_development import Ranker
    raw = json.loads(NEW_MODEL.read_text(encoding='utf-8'))
    model = Ranker(32)
    model.load_state_dict({key: torch.tensor(value, dtype=torch.float32)
                           for key, value in raw['weights'].items()})
    model.eval()
    return model, np.asarray(raw['mean'], dtype=np.float32), np.asarray(raw['scale'], dtype=np.float32)


def select(task, rows, data):
    import numpy as np
    import torch
    from mixed_evaluator_transfer import choose
    from ast_evaluator_feedback import features
    x = np.asarray(features(task, rows), dtype=np.float32)
    result = {}
    with torch.no_grad():
        for name, (model, mean, scale) in data.items():
            logits = model(torch.from_numpy((x - mean) / scale)).numpy()
            result[name] = choose(logits, rows)
    return result


def train():
    if NEW_MODEL.exists():
        raise RuntimeError('replay model already exists')
    import numpy as np
    import torch
    from ast_evaluator_feedback import features, model_inputs
    from mixed_evaluator_transfer import choose
    from temperature_withheld_families import inputs
    from listwise_evaluator_development import Ranker
    old, mean, scale = model_inputs()
    parent_data = inputs()
    source = source_rows()
    records = []
    for task, rows, stream in source:
        x = np.asarray(features(task, rows), dtype=np.float32)
        y = np.asarray([bool(evaluate_program(row['program'], task['hidden'][8:]))
                        for row in rows], dtype=bool)
        records.append((task, rows, stream, torch.from_numpy((x - mean) / scale), torch.from_numpy(y)))
    torch.manual_seed(902671)
    model = Ranker(32)
    model.load_state_dict(old.state_dict())
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0001, weight_decay=.001)
    start = time.perf_counter()
    for _ in range(40):
        model.train(); optimizer.zero_grad()
        losses = []
        for _, _, _, x, y in records:
            if not bool(y.any()) or bool(y.all()):
                continue
            logits = model(x) / .25
            losses.append(.25 * (torch.logsumexp(logits, 0) - torch.logsumexp(logits[y], 0)))
        torch.stack(losses).mean().backward()
        optimizer.step()
    model.eval()
    old_correct = {'ast_only': 0, 'mixed': 0}
    new_correct = {'ast_only': 0, 'mixed': 0}
    with torch.no_grad():
        for _, rows, stream, x, y in records:
            old_correct[stream] += bool(y[choose(old(x).numpy(), rows)])
            new_correct[stream] += bool(y[choose(model(x).numpy(), rows)])
    result = {'scope': 'incremental replay on two inspected AST feedback streams',
              'source_tasks': len(source), 'source_candidate_labels': sum(len(y) for *_, y in records),
              'source_reachable': sum(bool(y.any()) for *_, y in records),
              'old_source_correct': old_correct, 'new_source_correct': new_correct,
              'epochs': 40, 'learning_rate': .0001, 'temperature': .25,
              'training_seed': 902671, 'training_wall_seconds': time.perf_counter() - start,
              'old_model_sha256': hashlib.sha256(OLD_MODEL.read_bytes()).hexdigest(),
              'first_outcomes_sha256': hashlib.sha256((FIRST / 'results.json').read_bytes()).hexdigest(),
              'second_outcomes_sha256': hashlib.sha256((SECOND / 'results.json').read_bytes()).hexdigest(),
              'mean': mean.tolist(), 'scale': scale.tolist(),
              'weights': {key: value.detach().numpy().tolist()
                          for key, value in model.state_dict().items()}}
    write_json(NEW_MODEL, result)
    print(json.dumps({key: value for key, value in result.items() if key not in ('mean', 'scale', 'weights')}, indent=2))


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


def prepare():
    if DEST.exists():
        raise RuntimeError('fresh transfer directory already exists')
    tasks = target_tasks()
    start = time.perf_counter()
    pools, times = pools_for(tasks)
    from temperature_withheld_families import inputs
    from ast_evaluator_feedback import model_inputs
    parent = inputs()
    data = {'parent': (parent[3]['0.25'], parent[1], parent[2]),
            'specialist_1': model_inputs(), 'specialist_2': updated_model()}
    choices = []
    for task in tasks:
        rows = pools[task['id']]
        assert rows
        choices.append({'id': task['id'], 'seed': task['seed'], 'stream': task['stream'],
                        'pool_sha256': digest(rows), 'selected': select(task, rows, data)})
    manifest = {'protocol': 'EXPERIMENT-ast-feedback-replay-update.md',
                'mixed_seeds': MIXED_SEEDS, 'ast_only_seeds': AST_SEEDS,
                'tasks': len(tasks), 'cap_per_source': CAP,
                'old_model_sha256': hashlib.sha256(OLD_MODEL.read_bytes()).hexdigest(),
                'new_model_sha256': hashlib.sha256(NEW_MODEL.read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256((ROOT / 'ast_feedback_replay_update.py').read_bytes()).hexdigest(),
                'candidate_count': sum(len(rows) for rows in pools.values()),
                'generation_seconds': sum(times.values()),
                'preparation_wall_seconds': time.perf_counter() - start}
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'candidate_pools.json', pools)
    write_json(DEST / 'frozen_choices.json', choices)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', **manifest}, indent=2))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('results already exist')
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(OLD_MODEL.read_bytes()).hexdigest() == manifest['old_model_sha256']
    assert hashlib.sha256(NEW_MODEL.read_bytes()).hexdigest() == manifest['new_model_sha256']
    assert hashlib.sha256((ROOT / 'ast_feedback_replay_update.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    outcomes = []
    for task, choice in zip(tasks, choices):
        rows = pools[task['id']]
        assert task['id'] == choice['id'] and digest(rows) == choice['pool_sha256']
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
        outcomes.append({'id': task['id'], 'seed': task['seed'], 'stream': task['stream'],
                         'reachable': any(labels),
                         'correct': {name: bool(labels[index])
                                     for name, index in choice['selected'].items()}})
    names = tuple(outcomes[0]['correct'])
    def agg(rows):
        return {'tasks': len(rows), 'reachable': sum(r['reachable'] for r in rows),
                'correct': {name: sum(r['correct'][name] for r in rows) for name in names}}
    summary = {'scope': 'fresh AST-only and mixed-stream replay-update transfer',
               'overall': agg(outcomes),
               'by_stream': {stream: agg([r for r in outcomes if r['stream'] == stream])
                             for stream in ('ast_only', 'mixed')},
               'by_bank': [{'seed': seed, 'stream': 'mixed' if seed in MIXED_SEEDS else 'ast_only',
                            **agg([r for r in outcomes if r['seed'] == seed])}
                           for seed in (*MIXED_SEEDS, *AST_SEEDS)],
               'new_minus_old_by_bank': [sum(r['correct']['specialist_2'] - r['correct']['specialist_1']
                                             for r in outcomes if r['seed'] == seed)
                                         for seed in (*MIXED_SEEDS, *AST_SEEDS)]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'train': train, 'prepare': prepare, 'score': score}[sys.argv[1]]()
