"""Incremental AST feedback edit; source, freeze, and score are separate stages."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from stitch_ten import source_candidates
from seed_casebanks import random_bank


SOURCE_RUN = ROOT / 'runs/temperature-withheld-families-20260917'
MODEL_OUT = ROOT / 'analysis/ast-feedback-model.json'
DEST = ROOT / 'runs/ast-feedback-transfer-20260917'
SEEDS = tuple(range(902288, 902294))
PER_BANK = 8
CAP = 512


def generate(task):
    public = {'id': task['id'], 'visible': task['visible']}
    out = {}
    elapsed = {}
    for cap in (128, CAP):
        start = time.perf_counter()
        unique = {}
        for arm in ('v67', 'v73'):
            for row in source_candidates(public, arm, {}, cap):
                unique.setdefault(row['program'], row)
        out[str(cap)] = list(unique.values())
        elapsed[str(cap)] = time.perf_counter() - start
    return task['id'], out, elapsed


def pools_for(tasks):
    with ProcessPoolExecutor(max_workers=8) as executor:
        items = list(executor.map(generate, tasks))
    return ({key: rows for key, rows, _ in items},
            {key: elapsed for key, _, elapsed in items})


def model_inputs():
    import numpy as np
    import torch
    from listwise_evaluator_development import Ranker
    raw = json.loads(MODEL_OUT.read_text(encoding='utf-8'))
    model = Ranker(32)
    model.load_state_dict({key: torch.tensor(value, dtype=torch.float32)
                           for key, value in raw['weights'].items()})
    model.eval()
    return model, np.asarray(raw['mean'], dtype=np.float32), np.asarray(raw['scale'], dtype=np.float32)


def features(task, rows):
    import seed_growth
    from mixed_probe_diagnostic import bool_safe_structure
    seed_growth.structure = bool_safe_structure
    return seed_growth.representation({'id': task['id'], 'visible': task['visible']}, rows)['structural']


def select_model(task, rows, data):
    import numpy as np
    import torch
    from mixed_evaluator_transfer import choose
    model, mean, scale = data
    x = np.asarray(features(task, rows), dtype=np.float32)
    with torch.no_grad():
        scores = model(torch.from_numpy((x - mean) / scale)).numpy()
    return choose(scores, rows)


def source():
    if MODEL_OUT.exists():
        raise RuntimeError('source model already exists')
    tasks = [task for task in json.loads((SOURCE_RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
             if task['family'] == 'ast_transition']
    generated, times = pools_for(tasks)
    import numpy as np
    import torch
    from listwise_evaluator_development import Ranker
    from temperature_withheld_families import inputs
    parent_raw, mean, scale, parents, _ = inputs()
    parent = parents['0.25']
    rows = []
    for task in tasks:
        candidates = generated[task['id']][str(CAP)]
        x = np.asarray(features(task, candidates), dtype=np.float32)
        y = np.asarray([bool(evaluate_program(item['program'], task['hidden'][8:]))
                        for item in candidates], dtype=bool)
        rows.append((task, candidates, x, y))
    torch.manual_seed(902670)
    child = Ranker(32)
    child.load_state_dict(parent.state_dict())
    tx = [torch.from_numpy((x - mean) / scale) for _, _, x, _ in rows]
    ty = [torch.from_numpy(y) for _, _, _, y in rows]
    optimizer = torch.optim.AdamW(child.parameters(), lr=.0003, weight_decay=.001)
    for _ in range(60):
        child.train(); optimizer.zero_grad()
        losses = []
        for x, y in zip(tx, ty):
            if not bool(y.any()) or bool(y.all()):
                continue
            logits = child(x) / .25
            losses.append(.25 * (torch.logsumexp(logits, 0) - torch.logsumexp(logits[y], 0)))
        torch.stack(losses).mean().backward()
        optimizer.step()
    child.eval()
    from mixed_evaluator_transfer import choose
    prior_correct = 0; updated_correct = 0
    with torch.no_grad():
        for (_, candidates, _, y), x in zip(rows, tx):
            prior_correct += bool(y[choose(parent(x).numpy(), candidates)])
            updated_correct += bool(y[choose(child(x).numpy(), candidates)])
    result = {'scope': 'feedback edit trained on previously inspected AST tasks',
              'source_tasks': len(tasks), 'source_labels': sum(len(y) for _, _, _, y in rows),
              'source_reachable': sum(bool(y.any()) for _, _, _, y in rows),
              'source_parent_correct': prior_correct, 'source_updated_correct': updated_correct,
              'training_epochs': 60, 'learning_rate': .0003, 'temperature': .25,
              'training_seed': 902670, 'cap_per_source': CAP,
              'parent_sha256': hashlib.sha256(parent_raw['model']).hexdigest(),
              'generation_seconds': sum(sum(t.values()) for t in times.values()),
              'mean': mean.tolist(), 'scale': scale.tolist(),
              'weights': {key: value.detach().numpy().tolist()
                          for key, value in child.state_dict().items()}}
    write_json(MODEL_OUT, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('mean', 'scale', 'weights')}, indent=2))


def prepare():
    if DEST.exists():
        raise RuntimeError('fresh transfer directory already exists')
    tasks = [{**task, 'seed': seed} for seed in SEEDS
             for task in random_bank(seed, PER_BANK, ('ast_transition',), visible=1, hidden=23)]
    start = time.perf_counter()
    generated, times = pools_for(tasks)
    from temperature_withheld_families import inputs, decision
    parent_data = inputs()
    child_data = model_inputs()
    choices = []
    for task in tasks:
        pools = generated[task['id']]
        old, wide = pools['128'], pools[str(CAP)]
        choices.append({'id': task['id'], 'seed': task['seed'],
                        'pool_sha256': {key: digest(value) for key, value in pools.items()},
                        'old': decision(task, old, parent_data)['selected'],
                        'wide': decision(task, wide, parent_data)['selected'],
                        'updated': select_model(task, wide, child_data)})
    manifest = {'protocol': 'EXPERIMENT-ast-evaluator-feedback.md',
                'seeds': SEEDS, 'per_bank': PER_BANK, 'cap_per_source': CAP,
                'model_sha256': hashlib.sha256(MODEL_OUT.read_bytes()).hexdigest(),
                'runner_sha256': hashlib.sha256((ROOT / 'ast_evaluator_feedback.py').read_bytes()).hexdigest(),
                'preparation_wall_seconds': time.perf_counter() - start,
                'generation_seconds': sum(sum(t.values()) for t in times.values())}
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'candidate_pools.json', generated)
    write_json(DEST / 'frozen_choices.json', choices)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', 'tasks': len(tasks),
                      'old_candidates': sum(len(v['128']) for v in generated.values()),
                      'wide_candidates': sum(len(v[str(CAP)]) for v in generated.values()),
                      **manifest}, indent=2))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('results already exist')
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(MODEL_OUT.read_bytes()).hexdigest() == manifest['model_sha256']
    assert hashlib.sha256((ROOT / 'ast_evaluator_feedback.py').read_bytes()).hexdigest() == manifest['runner_sha256']
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    choices = json.loads((DEST / 'frozen_choices.json').read_text(encoding='utf-8'))
    outcomes = []
    for task, choice in zip(tasks, choices):
        assert task['id'] == choice['id']
        labels = {}
        for cap in ('128', str(CAP)):
            rows = pools[task['id']][cap]
            assert digest(rows) == choice['pool_sha256'][cap]
            labels[cap] = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
        outcomes.append({'id': task['id'], 'seed': task['seed'],
                         'old_reachable': any(labels['128']),
                         'wide_reachable': any(labels[str(CAP)]),
                         'old': {name: bool(labels['128'][i]) for name, i in choice['old'].items()},
                         'wide': {name: bool(labels[str(CAP)][i]) for name, i in choice['wide'].items()},
                         'updated': bool(labels[str(CAP)][choice['updated']])})
    def agg(group):
        return {'tasks': len(group), 'old_reachable': sum(r['old_reachable'] for r in group),
                'wide_reachable': sum(r['wide_reachable'] for r in group),
                'old_temp_0.25': sum(r['old']['temp_0.25'] for r in group),
                'wide_temp_0.25': sum(r['wide']['temp_0.25'] for r in group),
                'updated': sum(r['updated'] for r in group),
                'wide_temp_0.5': sum(r['wide']['temp_0.5'] for r in group),
                'wide_temp_1.0': sum(r['wide']['temp_1.0'] for r in group),
                'wide_E192': sum(r['wide']['E192'] for r in group)}
    summary = {'scope': 'fresh AST instance transfer, trained feedback edit',
               'overall': agg(outcomes),
               'by_bank': [{'seed': seed, **agg([r for r in outcomes if r['seed'] == seed])}
                           for seed in SEEDS],
               'updated_minus_parent_by_bank': [
                   sum(r['updated'] - r['wide']['temp_0.25'] for r in outcomes if r['seed'] == seed)
                   for seed in SEEDS]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'source': source, 'prepare': prepare, 'score': score}[sys.argv[1]]()
