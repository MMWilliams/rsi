"""Frozen confirmation of improver growth in the complexity-partition environment.

Protocol: EXPERIMENT-complexity-improver-confirmation.md

`prepare` generates three fresh panels, their candidate pools and the frozen
candidate orders. `score` opens final labels and records each specialist's
verified pick and confidence. `improver` runs the history-size curve and the
declared gates. Stage boundaries are hashed so scoring cannot change preparation.
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
from candidate_reranker_transfer import model_for
import complexity_partition_environment as env


DEST = ROOT / 'runs/complexity-improver-confirmation-20260920'
PROTOCOL = ROOT / 'EXPERIMENT-complexity-improver-confirmation.md'
SCRIPT = ROOT / 'complexity_improver_confirmation.py'
E0 = ROOT / 'runs/candidate-reranker-transfer-20260918/e0.joblib'
SPECIALISTS = ROOT / 'analysis/complexity-partition-models-20260920'
PANELS = {'history_a': tuple(range(912100, 912112)),
          'history_b': tuple(range(912200, 912212)),
          'transfer': tuple(range(912300, 912312))}
WIDTH = 100
SIZES = (2, 4, 8, 12, 16, 24)
THRESHOLD = 6
NAMES = [b[0] for b in env.BINS] + ['pooled']
ACTIONS = NAMES + ['e0']


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
                'e0_sha256': sha(E0), 'width': WIDTH,
                'specialist_sha256': {n: sha(SPECIALISTS / f'{n}.joblib')
                                      for n in NAMES},
                'panels': {}}
    for name, seeds in PANELS.items():
        tasks = [{**t, 'seed': s} for s in seeds
                 for t in random_bank(s, 48, FAMILIES, visible=1, hidden=23)]
        base, wide, times = pools_for(tasks)
        records = []
        rescored = 0
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
            assert len(set(record['orders']['e0'])) == len(pool)
            rescored += len(x)
            records.append(record)
        write_json(DEST / f'{name}_bank.json', tasks)
        write_json(DEST / f'{name}_base_pools.json', base)
        write_json(DEST / f'{name}_wide_pools.json', wide)
        write_json(DEST / f'{name}_records.json', records)
        manifest['panels'][name] = {
            'seeds': list(seeds), 'tasks': len(tasks),
            'candidates_rescored': rescored,
            'generation_seconds': sum(times.values()),
            'records_sha256': sha(DEST / f'{name}_records.json')}
        print('prepared', name, len(tasks), flush=True)
    manifest['preparation_wall_seconds'] = time.perf_counter() - start
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'panels frozen',
                      'wall': manifest['preparation_wall_seconds']}, indent=2))


def score():
    if (DEST / 'rows_transfer.json').exists():
        raise RuntimeError('already scored')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    for name in PANELS:
        assert manifest['panels'][name]['records_sha256'] \
            == sha(DEST / f'{name}_records.json')
    models = {n: joblib.load(SPECIALISTS / f'{n}.joblib') for n in NAMES}
    checked = 0
    for name in PANELS:
        tasks = json.loads((DEST / f'{name}_bank.json').read_text())
        base = json.loads((DEST / f'{name}_base_pools.json').read_text())
        wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
        records = json.loads((DEST / f'{name}_records.json').read_text())
        rows = []
        for task, record in zip(tasks, records):
            pool = wide.get(task['id'], base[task['id']])
            old = record['orders']['old']
            head = old[:min(WIDTH, len(old))]
            x = features(task, pool, record, len(head))
            verified = [int(bool(evaluate_program(pool[i]['program'],
                                                  task['hidden'][8:])))
                        for i in head]
            checked += len(verified)
            scores = np.asarray(record['old_scores'], float)
            std = max(float(scores.std()), .05)
            top = float(scores[old[0]])
            stats = {'log_pool': float(np.log1p(len(pool))),
                     'head': float(len(head)),
                     'margin': ((top - float(scores[old[1]])) / std
                                if len(old) > 1 else 0.),
                     'spread': float(np.mean([(top - scores[i]) / std
                                              for i in head])),
                     'distinct': len({str(pool[i]['program'])
                                      for i in head}) / len(head)}
            e0_index = record['orders']['e0'][0]
            labels = {'e0': (verified[head.index(e0_index)] if e0_index in head
                             else int(bool(evaluate_program(
                                 pool[e0_index]['program'],
                                 task['hidden'][8:]))))}
            confidence = {}
            for key, model in models.items():
                p = model.predict_proba(x)[:, 1]
                pick = max(range(len(head)), key=lambda i: (float(p[i]), -i))
                labels[key] = verified[pick]
                confidence[key] = float(p[pick])
            rows.append({'seed': record['seed'], 'family': task['family'],
                         'bin': env.bin_of(verified), 'stats': stats,
                         'labels': labels, 'confidence': confidence})
        write_json(DEST / f'rows_{name}.json', {'panel': name, 'rows': rows})
        print('scored', name, len(rows), flush=True)
    write_json(DEST / 'score_manifest.json',
               {'candidate_labels_checked': checked,
                'rows_sha256': {n: sha(DEST / f'rows_{n}.json') for n in PANELS}})
    print('labels checked', checked)


def banks_of(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['seed']].append(row)
    return [grouped[s] for s in sorted(grouped)]


def load_rows(name):
    return json.loads((DEST / f'rows_{name}.json').read_text())['rows']


def fit_router(tasks, scored_actions):
    x = np.asarray([env.feats(r, scored_actions) for r in tasks], np.float32)
    models = {}
    for action in ACTIONS:
        y = np.asarray([r['labels'][action] for r in tasks], np.int8)
        models[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return models


def deploy(models, target, scored_actions):
    x = np.asarray([env.feats(r, scored_actions) for r in target], np.float32)
    predicted = {a: (np.full(len(target), m) if isinstance(m, float)
                     else m.predict_proba(x)[:, 1]) for a, m in models.items()}
    return [max(ACTIONS, key=lambda a: (float(predicted[a][i]), a))
            for i in range(len(target))]


def per_bank(target_banks, picks):
    out = []
    index = 0
    for bank in target_banks:
        total = 0
        for row in bank:
            total += row['labels'][picks[index]]
            index += 1
        out.append(total)
    return out


def compare(left, right):
    diffs = [int(round(a - b)) for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def improver():
    if (DEST / 'improver_results.json').exists():
        raise RuntimeError('already run')
    score_manifest = json.loads((DEST / 'score_manifest.json').read_text())
    for name in PANELS:
        assert score_manifest['rows_sha256'][name] == sha(DEST / f'rows_{name}.json')
    scored_actions = sorted(NAMES)
    history = banks_of(load_rows('history_a')) + banks_of(load_rows('history_b'))
    target_banks = banks_of(load_rows('transfer'))
    target_rows = [r for bank in target_banks for r in bank]

    default = per_bank(target_banks,
                       [max(NAMES, key=lambda a: (r['confidence'][a], a))
                        for r in target_rows])
    oracle = per_bank(target_banks,
                      [max(ACTIONS, key=lambda a: r['labels'][a])
                       for r in target_rows])

    curve = {}
    for size in SIZES:
        windows = [history[start:start + size]
                   for start in range(len(history) - size + 1)]
        accumulated = np.zeros(len(target_banks))
        totals = []
        for window in windows:
            tasks = [r for bank in window for r in bank]
            picks = deploy(fit_router(tasks, scored_actions), target_rows,
                           scored_actions)
            scores = per_bank(target_banks, picks)
            accumulated += np.asarray(scores, float)
            totals.append(sum(scores))
        expected = accumulated / len(windows)
        curve[str(size)] = {'windows': len(windows),
                            'expected_total': float(expected.sum()),
                            'min_total': int(min(totals)),
                            'max_total': int(max(totals)),
                            'expected_per_bank': [float(v) for v in expected],
                            'vs_default': compare(list(expected), default)}
        value = curve[str(size)]
        print('history={:2d} expected={:7.1f} vs_default={:+d} {}'.format(
            size, value['expected_total'], value['vs_default']['gain'],
            value['vs_default']['interval']), flush=True)

    largest = curve[str(SIZES[-1])]['expected_per_bank']
    smallest = curve[str(SIZES[0])]['expected_per_bank']
    growth = compare(largest, smallest)
    contextual = curve[str(SIZES[-1])]['vs_default']
    monotone = all(curve[str(a)]['expected_total']
                   <= curve[str(b)]['expected_total']
                   for a, b in zip(SIZES, SIZES[1:]))

    result = {
        'scope': 'frozen confirmation on fresh banks',
        'protocol_sha256': sha(PROTOCOL),
        'default_total': sum(default), 'oracle_total': sum(oracle),
        'curve': curve, 'monotone': bool(monotone),
        'gates': {
            'C1_contextual_value': {
                **contextual,
                'passed': bool(contextual['gain'] > 0
                               and contextual['interval'][0] > 0)},
            'C2_improver_growth': {
                **growth,
                'passed': bool(growth['gain'] >= THRESHOLD
                               and growth['losing_banks'] <= 4
                               and growth['interval'][0] > 0)}},
        'candidate_labels_checked':
            score_manifest['candidate_labels_checked'],
        'limits': [
            'One synthetic benchmark and one notion of complexity.',
            'The complexity bin derives from the old ranker order.',
            'Specialists are frozen; this tests routing, not construction.',
            'Contiguous windows are not independent samples.']}
    write_json(DEST / 'improver_results.json', result)
    print('default={} oracle={} monotone={}'.format(
        sum(default), sum(oracle), monotone))
    print('C1: {:+d} {}w/{}l {} passed={}'.format(
        contextual['gain'], contextual['positive_banks'],
        contextual['losing_banks'], contextual['interval'],
        result['gates']['C1_contextual_value']['passed']))
    print('C2: {:+d} {}w/{}l {} passed={}'.format(
        growth['gain'], growth['positive_banks'], growth['losing_banks'],
        growth['interval'], result['gates']['C2_improver_growth']['passed']))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'improver': improver}[sys.argv[1]]()
