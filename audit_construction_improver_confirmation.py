"""Independent audit of a construction-improver confirmation run.

Regenerates each panel from its seeds, rebuilds every candidate pool, recomputes
both candidate orders, rechecks every final label and every cached feature row,
then rebuilds the entire construction curve with its own re-derived partition,
specialist training, router fitting and deployment, and recomputes all four
gates.

It deliberately imports none of `construction_improver_development`; the
improver's whole procedure is written out again here so a bug in the runner
cannot be reproduced by sharing its code.

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
import construction_improver_confirmation as conf


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
    dest = conf.DEST
    manifest = json.loads((dest / 'manifest.json').read_text())
    seeds = manifest['panels'][name]['seeds']
    tasks = [{**t, 'seed': s} for s in seeds
             for t in random_bank(s, 48, FAMILIES, visible=1, hidden=23)]
    sealed = json.loads((dest / f'{name}_bank.json').read_text())
    if [t['id'] for t in tasks] != [t['id'] for t in sealed]:
        failures.append(f'{name}: regenerated task ids differ')

    base, wide, _ = pools_for(tasks)
    stored_base = json.loads((dest / f'{name}_base_pools.json').read_text())
    stored_wide = json.loads((dest / f'{name}_wide_pools.json').read_text())
    records = json.loads((dest / f'{name}_records.json').read_text())
    cached = json.loads((dest / f'{name}_cache.json').read_text())['tasks']
    cached_x = np.load(dest / f'{name}_cache.npz')['x']

    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(conf.E0)

    rows = []
    checked = 0
    for task, record, entry in zip(tasks, records, cached):
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
        head = old_order[:min(conf.WIDTH, len(old_order))]
        x = features(task, pool, rebuilt, len(head))
        probabilities = e0.predict_proba(x)[:, 1]
        ordered = sorted(range(len(x)),
                         key=lambda i: (-float(probabilities[i]), i))
        e0_order = [old_order[i] for i in ordered] + old_order[len(x):]
        if e0_order != record['orders']['e0']:
            failures.append(f'{name}/{key}: e0 order differs')

        labels = [int(bool(evaluate_program(pool[i]['program'],
                                            task['hidden'][8:]))) for i in head]
        checked += len(labels)
        e0_index = e0_order[0]
        e0_label = (labels[head.index(e0_index)] if e0_index in head
                    else int(bool(evaluate_program(pool[e0_index]['program'],
                                                   task['hidden'][8:]))))
        if labels != entry['labels']:
            failures.append(f'{name}/{key}: cached labels differ')
        if e0_label != entry['e0_label']:
            failures.append(f'{name}/{key}: cached e0 label differs')
        stored_rows = cached_x[entry['start']:entry['start'] + entry['count']]
        if not np.allclose(x, stored_rows, atol=1e-5):
            failures.append(f'{name}/{key}: cached feature rows differ')

        arr = np.asarray(scores, float)
        std = max(float(arr.std()), .05)
        top = float(arr[old_order[0]])
        rows.append({'seed': task['seed'], 'x': x.tolist(), 'labels': labels,
                     'e0_label': e0_label,
                     'stats': {'log_pool': float(np.log1p(len(pool))),
                               'head': float(len(head)),
                               'margin': ((top - float(arr[old_order[1]])) / std
                                          if len(old_order) > 1 else 0.),
                               'spread': float(np.mean([(top - arr[i]) / std
                                                        for i in head])),
                               'distinct': len({str(pool[i]['program'])
                                                for i in head}) / len(head)}})
    np.savez_compressed(dest / f'audit_{name}.npz',
                        x=np.concatenate([np.asarray(r['x'], np.float32)
                                          for r in rows]))
    offset = 0
    meta = []
    for row in rows:
        count = len(row['labels'])
        meta.append({'seed': row['seed'], 'start': offset, 'count': count,
                     'labels': row['labels'], 'e0_label': row['e0_label'],
                     'stats': row['stats']})
        offset += count
    write_json(dest / f'audit_{name}.json',
               {'panel': name, 'tasks': meta, 'labels_checked': checked,
                'failures': failures})
    print('rebuilt', name, len(rows), checked, 'failures', len(failures))


def load_banks(name):
    dest = conf.DEST
    x = np.load(dest / f'audit_{name}.npz')['x']
    part = json.loads((dest / f'audit_{name}.json').read_text())
    grouped = defaultdict(list)
    for task in part['tasks']:
        grouped[task['seed']].append({
            'seed': task['seed'],
            'x': x[task['start']:task['start'] + task['count']],
            'labels': task['labels'], 'e0_label': task['e0_label'],
            'stats': task['stats']})
    return [grouped[s] for s in sorted(grouped)], part


def build(history):
    tasks = [t for bank in history for t in bank]
    groups = defaultdict(list)
    for task in tasks:
        groups[bin_of(task['labels'])].append(task)
    models = {}
    for name, group in groups.items():
        if name == 'unreachable' or len(group) < 8:
            continue
        x = np.concatenate([t['x'] for t in group])
        y = np.concatenate([np.asarray(t['labels'], np.int8) for t in group])
        if 0 < y.sum() < len(y):
            models[name] = model_for(15).fit(x, y)
    px = np.concatenate([t['x'] for t in tasks])
    py = np.concatenate([np.asarray(t['labels'], np.int8) for t in tasks])
    models['pooled'] = model_for(15).fit(px, py)
    return models


def view(task, models):
    labels = {'e0': task['e0_label']}
    confidence = {}
    for name, model in models.items():
        p = model.predict_proba(task['x'])[:, 1]
        pick = max(range(len(p)), key=lambda i: (float(p[i]), -i))
        labels[name] = task['labels'][pick]
        confidence[name] = float(p[pick])
    return labels, confidence


def vector(stats, confidence, order):
    return np.asarray([stats['log_pool'], stats['margin'], stats['spread'],
                       stats['distinct'], stats['head'] / 100.]
                      + [confidence[a] for a in order], np.float32)


def route(history, models, actions, order):
    rows = []
    targets = defaultdict(list)
    for bank in history:
        for task in bank:
            labels, confidence = view(task, models)
            rows.append(vector(task['stats'], confidence, order))
            for action in actions:
                targets[action].append(labels[action])
    x = np.asarray(rows, np.float32)
    fitted = {}
    for action in actions:
        y = np.asarray(targets[action], np.int8)
        fitted[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return fitted


def run(transfer, models, router, actions, order):
    out = []
    for bank in transfer:
        total = 0
        for task in bank:
            labels, confidence = view(task, models)
            x = vector(task['stats'], confidence, order).reshape(1, -1)
            best, best_p = None, -1.
            for action in actions:
                model = router[action]
                p = (model if isinstance(model, float)
                     else float(model.predict_proba(x)[0, 1]))
                if p > best_p or (p == best_p and action < best):
                    best, best_p = action, p
            total += labels[best]
        out.append(total)
    return out


def pooled_run(transfer, models):
    out = []
    for bank in transfer:
        total = 0
        for task in bank:
            p = models['pooled'].predict_proba(task['x'])[:, 1]
            pick = max(range(len(p)), key=lambda i: (float(p[i]), -i))
            total += task['labels'][pick]
        out.append(total)
    return out


def compare(left, right):
    diffs = [int(round(a - b)) for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def main():
    dest = conf.DEST
    failures = []
    recorded = json.loads((dest / 'results.json').read_text())
    manifest = json.loads((dest / 'manifest.json').read_text())
    if manifest['protocol_sha256'] != sha(conf.PROTOCOL):
        failures.append('protocol hash differs from the frozen manifest')

    panels = {}
    labels_checked = 0
    for name in conf.PANELS:
        if not (dest / f'audit_{name}.json').exists():
            raise RuntimeError(f'run "{name}" first')
        banks, part = load_banks(name)
        failures.extend(part['failures'])
        labels_checked += part['labels_checked']
        panels[name] = banks

    history_pool = panels['history_a'] + panels['history_b']
    transfer = panels['transfer']
    curve = {}
    for size in conf.SIZES:
        span = len(history_pool) - size + 1
        starts = list(range(0, span, max(1, span // conf.MAX_WINDOWS)))[:conf.MAX_WINDOWS]
        built = np.zeros(len(transfer))
        pooled = np.zeros(len(transfer))
        for start in starts:
            history = history_pool[start:start + size]
            models = build(history)
            order = sorted(models)
            actions = order + ['e0']
            router = route(history, models, actions, order)
            built += np.asarray(run(transfer, models, router, actions, order),
                                float)
            pooled += np.asarray(pooled_run(transfer, models), float)
        built /= len(starts)
        pooled /= len(starts)
        curve[str(size)] = {'built_total': float(built.sum()),
                            'pooled_total': float(pooled.sum()),
                            'built_per_bank': [float(v) for v in built],
                            'pooled_per_bank': [float(v) for v in pooled],
                            'built_minus_pooled': compare(list(built), list(pooled))}
        print('rebuilt history={:2d} built={:6.1f} pooled={:6.1f}'.format(
            size, float(built.sum()), float(pooled.sum())), flush=True)

    largest = curve[str(conf.SIZES[-1])]
    smallest = curve[str(conf.SIZES[0])]
    e1 = largest['built_minus_pooled']
    e2 = compare(largest['built_per_bank'], smallest['built_per_bank'])
    pooled_growth = compare(largest['pooled_per_bank'],
                            smallest['pooled_per_bank'])
    monotone = all(curve[str(a)]['built_total'] <= curve[str(b)]['built_total']
                   for a, b in zip(conf.SIZES, conf.SIZES[1:]))
    gates = {
        'E1_construction_beats_pooling': {
            **e1, 'passed': bool(e1['gain'] > 0 and e1['interval'][0] > 0)},
        'E2_construction_growth': {
            **e2,
            'passed': bool(e2['gain'] >= conf.THRESHOLD
                           and e2['losing_banks'] <= 4
                           and e2['interval'][0] > 0)},
        'E3_growth_exceeds_data_volume': {
            'construction_growth': e2['gain'],
            'pooled_growth': pooled_growth['gain'],
            'margin': e2['gain'] - pooled_growth['gain'],
            'passed': bool(e2['gain'] > pooled_growth['gain'])},
        'E4_monotone': {'passed': bool(monotone)}}

    for name, value in gates.items():
        if json.loads(json.dumps(value)) != recorded['gates'][name]:
            failures.append(f'gate {name} differs from the recorded run')
    for size in conf.SIZES:
        a = round(curve[str(size)]['built_total'], 6)
        b = round(recorded['curve'][str(size)]['built_total'], 6)
        if a != b:
            failures.append(f'built curve at {size} differs: {a} vs {b}')
    if labels_checked != recorded['candidate_labels_checked']:
        failures.append('candidate label count differs')

    audit = {'scope': 'independent reconstruction of the construction-improver '
                      'confirmation',
             'run': dest.name, 'protocol_sha256': sha(conf.PROTOCOL),
             'tasks_rebuilt': sum(len(b) for banks in panels.values()
                                  for b in banks),
             'candidate_labels_rechecked': labels_checked,
             'curve_rebuilt': {k: v['built_total'] for k, v in curve.items()},
             'gates_rebuilt': gates,
             'failures': failures, 'passed': not failures}
    write_json(dest / 'audit.json', audit)
    print(json.dumps({'passed': audit['passed'],
                      'tasks_rebuilt': audit['tasks_rebuilt'],
                      'candidate_labels_rechecked': labels_checked,
                      'failures': failures[:20]}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        rebuild_panel(sys.argv[1])
    else:
        main()
