"""Frozen fresh-bank transfer of a sharper task-level ranking loss."""
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
from listwise_evaluator_development import Ranker
from listwise_evaluator_transfer import load_inputs, decision as old_decision
import seed_growth


SOURCE = ROOT / 'analysis/temperature-ranker-development.json'
DEST = ROOT / 'runs/temperature-ranker-transfer-20260917'
SEEDS = tuple(range(902234, 902240))
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')
PER_BANK = 32
CHECKPOINTS = (('0.25', '80'), ('0.25', '120'),
               ('0.5', '120'), ('1.0', '120'))


def temp_inputs():
    raw = SOURCE.read_bytes()
    data = json.loads(raw)
    mean = np.asarray(data['normalization_mean'], dtype=np.float32)
    scale = np.asarray(data['normalization_scale'], dtype=np.float32)
    models = {}
    for temperature, epoch in CHECKPOINTS:
        model = Ranker(32)
        state = {key: torch.tensor(value, dtype=torch.float32)
                 for key, value in data['variants'][temperature]['weights'][epoch].items()}
        model.load_state_dict(state)
        model.eval()
        models[(temperature, epoch)] = model
    return raw, mean, scale, models


def decision(task, rows, base, temp):
    record = old_decision(task, rows, base)
    _, mean, scale, models = temp
    if rows:
        x = np.asarray(representation({'id': task['id'], 'visible': task['visible']},
                                      rows)['structural'], dtype=np.float32)
        tx = torch.from_numpy((x - mean) / scale)
        with torch.no_grad():
            for (temperature, epoch), model in models.items():
                name = f'temp_{temperature}_{epoch}'
                logits = model(tx).numpy().tolist()
                record['scores'][name] = logits
                record['selected'][name] = choose(logits, rows)
        assert record['selected']['temp_1.0_120'] == record['selected']['listwise_120']
    else:
        for temperature, epoch in CHECKPOINTS:
            name = f'temp_{temperature}_{epoch}'
            record['scores'][name] = []
            record['selected'][name] = None
    return record


def prepare():
    if DEST.exists():
        raise RuntimeError('transfer directory already exists')
    seed_growth.structure = bool_safe_structure
    base = load_inputs()
    temp = temp_inputs()
    tasks = [{**task, 'seed': seed} for seed in SEEDS for task in
             random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated = list(executor.map(pool, tasks))
    pools = {key: rows for key, rows, _ in generated}
    records = [decision(task, pools[task['id']], base, temp) for task in tasks]
    manifest = {'protocol': 'EXPERIMENT-temperature-ranker-transfer.md',
                'temperature_sha256': hashlib.sha256(temp[0]).hexdigest(),
                'base_input_sha256': {name: hashlib.sha256(value).hexdigest()
                                      for name, value in base[0].items()},
                'runner_sha256': hashlib.sha256(
                    (ROOT / 'temperature_ranker_transfer.py').read_bytes()).hexdigest(),
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
    assert manifest['temperature_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert manifest['base_input_sha256'] == {
        name: hashlib.sha256(value).hexdigest() for name, value in load_inputs()[0].items()}
    assert manifest['runner_sha256'] == hashlib.sha256(
        (ROOT / 'temperature_ranker_transfer.py').read_bytes()).hexdigest()
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
    summary = {'scope': 'fresh temperature-ranker transfer',
               'overall': aggregate(outcomes), 'by_bank': by_bank,
               'by_family': {family: aggregate([row for row in outcomes
                                                if row['family'] == family])
                             for family in FAMILIES},
               'temp_0.25_minus_1.0_by_bank': [row['correct']['temp_0.25_120'] -
                                                row['correct']['temp_1.0_120']
                                                for row in by_bank]}
    write_json(DEST / 'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
