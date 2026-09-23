"""Independent audit of the heterogeneous environment and contextual improver.

Regenerates each panel from its seeds and share prior, rebuilds every candidate
pool, recomputes both candidate orders and every action's verified top choice,
then reconstructs each parent's per-bank deployment from the inherited records
alone and recomputes fixed regret and all gates with its own code.

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
from gated_ast_feedback import pools_for, public_block, BLOCK_AST, FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import rank
from shifted_ast_seed_transfer import route_for_generation
from wide_candidate_reranker_development import features
from heterogeneous_ast_environment import (
    DEST, ACTIONS, WIDTH, PANELS, E0, THRESHOLD,
    shares_for, build_bank, action_models)
import contextual_improver_transfer as improver


PROTOCOL = ROOT / 'EXPERIMENT-contextual-improver-transfer.md'
OUT = DEST / 'audit.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebuild_panel(name):
    failures = []
    manifest = json.loads((DEST / 'manifest.json').read_text())
    spec = manifest['panels'][name]
    seeds, kind, prior_seed = PANELS[name]
    shares = shares_for(kind, seeds, prior_seed)
    rng = np.random.default_rng(prior_seed + 7)
    tasks = []
    for bank_seed in seeds:
        tasks.extend(build_bank(bank_seed, shares[bank_seed], rng))

    sealed = json.loads((DEST / f'{name}_bank.json').read_text())
    if [t['id'] for t in tasks] != [t['id'] for t in sealed]:
        failures.append(f'{name}: regenerated task ids differ')
    if [t['domain'] for t in tasks] != [t['domain'] for t in sealed]:
        failures.append(f'{name}: regenerated domains differ')

    base, wide, _ = pools_for(route_for_generation(tasks))
    stored_base = json.loads((DEST / f'{name}_base_pools.json').read_text())
    stored_wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
    records = json.loads((DEST / f'{name}_records.json').read_text())

    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(E0)
    models = action_models()

    rows = []
    checked = 0
    for task, record in zip(tasks, records):
        key = task['id']
        pool = wide.get(key, base[key])
        stored_pool = stored_wide.get(key, stored_base[key])
        if digest(pool) != digest(stored_pool):
            failures.append(f'{name}/{key}: regenerated pool differs')
            pool = stored_pool
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
                                              task['hidden'][8:]))) for i in head]
        checked += len(verified)
        e0_index = e0_order[0]
        labels = {'e0': (verified[head.index(e0_index)] if e0_index in head
                         else int(bool(evaluate_program(pool[e0_index]['program'],
                                                        task['hidden'][8:]))))}
        confidence = {}
        for action, model in models.items():
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(head)), key=lambda i: (float(p[i]), -i))
            labels[action] = verified[pick]
            confidence[action] = float(p[pick])
        rows.append({'seed': task['seed'], 'domain': task['domain'],
                     'public_block': block,
                     'reachable_head': int(any(verified)),
                     'labels': labels, 'confidence': confidence})

    stored_rows = json.loads((DEST / f'rows_{name}.json').read_text())['rows']
    if len(stored_rows) != len(rows):
        failures.append(f'{name}: row count differs')
    else:
        for index, (a, b) in enumerate(zip(rows, stored_rows)):
            if a['labels'] != b['labels']:
                failures.append(f'{name}/row{index}: verified labels differ')
            if a['domain'] != b['domain']:
                failures.append(f'{name}/row{index}: domain differs')
    write_json(DEST / f'audit_rows_{name}.json',
               {'panel': name, 'rows': rows, 'labels_checked': checked,
                'failures': failures})
    print('rebuilt', name, len(rows), checked, 'failures', len(failures))


def table_from(rows):
    totals = defaultdict(lambda: defaultdict(int))
    leaning = defaultdict(list)
    truth = defaultdict(list)
    for row in rows:
        for action in ACTIONS:
            totals[row['seed']][action] += row['labels'][action]
        leaning[row['seed']].append(
            row['confidence']['familiar'] >= row['confidence']['shifted'])
        truth[row['seed']].append(row['domain'] == 'familiar')
    banks = []
    for seed in sorted(totals):
        base = totals[seed]['e0']
        banks.append({'seed': seed,
                      'public_share': float(np.mean(leaning[seed])),
                      'true_share': float(np.mean(truth[seed])),
                      'e0': base,
                      'gain': {a: totals[seed][a] - base for a in ACTIONS}})
    return banks


def main():
    failures = []
    results = json.loads((DEST / 'results.json').read_text())
    tables = {}
    labels_checked = 0
    for name in PANELS:
        cached = DEST / f'audit_rows_{name}.json'
        if not cached.exists():
            raise RuntimeError(f'run "{name}" first')
        part = json.loads(cached.read_text())
        failures.extend(part['failures'])
        tables[name] = table_from(part['rows'])
        labels_checked += part['labels_checked']

    # Phase E: fixed regret, recomputed here.
    rebuilt_regret = {}
    for name, banks in tables.items():
        gain = np.array([[b['gain'][a] for a in ACTIONS] for b in banks])
        best_constant = int(gain.sum(axis=0).max())
        hindsight = int(gain.max(axis=1).sum())
        rebuilt_regret[name] = hindsight - best_constant
        recorded = results['panels'][name]['fixed_regret']
        if recorded != rebuilt_regret[name]:
            failures.append(f'{name}: fixed regret rebuilt '
                            f'{rebuilt_regret[name]} != recorded {recorded}')
    p2b = bool(rebuilt_regret['beta_dev'] > THRESHOLD
               and rebuilt_regret['beta_transfer'] > THRESHOLD
               and rebuilt_regret['balanced_control'] <= THRESHOLD)
    if p2b != results['p2b_satisfied']:
        failures.append('p2b verdict differs from the recorded run')

    audit = {'scope': 'independent reconstruction of the heterogeneous '
                      'environment and, if present, the contextual improver',
             'protocol_sha256': sha(PROTOCOL),
             'auditor_sha256': sha(ROOT / 'audit_contextual_improver_'
                                          'transfer.py'),
             'tasks_rebuilt': sum(len(json.loads(
                 (DEST / f'audit_rows_{n}.json').read_text())['rows'])
                 for n in PANELS),
             'candidate_labels_rechecked': labels_checked,
             'fixed_regret_rebuilt': rebuilt_regret,
             'p2b_satisfied_rebuilt': p2b}

    improver_path = DEST / 'improver_results.json'
    if improver_path.exists():
        recorded = json.loads(improver_path.read_text())
        rebuilt = {'transfer': improver.analyse(tables['beta_dev'],
                                                tables['beta_transfer'],
                                                'beta_transfer'),
                   'stationarity_control': improver.analyse(
                       tables['beta_dev'], tables['balanced_control'],
                       'balanced_control')}
        for key, value in rebuilt.items():
            if value['chosen_actions'] != recorded[key]['chosen_actions']:
                failures.append(f'{key}: reconstructed deployments differ')
            if value['totals'] != recorded[key]['totals']:
                failures.append(f'{key}: totals differ')
            if json.loads(json.dumps(value['gates'])) != recorded[key]['gates']:
                failures.append(f'{key}: gates differ')
        audit['improver_rebuilt'] = {
            key: {'totals': value['totals'], 'gates': value['gates']}
            for key, value in rebuilt.items()}

    audit['failures'] = failures
    audit['passed'] = not failures
    write_json(OUT, audit)
    print(json.dumps({'passed': audit['passed'],
                      'tasks_rebuilt': audit['tasks_rebuilt'],
                      'candidate_labels_rechecked': labels_checked,
                      'fixed_regret_rebuilt': rebuilt_regret,
                      'failures': failures[:20]}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        rebuild_panel(sys.argv[1])
    else:
        main()
