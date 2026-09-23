"""Frozen fixed-catalog parent/child improver inheritance trial."""
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
import seed_growth


MODEL_SOURCE = ROOT / 'analysis/temperature-ranker-development.json'
PRIOR_SOURCE = ROOT / 'runs/temperature-ranker-transfer-20260917/results.json'
DEST = ROOT / 'runs/loss-catalog-inheritance-20260917'
SEEDS = tuple(range(902240, 902252))
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')
PER_BANK = 32
CATALOG = ('t1', 't05', 't025')
TEMP = {'t1': '1.0', 't05': '0.5', 't025': '0.25'}
POLICIES = ('empty', 'inherited', 'scrambled')
PRIOR_EFFECTIVE_TASKS = 64


def model_inputs():
    raw = MODEL_SOURCE.read_bytes()
    data = json.loads(raw)
    mean = np.asarray(data['normalization_mean'], dtype=np.float32)
    scale = np.asarray(data['normalization_scale'], dtype=np.float32)
    models = {}
    for name in CATALOG:
        model = Ranker(32)
        weights = data['variants'][TEMP[name]]['weights']['120']
        model.load_state_dict({key: torch.tensor(value, dtype=torch.float32)
                               for key, value in weights.items()})
        model.eval()
        models[name] = model
    return raw, mean, scale, models


def prior_inputs():
    raw = PRIOR_SOURCE.read_bytes()
    counts = json.loads(raw)['summary']['overall']['correct']
    rates = {'t1': counts['temp_1.0_120'] / 192,
             't05': counts['temp_0.5_120'] / 192,
             't025': counts['temp_0.25_120'] / 192}
    inherited = {name: PRIOR_EFFECTIVE_TASKS * rate for name, rate in rates.items()}
    scrambled = {'t1': inherited['t025'], 't05': inherited['t1'],
                 't025': inherited['t05']}
    return raw, {'empty': dict.fromkeys(CATALOG, 0.),
                 'inherited': inherited, 'scrambled': scrambled}


def model_decision(task, rows, inputs):
    _, mean, scale, models = inputs
    selected = {}
    if rows:
        x = np.asarray(representation({'id': task['id'], 'visible': task['visible']},
                                      rows)['structural'], dtype=np.float32)
        tx = torch.from_numpy((x - mean) / scale)
        with torch.no_grad():
            for name, model in models.items():
                selected[name] = choose(model(tx).numpy(), rows)
    else:
        selected = dict.fromkeys(CATALOG)
    return {'id': task['id'], 'seed': task['seed'], 'family': task['family'],
            'pool_sha256': digest(rows), 'selected': selected}


def verify_prepared():
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['model_sha256'] == hashlib.sha256(MODEL_SOURCE.read_bytes()).hexdigest()
    assert manifest['prior_sha256'] == hashlib.sha256(PRIOR_SOURCE.read_bytes()).hexdigest()
    assert manifest['runner_sha256'] == hashlib.sha256(
        (ROOT / 'loss_catalog_inheritance.py').read_bytes()).hexdigest()
    return manifest


def prepare():
    if DEST.exists():
        raise RuntimeError('transfer directory already exists')
    seed_growth.structure = bool_safe_structure
    inputs = model_inputs()
    prior_raw, priors = prior_inputs()
    tasks = [{**task, 'seed': seed} for seed in SEEDS for task in
             random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated = list(executor.map(pool, tasks))
    pools = {key: rows for key, rows, _ in generated}
    records = [model_decision(task, pools[task['id']], inputs) for task in tasks]
    manifest = {'protocol': 'EXPERIMENT-loss-catalog-inheritance.md',
                'model_sha256': hashlib.sha256(inputs[0]).hexdigest(),
                'prior_sha256': hashlib.sha256(prior_raw).hexdigest(),
                'runner_sha256': hashlib.sha256(
                    (ROOT / 'loss_catalog_inheritance.py').read_bytes()).hexdigest(),
                'seeds': SEEDS, 'per_bank': PER_BANK,
                'prior_effective_tasks': PRIOR_EFFECTIVE_TASKS,
                'prior_table': priors,
                'preparation_wall_seconds': time.perf_counter() - start}
    write_json(DEST / 'sealed_bank.json', tasks)
    write_json(DEST / 'candidate_pools.json', pools)
    write_json(DEST / 'frozen_model_decisions.json', records)
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', 'tasks': len(tasks),
                      'candidates': sum(map(len, pools.values())),
                      'preparation_wall_seconds': manifest['preparation_wall_seconds']}, indent=2))


def verified_choices(task, record, rows):
    assert digest(rows) == record['pool_sha256']
    unique = set(index for index in record['selected'].values() if index is not None)
    labels = {index: bool(evaluate_program(rows[index]['program'], task['hidden'][8:]))
              for index in unique}
    return {name: labels.get(record['selected'][name], False) for name in CATALOG}, len(unique)


def select(table):
    return max(CATALOG, key=lambda name: (table[name], -CATALOG.index(name)))


def add(table, feedback):
    for row in feedback:
        for name in CATALOG:
            table[name] += row['correct'][name]


def admit():
    if (DEST / 'parent_frozen.json').exists() or (DEST / 'frozen_policy_choices.json').exists():
        raise RuntimeError('policy choices already frozen')
    verify_prepared()
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((DEST / 'frozen_model_decisions.json').read_text(encoding='utf-8'))
    priors = prior_inputs()[1]
    parents = []
    distinct_evaluations = 0
    start = time.perf_counter()
    for episode in range(len(SEEDS) // 2):
        parent_start = episode * 64
        parent_admission = []
        for index in range(parent_start, parent_start + 16):
            correct, unique = verified_choices(tasks[index], decisions[index],
                                               pools[tasks[index]['id']])
            parent_admission.append({'id': tasks[index]['id'], 'correct': correct})
            distinct_evaluations += unique
        parent_tables = {name: value.copy() for name, value in priors.items()}
        for table in parent_tables.values():
            add(table, parent_admission)
        parent_choice = {name: select(table) for name, table in parent_tables.items()}
        parents.append({'episode': episode, 'parent_seed': SEEDS[episode * 2],
                        'child_seed': SEEDS[episode * 2 + 1],
                        'parent_admission': parent_admission,
                        'parent_choice': parent_choice,
                        'parent_tables': parent_tables})
    write_json(DEST / 'parent_frozen.json', {'episodes': parents})
    parent_sha256 = hashlib.sha256((DEST / 'parent_frozen.json').read_bytes()).hexdigest()
    episodes = []
    for parent in parents:
        episode = parent['episode']
        parent_start = episode * 64
        parent_tables = parent['parent_tables']
        parent_final = []
        for index in range(parent_start + 16, parent_start + 32):
            correct, unique = verified_choices(tasks[index], decisions[index],
                                               pools[tasks[index]['id']])
            parent_final.append({'id': tasks[index]['id'], 'correct': correct})
            distinct_evaluations += unique
        for table in parent_tables.values():
            add(table, parent_final)
        child_admission = []
        for index in range(parent_start + 32, parent_start + 48):
            correct, unique = verified_choices(tasks[index], decisions[index],
                                               pools[tasks[index]['id']])
            child_admission.append({'id': tasks[index]['id'], 'correct': correct})
            distinct_evaluations += unique
        for table in parent_tables.values():
            add(table, child_admission)
        child_choice = {name: select(table) for name, table in parent_tables.items()}
        episodes.append({'episode': episode, 'parent_seed': parent['parent_seed'],
                         'child_seed': parent['child_seed'],
                         'parent_admission': parent['parent_admission'],
                         'parent_final': parent_final,
                         'child_admission': child_admission,
                         'parent_choice': parent['parent_choice'],
                         'child_choice': child_choice,
                         'child_table': parent_tables})
    journal = {'episodes': episodes, 'parent_sha256': parent_sha256,
               'distinct_program_evaluations': distinct_evaluations,
               'example_executions': distinct_evaluations * 15,
               'admission_wall_seconds': time.perf_counter() - start}
    write_json(DEST / 'frozen_policy_choices.json', journal)
    print(json.dumps({'status': 'admitted', 'episodes': len(episodes),
                      'distinct_program_evaluations': distinct_evaluations,
                      'example_executions': distinct_evaluations * 15}, indent=2))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('results already exist')
    verify_prepared()
    tasks = json.loads((DEST / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((DEST / 'frozen_model_decisions.json').read_text(encoding='utf-8'))
    journal = json.loads((DEST / 'frozen_policy_choices.json').read_text(encoding='utf-8'))
    assert journal['parent_sha256'] == hashlib.sha256(
        (DEST / 'parent_frozen.json').read_bytes()).hexdigest()
    episodes = []
    final_evaluations = 0
    for entry in journal['episodes']:
        offset = entry['episode'] * 64
        child_final = []
        for index in range(offset + 48, offset + 64):
            correct, unique = verified_choices(tasks[index], decisions[index],
                                               pools[tasks[index]['id']])
            child_final.append({'id': tasks[index]['id'], 'correct': correct})
            final_evaluations += unique
        parent = {name: sum(row['correct'][name] for row in entry['parent_final'])
                  for name in CATALOG}
        child = {name: sum(row['correct'][name] for row in child_final)
                 for name in CATALOG}
        parent_policy = {policy: parent[chosen] for policy, chosen in
                         entry['parent_choice'].items()}
        child_policy = {policy: child[chosen] for policy, chosen in
                        entry['child_choice'].items()}
        episodes.append({'episode': entry['episode'], 'parent_seed': entry['parent_seed'],
                         'child_seed': entry['child_seed'],
                         'parent_fixed': parent, 'child_fixed': child,
                         'parent_choice': entry['parent_choice'],
                         'child_choice': entry['child_choice'],
                         'parent_policy': parent_policy, 'child_policy': child_policy,
                         'child_final': child_final})
    summary = {'scope': 'fresh fixed-catalog parent/child inheritance transfer',
               'episodes': len(episodes), 'child_final_tasks': len(episodes) * 16,
               'parent_fixed': {name: sum(row['parent_fixed'][name] for row in episodes)
                                for name in CATALOG},
               'child_fixed': {name: sum(row['child_fixed'][name] for row in episodes)
                               for name in CATALOG},
               'parent_policy': {name: sum(row['parent_policy'][name] for row in episodes)
                                 for name in POLICIES},
               'child_policy': {name: sum(row['child_policy'][name] for row in episodes)
                                for name in POLICIES},
               'child_inherited_minus_empty_by_episode': [
                   row['child_policy']['inherited'] - row['child_policy']['empty']
                   for row in episodes],
               'admission_program_evaluations': journal['distinct_program_evaluations'],
               'final_program_evaluations': final_evaluations}
    write_json(DEST / 'results.json', {'summary': summary, 'episodes': episodes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'admit': admit, 'score': score}[sys.argv[1]]()
