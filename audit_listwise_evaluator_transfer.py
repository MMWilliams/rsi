"""Independent reconstruction of the frozen listwise transfer decisions and scores."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank
from seed_growth import representation
from mixed_probe_diagnostic import bool_safe_structure, pool
from mixed_evaluator_transfer import choose
import seed_growth


DEST = ROOT / 'runs/listwise-evaluator-transfer-20260917'
SOURCE = ROOT / 'analysis/listwise-evaluator-development-v2.json'
SEEDS = tuple(range(902228, 902234))
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')


def read(name):
    return json.loads((DEST / name).read_text(encoding='utf-8'))


def audit():
    seed_growth.structure = bool_safe_structure
    manifest = read('manifest.json')
    assert manifest['runner_sha256'] == hashlib.sha256(
        (ROOT / 'listwise_evaluator_transfer.py').read_bytes()).hexdigest()
    assert manifest['input_sha256']['listwise'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    variant = json.loads(SOURCE.read_text(encoding='utf-8'))['variants']['mlp32']
    mean = np.asarray(variant['normalization_mean'], dtype=np.float32)
    scale = np.asarray(variant['normalization_scale'], dtype=np.float32)
    tasks = read('sealed_bank.json')
    pools = read('candidate_pools.json')
    decisions = read('frozen_decisions.json')
    result = read('results.json')
    regenerated = [{**task, 'seed': seed} for seed in SEEDS for task in
                   random_bank(seed, 32, FAMILIES, visible=1, hidden=23)]
    assert tasks == regenerated
    assert len(tasks) == len(decisions) == len(result['tasks']) == 192
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated_pools = {key: rows for key, rows, _ in executor.map(pool, tasks)}
    assert generated_pools == pools
    actual = {name: 0 for name in result['summary']['overall']['correct']}
    by_bank = {seed: {name: 0 for name in actual} for seed in SEEDS}
    reachable = 0
    for task, record, outcome in zip(tasks, decisions, result['tasks']):
        key = task['id']
        rows = pools[key]
        assert key == record['id'] == outcome['id']
        assert digest(rows) == record['pool_sha256']
        x = np.asarray(representation({'id': key, 'visible': task['visible']},
                                      rows)['structural'], dtype=np.float32)
        tx = (x - mean) / scale
        for epoch in (40, 80, 120):
            state = variant['checkpoint_weights'][str(epoch)]
            hidden = np.maximum(tx @ np.asarray(state['layers.0.weight'], dtype=np.float32).T
                                + np.asarray(state['layers.0.bias'], dtype=np.float32), 0)
            logits = (hidden @ np.asarray(state['layers.2.weight'], dtype=np.float32).T
                      + np.asarray(state['layers.2.bias'], dtype=np.float32)).flatten()
            name = f'listwise_{epoch}'
            assert record['selected'][name] == choose(logits, rows)
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in rows]
        assert outcome['reachable'] == any(labels)
        reachable += any(labels)
        for name, index in record['selected'].items():
            correct = bool(labels[index]) if index is not None else False
            assert correct == outcome['correct'][name]
            actual[name] += correct
            by_bank[task['seed']][name] += correct
    assert reachable == result['summary']['overall']['reachable']
    assert actual == result['summary']['overall']['correct']
    for row in result['summary']['by_bank']:
        assert by_bank[row['seed']] == row['correct']
    report = {'status': 'pass', 'tasks': len(tasks), 'reachable': reachable,
              'candidate_pools_regenerated': len(tasks),
              'listwise_decisions_recomputed': len(tasks) * 3,
              'all_outcomes_recomputed': True}
    write_json(DEST / 'audit.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    audit()
