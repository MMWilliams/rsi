"""An environment where the public signature does not identify the mechanism.

Seven action spaces have failed the four preconditions, all for the same reason:
"use the specialist matching this task's public region, trained on the most
data" is near-optimal and needs no labels. That rule works because in this
benchmark the public Unicode block *is* the mechanism.

`shifted_ast_bank` breaks that by construction and not by anything added here.
It generates four distinct arithmetic predicates, and all four present in block
0x800. The public signature is identical across them, so no region-matching rule
can exist, and which specialist applies must be inferred from evidence.

This screens per-rule specialists against all four preconditions on the shifted
tasks already frozen and audited in the heterogeneous environment runs.

`cache` builds per-panel features and verified labels; `screen` trains the
specialists and reports the preconditions.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from wide_candidate_reranker_development import features


SOURCE = ROOT / 'runs/heterogeneous-ast-environment-20260920'
CACHE = ROOT / 'analysis/rule-identity-cache-20260920'
MODELS = ROOT / 'analysis/rule-identity-models-20260920'
OUT = ROOT / 'analysis/rule-identity-environment-20260920.json'
PANELS = ('beta_dev', 'beta_transfer', 'balanced_control')
TRAIN = 'beta_dev'
WIDTH = 100
THRESHOLD = 20
RULES = ((2, 13, 7, 9, 4), (5, 1, 3, 7, 2), (7, 11, 6, 5, 1), (9, 7, 8, 5, 3))


def rule_name(parameters):
    return f'rule{RULES.index(tuple(parameters))}'


def cache(panel):
    tasks = json.loads((SOURCE / f'{panel}_bank.json').read_text())
    base = json.loads((SOURCE / f'{panel}_base_pools.json').read_text())
    wide = json.loads((SOURCE / f'{panel}_wide_pools.json').read_text())
    records = json.loads((SOURCE / f'{panel}_records.json').read_text())
    xs = []
    meta = []
    offset = 0
    for task, record in zip(tasks, records):
        if task['domain'] != 'shifted':
            continue
        pool = wide.get(task['id'], base[task['id']])
        old = record['orders']['old']
        head = old[:min(WIDTH, len(old))]
        x = features(task, pool, record, len(head))
        labels = [int(bool(evaluate_program(pool[i]['program'],
                                            task['hidden'][8:]))) for i in head]
        e0 = record['orders']['e0'][0]
        e0_label = (labels[head.index(e0)] if e0 in head
                    else int(bool(evaluate_program(pool[e0]['program'],
                                                   task['hidden'][8:]))))
        xs.append(x)
        meta.append({'seed': record['seed'], 'start': offset, 'count': len(head),
                     'rule': rule_name(task['reference']['parameters']),
                     'labels': labels, 'e0_label': e0_label,
                     'reachable': int(any(labels))})
        offset += len(head)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE / f'{panel}.npz', x=np.concatenate(xs))
    write_json(CACHE / f'{panel}.json', {'panel': panel, 'tasks': meta})
    print('cached', panel, len(meta), 'shifted tasks', flush=True)


def load(panel):
    x = np.load(CACHE / f'{panel}.npz')['x']
    meta = json.loads((CACHE / f'{panel}.json').read_text())['tasks']
    return x, meta


def rows_of(x, meta, keep=None):
    xs = []
    ys = []
    for task in meta:
        if keep and task['rule'] != keep:
            continue
        xs.append(x[task['start']:task['start'] + task['count']])
        ys.append(np.asarray(task['labels'], np.int8))
    return np.concatenate(xs), np.concatenate(ys)


def evaluate_panel(panel, models):
    x, meta = load(panel)
    scored = {name: model.predict_proba(x)[:, 1] for name, model in models.items()}
    rows = []
    for task in meta:
        start, count = task['start'], task['count']
        entry = {'seed': task['seed'], 'rule': task['rule'],
                 'reachable': task['reachable'],
                 'labels': {'e0': task['e0_label']}, 'confidence': {}}
        for name, probabilities in scored.items():
            window = probabilities[start:start + count]
            pick = max(range(count), key=lambda i: (float(window[i]), -i))
            entry['labels'][name] = task['labels'][pick]
            entry['confidence'][name] = float(window[pick])
        rows.append(entry)
    return rows


def totals(rows, choose):
    banks = defaultdict(int)
    for row in rows:
        banks[row['seed']] += row['labels'][choose(row)]
    return [banks[s] for s in sorted(banks)]


def compare(left, right):
    diffs = [a - b for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def screen():
    if OUT.exists():
        raise RuntimeError('screen exists')
    x, meta = load(TRAIN)
    names = [f'rule{i}' for i in range(len(RULES))]
    models = {}
    for name in names:
        rx, ry = rows_of(x, meta, keep=name)
        models[name] = model_for(15).fit(rx, ry)
    px, py = rows_of(x, meta)
    models['pooled'] = model_for(15).fit(px, py)
    MODELS.mkdir(parents=True, exist_ok=True)
    for name, model in models.items():
        joblib.dump(model, MODELS / f'{name}.joblib', compress=3)

    actions = names + ['pooled', 'e0']
    result = {'scope': 'four-precondition screen of the rule-identity '
                       'environment, on frozen audited shifted tasks',
              'why': 'all four shifted rules present in Unicode block 0x800, so '
                     'no public region-matching rule can exist',
              'train_panel': TRAIN, 'rules': len(RULES), 'threshold': THRESHOLD,
              'panels': {}}

    for panel in PANELS:
        if panel == TRAIN:
            continue
        rows = evaluate_panel(panel, models)
        own = totals(rows, lambda r: r['rule'])
        pooled = totals(rows, lambda r: 'pooled')
        confident = totals(
            rows, lambda r: max(models, key=lambda a: (r['confidence'][a], a)))
        oracle = totals(rows, lambda r: max(actions,
                                            key=lambda a: r['labels'][a]))
        best_single = max(actions, key=lambda a: sum(r['labels'][a] for r in rows))
        constant = totals(rows, lambda r, a=best_single: a)
        defaults = {'pooled': pooled, 'most_confident': confident,
                    'best_constant': constant}
        best_default_name = max(defaults, key=lambda k: sum(defaults[k]))
        best_default = defaults[best_default_name]

        result['panels'][panel] = {
            'tasks': len(rows), 'reachable': sum(r['reachable'] for r in rows),
            'own_rule_oracle_routing': sum(own),
            'pooled': sum(pooled), 'most_confident': sum(confident),
            'best_constant': sum(constant), 'best_constant_action': best_single,
            'oracle': sum(oracle),
            'best_default': best_default_name,
            'best_default_total': sum(best_default),
            'default_regret': sum(oracle) - sum(best_default),
            'p2c_passed': bool(sum(oracle) - sum(best_default) > THRESHOLD),
            'own_rule_minus_default': compare(own, best_default)}
        value = result['panels'][panel]
        print(f'{panel}: pooled={value["pooled"]} conf={value["most_confident"]} '
              f'const={value["best_constant"]} own_rule={value["own_rule_oracle_routing"]} '
              f'oracle={value["oracle"]}', flush=True)
        print(f'   best default = {best_default_name} '
              f'({value["best_default_total"]})  P2c regret='
              f'{value["default_regret"]} passed={value["p2c_passed"]}',
              flush=True)
        d = value['own_rule_minus_default']
        print(f'   own-rule routing - default = {d["gain"]:+d} '
              f'{d["positive_banks"]}w/{d["losing_banks"]}l {d["interval"]}',
              flush=True)

    result['verdict'] = {
        'p2c_all_panels': all(v['p2c_passed'] for v in result['panels'].values())}
    result['limits'] = [
        'Shifted tasks come from frozen, audited heterogeneous-environment '
        'panels; nothing new was generated.',
        'Own-rule routing uses the hidden rule identity and is an upper '
        'reference, not a deployable policy. P2d must show a public-feature '
        'policy can approach it.',
        'Specialists train on about 87 tasks per rule, which is small.']
    write_json(OUT, result)
    print('verdict:', result['verdict'])


if __name__ == '__main__':
    if sys.argv[1] == 'cache':
        for panel in PANELS:
            if not (CACHE / f'{panel}.npz').exists():
                cache(panel)
    else:
        screen()
