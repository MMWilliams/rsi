"""Frozen confirmation of construction-improver growth.

Protocol: EXPERIMENT-construction-improver-confirmation.md, hashed before any
bank is generated.

`prepare` generates three fresh panels with pools and candidate orders.
`cache` computes the candidate feature matrix and verified labels per task, which
is what the improver trains on. `improver` runs the history-size curve, the
pooled baseline and the four declared gates.

Nothing is inherited: the improver builds its partition, specialists and router
from its own history alone.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import FAMILIES, random_bank
from gated_ast_feedback import pools_for, public_block, BLOCK_AST, FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import rank
from cross_family_meta_improver_transfer import interval
from wide_candidate_reranker_development import features
import construction_improver_development as dev


DEST = ROOT / 'runs/construction-improver-confirmation-20260921'
PROTOCOL = ROOT / 'EXPERIMENT-construction-improver-confirmation.md'
SCRIPT = ROOT / 'construction_improver_confirmation.py'
E0 = ROOT / 'runs/candidate-reranker-transfer-20260918/e0.joblib'
PANELS = {'history_a': tuple(range(916100, 916112)),
          'history_b': tuple(range(916200, 916212)),
          'transfer': tuple(range(916300, 916312))}
WIDTH = 100
SIZES = (4, 8, 16, 24)
MAX_WINDOWS = 6
THRESHOLD = 6


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    if (DEST / 'manifest.json').exists():
        raise RuntimeError('already prepared')
    DEST.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(E0)
    manifest = {'protocol_sha256': sha(PROTOCOL), 'runner_sha256': sha(SCRIPT),
                'e0_sha256': sha(E0), 'width': WIDTH, 'panels': {}}
    for name, seeds in PANELS.items():
        tasks = [{**t, 'seed': s} for s in seeds
                 for t in random_bank(s, 48, FAMILIES, visible=1, hidden=23)]
        base, wide, times = pools_for(tasks)
        records = []
        for task in tasks:
            key = task['id']
            block = public_block(task)
            pool = wide.get(key, base[key])
            ranker = replay if block == BLOCK_AST else evaluators[FIXED[block]]
            scores, old_order = rank(task, pool, ranker)
            record = {'id': key, 'seed': task['seed'], 'family': task['family'],
                      'public_block': block, 'pool_sha256': digest(pool),
                      'old_scores': scores, 'orders': {'old': old_order}}
            x = features(task, pool, record, min(WIDTH, len(old_order)))
            probabilities = e0.predict_proba(x)[:, 1]
            head = sorted(range(len(x)),
                          key=lambda i: (-float(probabilities[i]), i))
            record['orders']['e0'] = ([old_order[i] for i in head]
                                      + old_order[len(x):])
            records.append(record)
        write_json(DEST / f'{name}_bank.json', tasks)
        write_json(DEST / f'{name}_base_pools.json', base)
        write_json(DEST / f'{name}_wide_pools.json', wide)
        write_json(DEST / f'{name}_records.json', records)
        manifest['panels'][name] = {
            'seeds': list(seeds), 'tasks': len(tasks),
            'generation_seconds': sum(times.values()),
            'records_sha256': sha(DEST / f'{name}_records.json')}
        print('prepared', name, len(tasks), flush=True)
    manifest['preparation_wall_seconds'] = time.perf_counter() - start
    write_json(DEST / 'manifest.json', manifest)
    print('panels frozen in %.0fs' % manifest['preparation_wall_seconds'])


def cache():
    manifest = json.loads((DEST / 'manifest.json').read_text())
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    checked = 0
    for name in PANELS:
        target = DEST / f'{name}_cache.npz'
        if target.exists():
            continue
        tasks = json.loads((DEST / f'{name}_bank.json').read_text())
        base = json.loads((DEST / f'{name}_base_pools.json').read_text())
        wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
        records = json.loads((DEST / f'{name}_records.json').read_text())
        xs = []
        meta = []
        offset = 0
        for task, record in zip(tasks, records):
            pool = wide.get(task['id'], base[task['id']])
            old = record['orders']['old']
            head = old[:min(WIDTH, len(old))]
            x = features(task, pool, record, len(head))
            labels = [int(bool(evaluate_program(pool[i]['program'],
                                                task['hidden'][8:])))
                      for i in head]
            checked += len(labels)
            e0_index = record['orders']['e0'][0]
            e0_label = (labels[head.index(e0_index)] if e0_index in head
                        else int(bool(evaluate_program(pool[e0_index]['program'],
                                                       task['hidden'][8:]))))
            scores = np.asarray(record['old_scores'], float)
            std = max(float(scores.std()), .05)
            top = float(scores[old[0]])
            xs.append(x)
            meta.append({'seed': record['seed'], 'start': offset,
                         'count': len(head), 'labels': labels,
                         'e0_label': e0_label,
                         'stats': {'log_pool': float(np.log1p(len(pool))),
                                   'head': float(len(head)),
                                   'margin': ((top - float(scores[old[1]])) / std
                                              if len(old) > 1 else 0.),
                                   'spread': float(np.mean(
                                       [(top - scores[i]) / std for i in head])),
                                   'distinct': len({str(pool[i]['program'])
                                                    for i in head}) / len(head)}})
            offset += len(head)
        np.savez_compressed(target, x=np.concatenate(xs))
        write_json(DEST / f'{name}_cache.json', {'panel': name, 'tasks': meta})
        print('cached', name, len(meta), flush=True)
    write_json(DEST / 'cache_manifest.json',
               {'candidate_labels_checked': checked,
                'cache_sha256': {n: sha(DEST / f'{n}_cache.json')
                                 for n in PANELS}})


def load_banks(name):
    x = np.load(DEST / f'{name}_cache.npz')['x']
    meta = json.loads((DEST / f'{name}_cache.json').read_text())['tasks']
    grouped = defaultdict(list)
    for task in meta:
        grouped[task['seed']].append({
            'seed': task['seed'],
            'x': x[task['start']:task['start'] + task['count']],
            'labels': task['labels'], 'e0_label': task['e0_label'],
            'stats': task['stats']})
    return [grouped[s] for s in sorted(grouped)]


def improver():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already run')
    cache_manifest = json.loads((DEST / 'cache_manifest.json').read_text())
    for name in PANELS:
        assert cache_manifest['cache_sha256'][name] == sha(DEST / f'{name}_cache.json')
    history_pool = load_banks('history_a') + load_banks('history_b')
    transfer = load_banks('transfer')
    print('history banks', len(history_pool), 'transfer', len(transfer), flush=True)

    curve = {}
    for size in SIZES:
        span = len(history_pool) - size + 1
        starts = list(range(0, span, max(1, span // MAX_WINDOWS)))[:MAX_WINDOWS]
        built = np.zeros(len(transfer))
        pooled = np.zeros(len(transfer))
        for start in starts:
            history = history_pool[start:start + size]
            specialists = dev.build_system(history)
            order = sorted(specialists)
            actions = order + ['e0']
            router = dev.fit_router(history, specialists, actions, order)
            built += np.asarray(
                dev.deploy(transfer, specialists, router, actions, order), float)
            pooled += np.asarray(dev.pooled_only(transfer, specialists), float)
        built /= len(starts)
        pooled /= len(starts)
        curve[str(size)] = {'windows': len(starts),
                            'built_total': float(built.sum()),
                            'pooled_total': float(pooled.sum()),
                            'built_per_bank': [float(v) for v in built],
                            'pooled_per_bank': [float(v) for v in pooled],
                            'built_minus_pooled': dev.compare(list(built),
                                                              list(pooled))}
        value = curve[str(size)]
        print('history={:2d} built={:6.1f} pooled={:6.1f} diff={:+d} {}'.format(
            size, value['built_total'], value['pooled_total'],
            value['built_minus_pooled']['gain'],
            value['built_minus_pooled']['interval']), flush=True)

    largest = curve[str(SIZES[-1])]
    smallest = curve[str(SIZES[0])]
    e1 = largest['built_minus_pooled']
    e2 = dev.compare(largest['built_per_bank'], smallest['built_per_bank'])
    pooled_growth = dev.compare(largest['pooled_per_bank'],
                                smallest['pooled_per_bank'])
    monotone = all(curve[str(a)]['built_total'] <= curve[str(b)]['built_total']
                   for a, b in zip(SIZES, SIZES[1:]))

    result = {
        'scope': 'frozen confirmation of construction-improver growth',
        'protocol_sha256': sha(PROTOCOL),
        'candidate_labels_checked': cache_manifest['candidate_labels_checked'],
        'sizes': list(SIZES), 'curve': curve,
        'gates': {
            'E1_construction_beats_pooling': {
                **e1, 'passed': bool(e1['gain'] > 0 and e1['interval'][0] > 0)},
            'E2_construction_growth': {
                **e2,
                'passed': bool(e2['gain'] >= THRESHOLD
                               and e2['losing_banks'] <= 4
                               and e2['interval'][0] > 0)},
            'E3_growth_exceeds_data_volume': {
                'construction_growth': e2['gain'],
                'pooled_growth': pooled_growth['gain'],
                'margin': e2['gain'] - pooled_growth['gain'],
                'passed': bool(e2['gain'] > pooled_growth['gain'])},
            'E4_monotone': {'passed': bool(monotone)}},
        'pooled_growth_detail': pooled_growth,
        'limits': [
            'One synthetic benchmark and one notion of complexity.',
            'The partition rule is researcher written; the improver computes '
            'the partition and trains every model but did not invent the rule.',
            'Strided windows over one history pool are not independent.',
            'Recursive child-improver growth is untested here and failed its '
            'own screen; see RECURSIVE-GROWTH-2026-09-21.md.']}
    write_json(DEST / 'results.json', result)
    for key, value in result['gates'].items():
        print(key, json.dumps(value))


if __name__ == '__main__':
    {'prepare': prepare, 'cache': cache, 'improver': improver}[sys.argv[1]]()
