"""Frozen listwise evaluator transfer; prepare choices before scoring labels."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import torch

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import representation
from mixed_probe_diagnostic import pool, bool_safe_structure
from mixed_evaluator_transfer import choose
from context_expert_transfer import build_record, EXPERT, ROUTER, COMPONENTS, A, B, C
from listwise_evaluator_development import Ranker
import seed_growth


SOURCE = ROOT / 'analysis/listwise-evaluator-development-v2.json'
DEST = ROOT / 'runs/listwise-evaluator-transfer-20260917'
SEEDS = tuple(range(902228, 902234))
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')
PER_BANK = 32
EPOCHS = (40, 80, 120)


def load_inputs():
    paths = {'listwise': SOURCE, 'expert': EXPERT, 'router': ROUTER,
             'components': COMPONENTS}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    data = {name: json.loads(value) for name, value in raw.items()}
    variant = data['listwise']['variants']['mlp32']
    mean = np.asarray(variant['normalization_mean'], dtype=np.float32)
    scale = np.asarray(variant['normalization_scale'], dtype=np.float32)
    models = {}
    for epoch in EPOCHS:
        model = Ranker(32)
        state = {key: torch.tensor(value, dtype=torch.float32)
                 for key, value in variant['checkpoint_weights'][str(epoch)].items()}
        model.load_state_dict(state)
        model.eval()
        models[epoch] = model
    expert = data['expert']
    global_w = np.asarray(expert['global_weights'], dtype=float)
    experts = {int(key): np.asarray(value, dtype=float)
               for key, value in expert['expert_weights'].items()}
    components = {name: np.asarray(data['components']['weights'][name], dtype=float)
                  for name in (A, B, C)}
    assert np.array_equal(global_w, components[A])
    return raw, data, mean, scale, models, global_w, experts, components


def decision(task, rows, inputs):
    _, data, mean, scale, models, global_w, experts, components = inputs
    record = build_record(task, rows, global_w, experts, data['router'], components)
    if rows:
        x = np.asarray(representation({'id': task['id'], 'visible': task['visible']},
                                      rows)['structural'], dtype=np.float32)
        tx = torch.from_numpy((x - mean) / scale)
        with torch.no_grad():
            for epoch, model in models.items():
                name = f'listwise_{epoch}'
                logits = model(tx).numpy().tolist()
                record['scores'][name] = logits
                record['selected'][name] = choose(logits, rows)
    else:
        for epoch in EPOCHS:
            name = f'listwise_{epoch}'
            record['scores'][name] = []
            record['selected'][name] = None
    return record


def prepare():
    if DEST.exists():
        raise RuntimeError('transfer directory already exists')
    seed_growth.structure = bool_safe_structure
    inputs = load_inputs()
    raw = inputs[0]
    tasks = [{**task, 'seed': seed} for seed in SEEDS for task in
             random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated = list(executor.map(pool, tasks))
    pools = {key: rows for key, rows, _ in generated}
    records = [decision(task, pools[task['id']], inputs) for task in tasks]
    manifest = {'protocol': 'EXPERIMENT-listwise-evaluator-transfer.md',
                'input_sha256': {name: hashlib.sha256(value).hexdigest()
                                 for name, value in raw.items()},
                'runner_sha256': hashlib.sha256(
                    (ROOT / 'listwise_evaluator_transfer.py').read_bytes()).hexdigest(),
                'seeds': SEEDS, 'per_bank': PER_BANK,
                'preparation_wall_seconds': time.perf_counter() - start}
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'candidate_pools.json', pools)
    write_json(DEST / 'frozen_decisions.json', records)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', 'tasks': len(tasks),
                      'candidates': sum(map(len, pools.values())),
                      'preparation_wall_seconds': manifest['preparation_wall_seconds']}, indent=2))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('results already exist')
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    raw = load_inputs()[0]
    assert manifest['input_sha256'] == {name: hashlib.sha256(value).hexdigest()
                                        for name, value in raw.items()}
    assert manifest['runner_sha256'] == hashlib.sha256(
        (ROOT / 'listwise_evaluator_transfer.py').read_bytes()).hexdigest()
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    records = json.loads((DEST / 'frozen_decisions.json').read_text(encoding='utf-8'))
    assert len(tasks) == len(records) == len(SEEDS) * PER_BANK
    outcomes = []
    for task, record in zip(tasks, records):
        rows = pools[task['id']]
        assert task['id'] == record['id'] and digest(rows) == record['pool_sha256']
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in rows]
        correct = {name: bool(labels[index]) if index is not None else False
                   for name, index in record['selected'].items()}
        outcomes.append({'id': task['id'], 'seed': task['seed'],
                         'family': task['family'], 'reachable': any(labels),
                         'correct': correct})
    names = list(outcomes[0]['correct'])
    def aggregate(group):
        return {'tasks': len(group), 'reachable': sum(row['reachable'] for row in group),
                'correct': {name: sum(row['correct'][name] for row in group)
                            for name in names}}
    by_bank = [{'seed': seed, **aggregate([row for row in outcomes if row['seed'] == seed])}
               for seed in SEEDS]
    summary = {'scope': 'fresh listwise evaluator transfer',
               'overall': aggregate(outcomes), 'by_bank': by_bank,
               'by_family': {family: aggregate([row for row in outcomes
                                                if row['family'] == family])
                             for family in FAMILIES},
               'listwise_120_minus_E192_by_bank': [row['correct']['listwise_120'] -
                                                    row['correct'][A] for row in by_bank]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
