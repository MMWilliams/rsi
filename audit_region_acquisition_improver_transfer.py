"""Independent audit of the region-acquisition improver transfer.

Regenerates every bank from its seeds, rebuilds the candidate pools, recomputes
both candidate orders, rechecks every final candidate label, and reconstructs
each parent and child selection from the inherited records alone. Totals and
gates are recomputed here rather than read from the run, then compared with
`results.json`.

This module deliberately does not import the runner's scoring, selection or gate
helpers; it re-derives them so a bug in the runner cannot be reproduced.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from itertools import combinations

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


DEST = ROOT / 'runs/region-acquisition-improver-transfer-20260920'
PROTOCOL = ROOT / 'EXPERIMENT-region-acquisition-improver-transfer.md'
RUNNER = ROOT / 'region_acquisition_improver_transfer.py'
DEVELOPMENT = (ROOT / 'analysis'
               / 'region-specialist-repayment-development-20260920.json')
SPECIALISTS = ROOT / 'analysis/region-specialist-models-20260920'
E0 = ROOT / 'runs/candidate-reranker-transfer-20260918/e0.joblib'
OUT = DEST / 'audit.json'
REGIONS = ('transform_transition', 'ast_transition', 'novel_operator_transition',
           'stack_transition', 'mutation_transition', 'self_edit_transition')
INITIAL_PANEL = 'candidate-query-cost-transfer-20260918'
LATER_PANELS = ('candidate-query-cost-transfer-20260918',
                'combined-ranker-query-transfer-20260918',
                'candidate-conditioned-query-transfer-20260918')
WIDTH = 100
BUDGET = 3
SCRAMBLE_SEED = 907001


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebuild_bank(name, manifest, failures):
    """Regenerate one bank, its pools, orders and verified labels from scratch."""
    spec = manifest['banks'][name]
    tasks = [{**task, 'seed': seed} for seed in spec['seeds']
             for task in random_bank(seed, 48, FAMILIES, visible=1, hidden=23)]
    sealed = json.loads((DEST / f'{name}_bank.json').read_text())
    if [t['id'] for t in tasks] != [t['id'] for t in sealed]:
        failures.append(f'{name}: regenerated task ids differ')
    if len(tasks) != spec['tasks']:
        failures.append(f'{name}: task count {len(tasks)} != {spec["tasks"]}')

    base, wide, _ = pools_for(tasks)
    stored_base = json.loads((DEST / f'{name}_base_pools.json').read_text())
    stored_wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
    records = json.loads((DEST / f'{name}_records.json').read_text())

    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(E0)
    models = {region: joblib.load(SPECIALISTS / f'{region}.joblib')
              for region in REGIONS}

    rows = []
    labels_checked = 0
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
        if block != record['public_block']:
            failures.append(f'{name}/{key}: public block differs')
        ranker = replay if block == BLOCK_AST else evaluators[FIXED[block]]
        scores, old_order = rank(task, pool, ranker)
        if old_order != record['orders']['old']:
            failures.append(f'{name}/{key}: old order differs')
        if not np.allclose(np.asarray(scores, float),
                           np.asarray(record['old_scores'], float), atol=1e-9):
            failures.append(f'{name}/{key}: old scores differ')

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
        labels_checked += len(verified)
        e0_index = e0_order[0]
        e0_label = (verified[head.index(e0_index)] if e0_index in head
                    else int(bool(evaluate_program(pool[e0_index]['program'],
                                                   task['hidden'][8:]))))
        picks = {'e0': e0_label}
        for region, model in models.items():
            p = model.predict_proba(x)[:, 1]
            picks[region] = verified[max(range(len(head)),
                                         key=lambda i: (float(p[i]), -i))]
        rows.append({'seed': task['seed'], 'region': task['family'],
                     'reachable_head': int(any(verified)), 'pool': len(pool),
                     'labels': picks})
    return rows, labels_checked


def totals_for(rows, installed):
    banks = defaultdict(int)
    for row in rows:
        key = row['region'] if row['region'] in installed else 'e0'
        banks[row['seed']] += row['labels'][key]
    return banks


def compare(rows, left, right):
    a = totals_for(rows, left)
    b = totals_for(rows, right)
    diffs = [a[seed] - b[seed] for seed in sorted(a)]
    return {'left': sum(a.values()), 'right': sum(b.values()),
            'gain': sum(diffs), 'banks': len(diffs),
            'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def realized(rows, region):
    banks = defaultdict(lambda: [0, 0])
    for row in rows:
        if row['region'] != region:
            continue
        pair = banks[row['seed']]
        pair[0] += row['labels'][region]
        pair[1] += row['labels']['e0']
    return sum(a - b for a, b in banks.values())


def rebuild_records():
    """Rebuild what each parent inherits, straight from the development file."""
    panels = json.loads(DEVELOPMENT.read_text())['panels']
    table = {name: {region: panels[name]['own_region_repayment'][region]['gain']
                    for region in REGIONS} for name in LATER_PANELS}
    initial = [table[INITIAL_PANEL]]
    later = [table[name] for name in LATER_PANELS]
    rng = np.random.default_rng(SCRAMBLE_SEED)
    scrambled = []
    for panel in later:
        values = rng.permutation([panel[region] for region in REGIONS])
        scrambled.append(dict(zip(REGIONS, (int(v) for v in values))))
    return {'initial': initial, 'later': later,
            'duplicate': initial * len(later), 'scrambled': scrambled,
            'empty': []}


def rebuild_select(records, pool_size):
    if not records:
        return tuple(sorted(sorted(REGIONS,
                                   key=lambda r: (-pool_size[r], r))[:BUDGET]))
    mean = {region: float(np.mean([panel[region] for panel in records]))
            for region in REGIONS}
    return tuple(sorted(sorted(REGIONS,
                               key=lambda r: (-mean[r], r))[:BUDGET]))


def rebuild_one(name):
    """Rebuild a single bank in its own process and cache the rows.

    Commit, not physical RAM, is the binding constraint on this machine, and
    CPython does not return freed arena space to the OS. Auditing each bank in a
    fresh process keeps peak commit to one bank's worth.
    """
    failures = []
    manifest = json.loads((DEST / 'bank_manifest.json').read_text())
    rows, checked = rebuild_bank(name, manifest, failures)
    write_json(DEST / f'audit_rows_{name}.json',
               {'bank': name, 'rows': rows, 'labels_checked': checked,
                'failures': failures})
    print('rebuilt', name, len(rows), checked, 'failures', len(failures))


def main():
    failures = []
    manifest = json.loads((DEST / 'bank_manifest.json').read_text())
    results = json.loads((DEST / 'results.json').read_text())

    if manifest['protocol_sha256'] != sha(PROTOCOL):
        failures.append('protocol hash differs from the frozen manifest')
    if results['protocol_sha256'] != manifest['protocol_sha256']:
        failures.append('results protocol hash differs from the manifest')
    for region in REGIONS:
        if manifest['specialist_sha256'][region] != sha(
                SPECIALISTS / f'{region}.joblib'):
            failures.append(f'specialist {region} changed after freezing')
    for name in manifest['banks']:
        if manifest['banks'][name]['records_sha256'] != sha(
                DEST / f'{name}_records.json'):
            failures.append(f'{name}: frozen records changed after freezing')

    scored = {}
    labels_checked = 0
    for name in manifest['banks']:
        cached = DEST / f'audit_rows_{name}.json'
        if not cached.exists():
            raise RuntimeError(f'run "{name}" first to rebuild that bank')
        part = json.loads(cached.read_text())
        scored[name] = part['rows']
        labels_checked += part['labels_checked']
        failures.extend(part['failures'])

    pool_size = {region: float(np.mean([r['pool'] for r in scored['transfer_b']
                                        if r['region'] == region]))
                 for region in REGIONS}
    records = rebuild_records()
    parents = {name: rebuild_select(records[name], pool_size) for name in records}
    admission = {region: realized(scored['admission'], region)
                 for region in REGIONS}
    children = {name: rebuild_select(records[name] + [admission], pool_size)
                for name in records}

    for label, rebuilt in (('parents', parents), ('children', children)):
        for name, value in rebuilt.items():
            recorded = tuple(results['selections'][label][name])
            if value != recorded:
                failures.append(
                    f'{label}/{name}: reconstructed {value} != recorded {recorded}')
    if admission != results['admission_observation']:
        failures.append('admission observation differs')

    fixed = {'largest_pool': tuple(sorted(sorted(
                 REGIONS, key=lambda r: (-pool_size[r], r))[:BUDGET])),
             'all_six': tuple(sorted(REGIONS)), 'e0': ()}
    oracle = {name: max(combinations(sorted(REGIONS), BUDGET),
                        key=lambda c: sum(totals_for(scored[name], c).values()))
              for name in ('transfer_b', 'transfer_c')}

    rebuilt_totals = {
        'transfer_b': {**{f'parent_{k}': sum(totals_for(
                              scored['transfer_b'], v).values())
                          for k, v in parents.items()},
                       **{k: sum(totals_for(scored['transfer_b'], v).values())
                          for k, v in fixed.items()},
                       'oracle_b3': sum(totals_for(
                           scored['transfer_b'], oracle['transfer_b']).values())},
        'transfer_c': {**{f'child_{k}': sum(totals_for(
                              scored['transfer_c'], v).values())
                          for k, v in children.items()},
                       **{k: sum(totals_for(scored['transfer_c'], v).values())
                          for k, v in fixed.items()},
                       'oracle_b3': sum(totals_for(
                           scored['transfer_c'], oracle['transfer_c']).values())}}
    for bank, values in rebuilt_totals.items():
        for key, value in values.items():
            recorded = results['totals'][bank].get(key)
            if recorded != value:
                failures.append(
                    f'total {bank}/{key}: rebuilt {value} != recorded {recorded}')

    g1 = compare(scored['transfer_b'], parents['later'], ())
    g2 = compare(scored['transfer_b'], parents['later'], parents['initial'])
    g2_dup = compare(scored['transfer_b'], parents['later'], parents['duplicate'])
    g3 = compare(scored['transfer_c'], children['later'], children['initial'])
    g3_dup = compare(scored['transfer_c'], children['later'],
                     children['duplicate'])
    rebuilt_gates = {
        'g1_evaluator_component': {
            **g1, 'passed': bool(g1['gain'] > 0 and g1['interval'][0] > 0)},
        'g2_improver_growth': {
            'later_minus_initial': g2, 'later_minus_duplicate': g2_dup,
            'passed': bool(g2['gain'] >= 6 and g2['losing_banks'] <= 4
                           and g2['interval'][0] > 0 and g2_dup['gain'] >= 0)},
        'g3_recursive_child_growth': {
            'later_minus_initial': g3, 'later_minus_duplicate': g3_dup,
            'passed': bool(g3['gain'] >= 6 and g3['losing_banks'] <= 4
                           and g3['interval'][0] > 0 and g3_dup['gain'] >= 0)}}
    for name, value in rebuilt_gates.items():
        if json.loads(json.dumps(value)) != results['gates'][name]:
            failures.append(f'gate {name} differs from the recorded run')

    if labels_checked != results['cost']['candidate_labels_checked']:
        failures.append('candidate label count differs')

    audit = {'scope': 'independent reconstruction of the region-acquisition '
                      'improver transfer',
             'runner_sha256': sha(RUNNER),
             'auditor_sha256': sha(ROOT / 'audit_region_acquisition_improver_'
                                          'transfer.py'),
             'protocol_sha256': sha(PROTOCOL),
             'tasks_rebuilt': sum(len(rows) for rows in scored.values()),
             'candidate_labels_rechecked': labels_checked,
             'selections_reconstructed': {
                 'parents': {k: list(v) for k, v in parents.items()},
                 'children': {k: list(v) for k, v in children.items()}},
             'totals_rebuilt': rebuilt_totals,
             'gates_rebuilt': rebuilt_gates,
             'failures': failures,
             'passed': not failures}
    write_json(OUT, audit)
    print(json.dumps({'passed': audit['passed'],
                      'tasks_rebuilt': audit['tasks_rebuilt'],
                      'candidate_labels_rechecked': labels_checked,
                      'failures': failures[:20]}, indent=2))


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        rebuild_one(sys.argv[1])
    else:
        main()
