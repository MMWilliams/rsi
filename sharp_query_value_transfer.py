"""Frozen matched-query transfer of learned and fixed verifier allocation."""
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
from sharp_query_value_development import features
from active_probe_diagnostic import program_output
import seed_growth


MODEL = ROOT / 'analysis/temperature-ranker-development.json'
EXPERT = ROOT / 'analysis/context-expert-evaluator-development.json'
VALUE = ROOT / 'analysis/sharp-query-value-frozen.json'
DEST = ROOT / 'runs/sharp-query-value-transfer-20260917'
SEEDS = tuple(range(902258, 902264))
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')
PER_BANK = 32
BUDGET = 95
POLICIES = ('learned', 'top_disagreement', 'uncertainty', 'random')


def inputs():
    raw = {name: path.read_bytes() for name, path in
           [('model', MODEL), ('expert', EXPERT), ('value', VALUE)]}
    data = {name: json.loads(value) for name, value in raw.items()}
    m = data['model']
    mean = np.asarray(m['normalization_mean'], dtype=np.float32)
    scale = np.asarray(m['normalization_scale'], dtype=np.float32)
    weights = m['variants']['0.25']['weights']['120']
    ranker = Ranker(32)
    ranker.load_state_dict({key: torch.tensor(value, dtype=torch.float32)
                            for key, value in weights.items()})
    ranker.eval()
    expert = data['expert']
    global_w = np.asarray(expert['global_weights'], dtype=float)
    experts = {int(key): np.asarray(value, dtype=float)
               for key, value in expert['expert_weights'].items()}
    v = data['value']
    v_mean = np.asarray(v['mean'], dtype=float)
    v_scale = np.asarray(v['scale'], dtype=float)
    v_weights = np.asarray(v['weights'], dtype=float)
    return raw, mean, scale, ranker, global_w, experts, v_mean, v_scale, v_weights


def public_record(task, rows, data):
    _, mean, scale, ranker, global_w, experts, v_mean, v_scale, v_weights = data
    f = representation({'id': task['id'], 'visible': task['visible']}, rows)
    x = np.asarray(f['structural'], dtype=np.float32)
    with torch.no_grad():
        sharp = ranker(torch.from_numpy((x-mean)/scale)).numpy().tolist()
    blend_w = .5*global_w + .5*experts[f['block']]
    blend = (1/(1+np.exp(-np.clip(x@blend_w,-30,30)))).tolist()
    record = {'id': task['id'], 'seed': task['seed'], 'family': task['family'],
              'pool_sha256': digest(rows),
              'scores': {'temp_0.25_120': sharp, 'blend': blend},
              'selected': {'temp_0.25_120': choose(sharp, rows),
                           'blend': choose(blend, rows)}}
    probe, values, disagreement = features(task, record, rows)
    v = np.asarray(values, dtype=float)
    predicted = float(np.r_[(v-v_mean)/v_scale, 1.]@v_weights)
    record.update({'entropy_probe': probe, 'features': values,
                   'top_two_disagreement': disagreement,
                   'value_prediction': predicted,
                   'random_key': hashlib.sha256(('query:'+task['id']).encode()).hexdigest()})
    return record


def allocations(records):
    indices = list(range(len(records)))
    order = {
        'learned': sorted(indices, key=lambda i: (-records[i]['value_prediction'],
                                                  records[i]['id'])),
        'top_disagreement': sorted(indices, key=lambda i: (
            -records[i]['top_two_disagreement'], records[i]['features'][2], records[i]['id'])),
        'uncertainty': sorted(indices, key=lambda i: (records[i]['features'][2],
                                                     records[i]['id'])),
        'random': sorted(indices, key=lambda i: records[i]['random_key']),
    }
    return {name: set(values[:BUDGET]) for name, values in order.items()}


def prepare():
    if DEST.exists():
        raise RuntimeError('transfer directory already exists')
    seed_growth.structure = bool_safe_structure
    data = inputs()
    tasks = [{**task, 'seed': seed} for seed in SEEDS for task in
             random_bank(seed, PER_BANK, FAMILIES, visible=1, hidden=23)]
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated = list(executor.map(pool, tasks))
    pools = {key: rows for key, rows, _ in generated}
    records = [public_record(task, pools[task['id']], data) for task in tasks]
    selected = allocations(records)
    for i, record in enumerate(records):
        record['queries'] = {name: record['entropy_probe'] if i in selected[name] else None
                             for name in POLICIES}
    manifest = {'protocol': 'EXPERIMENT-sharp-query-value-transfer.md',
                'input_sha256': {name: hashlib.sha256(value).hexdigest()
                                 for name, value in data[0].items()},
                'runner_sha256': hashlib.sha256(
                    (ROOT/'sharp_query_value_transfer.py').read_bytes()).hexdigest(),
                'seeds': SEEDS, 'per_bank': PER_BANK, 'query_budget': BUDGET,
                'preparation_wall_seconds': time.perf_counter()-start}
    write_json(DEST/'sealed_bank.json', tasks)
    write_json(DEST/'candidate_pools.json', pools)
    write_json(DEST/'frozen_plans.json', records)
    write_json(DEST/'manifest.json', manifest)
    print(json.dumps({'status': 'prepared', 'tasks': len(tasks),
                      'candidates': sum(map(len,pools.values())),
                      'queries_per_policy': {name: len(selected[name]) for name in POLICIES},
                      'preparation_wall_seconds': manifest['preparation_wall_seconds']}, indent=2))


def score():
    if (DEST/'results.json').exists():
        raise RuntimeError('results already exist')
    manifest = json.loads((DEST/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['input_sha256'] == {name: hashlib.sha256(value).hexdigest()
                                        for name, value in inputs()[0].items()}
    assert manifest['runner_sha256'] == hashlib.sha256(
        (ROOT/'sharp_query_value_transfer.py').read_bytes()).hexdigest()
    tasks = json.loads((DEST/'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((DEST/'candidate_pools.json').read_text(encoding='utf-8'))
    records = json.loads((DEST/'frozen_plans.json').read_text(encoding='utf-8'))
    outcomes = []
    for task, record in zip(tasks, records):
        rows = pools[task['id']]
        assert task['id'] == record['id'] and digest(rows) == record['pool_sha256']
        sharp = record['selected']['temp_0.25_120']
        scores = record['scores']['temp_0.25_120']
        chosen = {'no_query': sharp}
        for name, probe in record['queries'].items():
            if probe is None:
                chosen[name] = sharp
                continue
            inp, truth = task['hidden'][probe]
            matching = [i for i, row in enumerate(rows)
                        if program_output(row['program'], inp) == truth]
            chosen[name] = max(matching, key=lambda i: (
                scores[i], -len(rows[i]['program']), rows[i]['program'])) if matching else sharp
        unique = set(chosen.values())
        labels = {i: bool(evaluate_program(rows[i]['program'], task['hidden'][8:]))
                  for i in unique}
        correct = {name: labels[index] for name, index in chosen.items()}
        outcomes.append({'id': task['id'], 'seed': task['seed'], 'family': task['family'],
                         'chosen': chosen, 'correct': correct,
                         'queries': record['queries']})
    names = ('no_query', *POLICIES)
    def aggregate(group):
        return {'tasks': len(group),
                'queries': {name: sum(row['queries'][name] is not None for row in group)
                            for name in POLICIES},
                'correct': {name: sum(row['correct'][name] for row in group)
                            for name in names}}
    banks = [{'seed': seed, **aggregate([row for row in outcomes if row['seed'] == seed])}
             for seed in SEEDS]
    summary = {'scope': 'fresh matched-query evaluator transfer',
               'overall': aggregate(outcomes), 'by_bank': banks,
               'by_family': {family: aggregate([row for row in outcomes
                                                if row['family'] == family])
                             for family in FAMILIES},
               'learned_minus_top_disagreement_by_bank': [
                   bank['correct']['learned']-bank['correct']['top_disagreement']
                   for bank in banks]}
    write_json(DEST/'results.json', {'summary': summary, 'tasks': outcomes})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
