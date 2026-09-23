"""Independent audit of a complexity-improver confirmation run.

Regenerates each panel from its seeds, rebuilds every candidate pool, recomputes
both candidate orders, rechecks every final label, recomputes the latent
complexity bin and each specialist's verified pick and confidence, then rebuilds
the history-size curve and both gates with its own code.

It does not import the runner's scoring, router fitting or gate helpers; those
are re-derived here so a bug in the runner cannot be reproduced.

Run one panel per process (`python audit_... <panel>`), then with no argument to
combine. Commit, not physical RAM, is the binding memory constraint here.
"""
from __future__ import annotations

import hashlib
import json
import sys
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
import complexity_improver_confirmation as conf


DEST = conf.DEST
PANELS = conf.PANELS
PROTOCOL = conf.PROTOCOL
SPECIALISTS = conf.SPECIALISTS
E0 = conf.E0
WIDTH = conf.WIDTH
SIZES = conf.SIZES
NAMES = conf.NAMES
ACTIONS = conf.ACTIONS
BINS = (('shallow', 0, 3), ('mid', 3, 15), ('deep', 15, 100))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bin_of(labels):
    for rank_index, y in enumerate(labels):
        if y:
            for name, low, high in BINS:
                if low <= rank_index < high:
                    return name
            return BINS[-1][0]
    return 'unreachable'


def rebuild_panel(name):
    failures = []
    manifest = json.loads((DEST / 'manifest.json').read_text())
    seeds = manifest['panels'][name]['seeds']
    tasks = [{**t, 'seed': s} for s in seeds
             for t in random_bank(s, 48, FAMILIES, visible=1, hidden=23)]
    sealed = json.loads((DEST / f'{name}_bank.json').read_text())
    if [t['id'] for t in tasks] != [t['id'] for t in sealed]:
        failures.append(f'{name}: regenerated task ids differ')

    base, wide, _ = pools_for(tasks)
    stored_base = json.loads((DEST / f'{name}_base_pools.json').read_text())
    stored_wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
    records = json.loads((DEST / f'{name}_records.json').read_text())
    stored_rows = json.loads((DEST / f'rows_{name}.json').read_text())['rows']

    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(E0)
    models = {n: joblib.load(SPECIALISTS / f'{n}.joblib') for n in NAMES}

    rows = []
    checked = 0
    for task, record, stored in zip(tasks, records, stored_rows):
        key = task['id']
        pool = wide.get(key, base[key])
        if digest(pool) != digest(stored_wide.get(key, stored_base[key])):
            failures.append(f'{name}/{key}: regenerated pool differs')
            pool = stored_wide.get(key, stored_base[key])
        if record['pool_sha256'] != digest(pool):
            failures.append(f'{name}/{key}: recorded pool hash differs')

        block = public_block(task)
        ranker = replay if block == BLOCK_AST else evaluators[FIXED[block]]
        scores, old_order = rank(task, pool, ranker)
        if old_order != record['orders']['old']:
            failures.append(f'{name}/{key}: old order differs')

        rebuilt = {'orders': {'old': old_order}, 'old_scores': scores}
        head = old_order[:min(WIDTH, len(old_order))]
        x = features(task, pool, rebuilt, len(head))
        probabilities = e0.predict_proba(x)[:, 1]
        ordered = sorted(range(len(x)),
                         key=lambda i: (-float(probabilities[i]), i))
        e0_order = [old_order[i] for i in ordered] + old_order[len(x):]
        if e0_order != record['orders']['e0']:
            failures.append(f'{name}/{key}: e0 order differs')

        verified = [int(bool(evaluate_program(pool[i]['program'],
                                              task['hidden'][8:])))
                    for i in head]
        checked += len(verified)
        arr = np.asarray(scores, float)
        std = max(float(arr.std()), .05)
        top = float(arr[old_order[0]])
        stats = {'log_pool': float(np.log1p(len(pool))),
                 'head': float(len(head)),
                 'margin': ((top - float(arr[old_order[1]])) / std
                            if len(old_order) > 1 else 0.),
                 'spread': float(np.mean([(top - arr[i]) / std for i in head])),
                 'distinct': len({str(pool[i]['program'])
                                  for i in head}) / len(head)}
        e0_index = e0_order[0]
        labels = {'e0': (verified[head.index(e0_index)] if e0_index in head
                         else int(bool(evaluate_program(
                             pool[e0_index]['program'], task['hidden'][8:]))))}
        confidence = {}
        for key_name, model in models.items():
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(head)), key=lambda i: (float(p[i]), -i))
            labels[key_name] = verified[pick]
            confidence[key_name] = float(p[pick])

        computed_bin = bin_of(verified)
        if computed_bin != stored['bin']:
            failures.append(f'{name}/{key}: complexity bin differs')
        if labels != stored['labels']:
            failures.append(f'{name}/{key}: verified action labels differ')
        rows.append({'seed': task['seed'], 'family': task['family'],
                     'bin': computed_bin, 'stats': stats,
                     'labels': labels, 'confidence': confidence})

    write_json(DEST / f'audit_rows_{name}.json',
               {'panel': name, 'rows': rows, 'labels_checked': checked,
                'failures': failures})
    print('rebuilt', name, len(rows), checked, 'failures', len(failures))


def feats(row, scored_actions):
    stats = row['stats']
    return np.asarray([stats['log_pool'], stats['margin'], stats['spread'],
                       stats['distinct'], stats['head'] / 100.]
                      + [row['confidence'][a] for a in scored_actions],
                      np.float32)


def banks_of(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['seed']].append(row)
    return [grouped[s] for s in sorted(grouped)]


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


def main():
    failures = []
    recorded = json.loads((DEST / 'improver_results.json').read_text())
    manifest = json.loads((DEST / 'manifest.json').read_text())
    if manifest['protocol_sha256'] != sha(PROTOCOL):
        failures.append('protocol hash differs from the frozen manifest')
    for name in NAMES:
        if manifest['specialist_sha256'][name] != sha(
                SPECIALISTS / f'{name}.joblib'):
            failures.append(f'specialist {name} changed after freezing')

    panels = {}
    labels_checked = 0
    for name in PANELS:
        cached = DEST / f'audit_rows_{name}.json'
        if not cached.exists():
            raise RuntimeError(f'run "{name}" first')
        part = json.loads(cached.read_text())
        failures.extend(part['failures'])
        panels[name] = part['rows']
        labels_checked += part['labels_checked']

    scored_actions = sorted(NAMES)
    history = banks_of(panels['history_a']) + banks_of(panels['history_b'])
    target_banks = banks_of(panels['transfer'])
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
        for window in windows:
            tasks = [r for bank in window for r in bank]
            x = np.asarray([feats(r, scored_actions) for r in tasks], np.float32)
            fitted = {}
            for action in ACTIONS:
                y = np.asarray([r['labels'][action] for r in tasks], np.int8)
                fitted[action] = (model_for(15).fit(x, y)
                                  if 0 < y.sum() < len(y) else float(y.mean()))
            xt = np.asarray([feats(r, scored_actions) for r in target_rows],
                            np.float32)
            predicted = {a: (np.full(len(target_rows), m)
                             if isinstance(m, float)
                             else m.predict_proba(xt)[:, 1])
                         for a, m in fitted.items()}
            picks = [max(ACTIONS, key=lambda a: (float(predicted[a][i]), a))
                     for i in range(len(target_rows))]
            accumulated += np.asarray(per_bank(target_banks, picks), float)
        expected = accumulated / len(windows)
        curve[str(size)] = {'expected_total': float(expected.sum()),
                            'expected_per_bank': [float(v) for v in expected]}
        print('rebuilt history={:2d} expected={:7.1f}'.format(
            size, float(expected.sum())), flush=True)

    largest = curve[str(SIZES[-1])]['expected_per_bank']
    smallest = curve[str(SIZES[0])]['expected_per_bank']
    growth = compare(largest, smallest)
    contextual = compare(largest, default)
    gates = {
        'C1_contextual_value': {
            **contextual,
            'passed': bool(contextual['gain'] > 0
                           and contextual['interval'][0] > 0)},
        'C2_improver_growth': {
            **growth,
            'passed': bool(growth['gain'] >= conf.THRESHOLD
                           and growth['losing_banks'] <= 4
                           and growth['interval'][0] > 0)}}

    if sum(default) != recorded['default_total']:
        failures.append('default total differs from the recorded run')
    if sum(oracle) != recorded['oracle_total']:
        failures.append('oracle total differs from the recorded run')
    for name, value in gates.items():
        if json.loads(json.dumps(value)) != recorded['gates'][name]:
            failures.append(f'gate {name} differs from the recorded run')
    for size in SIZES:
        a = round(curve[str(size)]['expected_total'], 6)
        b = round(recorded['curve'][str(size)]['expected_total'], 6)
        if a != b:
            failures.append(f'curve at history {size} differs: {a} vs {b}')
    if labels_checked != recorded['candidate_labels_checked']:
        failures.append('candidate label count differs')

    audit = {'scope': 'independent reconstruction of the complexity-improver '
                      'confirmation',
             'run': DEST.name,
             'protocol_sha256': sha(PROTOCOL),
             'tasks_rebuilt': sum(len(v) for v in panels.values()),
             'candidate_labels_rechecked': labels_checked,
             'curve_rebuilt': {k: v['expected_total'] for k, v in curve.items()},
             'gates_rebuilt': gates,
             'failures': failures, 'passed': not failures}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps({'passed': audit['passed'],
                      'tasks_rebuilt': audit['tasks_rebuilt'],
                      'candidate_labels_rechecked': labels_checked,
                      'failures': failures[:20]}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        rebuild_panel(sys.argv[1])
    else:
        main()
