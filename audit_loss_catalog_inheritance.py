"""Independent replay of the fixed-catalog improver inheritance trial."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import representation
from mixed_probe_diagnostic import pool, bool_safe_structure
from mixed_evaluator_transfer import choose
import seed_growth


DEST = ROOT / 'runs/loss-catalog-inheritance-20260917'
MODEL = ROOT / 'analysis/temperature-ranker-development.json'
PRIOR = ROOT / 'runs/temperature-ranker-transfer-20260917/results.json'
SEEDS = tuple(range(902240, 902252))
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')
CATALOG = ('t1', 't05', 't025')
TEMP = {'t1': '1.0', 't05': '0.5', 't025': '0.25'}


def read(name):
    return json.loads((DEST / name).read_text(encoding='utf-8'))


def best(table):
    return sorted(CATALOG, key=lambda name: (-table[name], CATALOG.index(name)))[0]


def feedback(task, record, rows):
    unique = set(index for index in record['selected'].values() if index is not None)
    truth = {index: bool(evaluate_program(rows[index]['program'], task['hidden'][8:]))
             for index in unique}
    return {name: truth.get(record['selected'][name], False) for name in CATALOG}


def add(table, entries):
    for entry in entries:
        for name in CATALOG:
            table[name] += entry['correct'][name]


def audit():
    seed_growth.structure = bool_safe_structure
    manifest = read('manifest.json')
    assert manifest['runner_sha256'] == hashlib.sha256(
        (ROOT / 'loss_catalog_inheritance.py').read_bytes()).hexdigest()
    assert manifest['model_sha256'] == hashlib.sha256(MODEL.read_bytes()).hexdigest()
    assert manifest['prior_sha256'] == hashlib.sha256(PRIOR.read_bytes()).hexdigest()
    model_data = json.loads(MODEL.read_text(encoding='utf-8'))
    mean = np.asarray(model_data['normalization_mean'], dtype=np.float32)
    scale = np.asarray(model_data['normalization_scale'], dtype=np.float32)
    tasks = read('sealed_bank.json')
    pools = read('candidate_pools.json')
    decisions = read('frozen_model_decisions.json')
    parent = read('parent_frozen.json')
    journal = read('frozen_policy_choices.json')
    result = read('results.json')
    regenerated = [{**task, 'seed': seed} for seed in SEEDS for task in
                   random_bank(seed, 32, FAMILIES, visible=1, hidden=23)]
    assert tasks == regenerated
    assert len(tasks) == len(decisions) == 384
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated = {key: rows for key, rows, _ in executor.map(pool, tasks)}
    assert generated == pools
    assert journal['parent_sha256'] == hashlib.sha256(
        (DEST / 'parent_frozen.json').read_bytes()).hexdigest()
    prior_correct = json.loads(PRIOR.read_text(encoding='utf-8'))['summary']['overall']['correct']
    inherited = {'t1': 64 * (prior_correct['temp_1.0_120'] / 192),
                 't05': 64 * (prior_correct['temp_0.5_120'] / 192),
                 't025': 64 * (prior_correct['temp_0.25_120'] / 192)}
    priors = {'empty': dict.fromkeys(CATALOG, 0.), 'inherited': inherited,
              'scrambled': {'t1': inherited['t025'], 't05': inherited['t1'],
                            't025': inherited['t05']}}
    assert manifest['prior_table'] == priors
    for task, record in zip(tasks, decisions):
        rows = pools[task['id']]
        assert record['id'] == task['id'] and digest(rows) == record['pool_sha256']
        x = np.asarray(representation({'id': task['id'], 'visible': task['visible']},
                                      rows)['structural'], dtype=np.float32)
        tx = (x - mean) / scale
        for name in CATALOG:
            weights = model_data['variants'][TEMP[name]]['weights']['120']
            hidden = np.maximum(tx @ np.asarray(weights['layers.0.weight'], dtype=np.float32).T
                                + np.asarray(weights['layers.0.bias'], dtype=np.float32), 0)
            logits = (hidden @ np.asarray(weights['layers.2.weight'], dtype=np.float32).T
                      + np.asarray(weights['layers.2.bias'], dtype=np.float32)).flatten()
            assert record['selected'][name] == choose(logits, rows)
    actual_parent = {name: 0 for name in CATALOG}
    actual_child = {name: 0 for name in CATALOG}
    actual_parent_policy = {name: 0 for name in priors}
    actual_child_policy = {name: 0 for name in priors}
    for episode in range(6):
        offset = episode * 64
        p = parent['episodes'][episode]
        j = journal['episodes'][episode]
        r = result['episodes'][episode]
        assert p['episode'] == j['episode'] == r['episode'] == episode
        table = {name: value.copy() for name, value in priors.items()}
        parent_admission = []
        for index in range(offset, offset + 16):
            task = tasks[index]
            parent_admission.append({'id': task['id'],
                'correct': feedback(task, decisions[index], pools[task['id']])})
        assert parent_admission == p['parent_admission'] == j['parent_admission']
        for value in table.values():
            add(value, parent_admission)
        assert table == p['parent_tables']
        choice = {name: best(value) for name, value in table.items()}
        assert choice == p['parent_choice'] == j['parent_choice'] == r['parent_choice']
        parent_final = []
        for index in range(offset + 16, offset + 32):
            task = tasks[index]
            parent_final.append({'id': task['id'],
                'correct': feedback(task, decisions[index], pools[task['id']])})
        assert parent_final == j['parent_final']
        for value in table.values():
            add(value, parent_final)
        child_admission = []
        for index in range(offset + 32, offset + 48):
            task = tasks[index]
            child_admission.append({'id': task['id'],
                'correct': feedback(task, decisions[index], pools[task['id']])})
        assert child_admission == j['child_admission']
        for value in table.values():
            add(value, child_admission)
        assert table == j['child_table']
        choice = {name: best(value) for name, value in table.items()}
        assert choice == j['child_choice'] == r['child_choice']
        child_final = []
        for index in range(offset + 48, offset + 64):
            task = tasks[index]
            child_final.append({'id': task['id'],
                'correct': feedback(task, decisions[index], pools[task['id']])})
        assert child_final == r['child_final']
        parent_counts = {name: sum(row['correct'][name] for row in parent_final)
                         for name in CATALOG}
        child_counts = {name: sum(row['correct'][name] for row in child_final)
                        for name in CATALOG}
        assert parent_counts == r['parent_fixed']
        assert child_counts == r['child_fixed']
        for name in CATALOG:
            actual_parent[name] += parent_counts[name]
            actual_child[name] += child_counts[name]
        for name in priors:
            assert r['parent_policy'][name] == parent_counts[r['parent_choice'][name]]
            assert r['child_policy'][name] == child_counts[r['child_choice'][name]]
            actual_parent_policy[name] += r['parent_policy'][name]
            actual_child_policy[name] += r['child_policy'][name]
    summary = result['summary']
    assert actual_parent == summary['parent_fixed']
    assert actual_child == summary['child_fixed']
    assert actual_parent_policy == summary['parent_policy']
    assert actual_child_policy == summary['child_policy']
    report = {'status': 'pass', 'tasks': 384, 'episodes': 6,
              'candidate_pools_regenerated': 384,
              'model_choices_recomputed': 384 * len(CATALOG),
              'parent_and_child_tables_replayed': True,
              'all_feedback_and_final_outcomes_recomputed': True}
    write_json(DEST / 'audit.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    audit()
