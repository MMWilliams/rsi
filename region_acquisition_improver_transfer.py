"""Frozen test of a region-acquisition improver on fresh banks.

Protocol: EXPERIMENT-region-acquisition-improver-transfer.md

Stage 1 `prepare` generates three fresh banks, their candidate pools and the
frozen E0 candidate order. Stage 2 `score` installs the region specialists each
parent and child improver selected, opens the final labels and reports G1, G2
and G3. Nothing in stage 2 can change stage 1's frozen artifacts.
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
from region_specialist_repayment_development import (
    MODELS as SPECIALISTS, REGIONS, WIDTH,
    TARGET as OPENED_PANELS, load_cache)


DEST = ROOT / 'runs/region-acquisition-improver-transfer-20260920'
PROTOCOL = ROOT / 'EXPERIMENT-region-acquisition-improver-transfer.md'
SCRIPT = ROOT / 'region_acquisition_improver_transfer.py'
E0 = ROOT / 'runs/candidate-reranker-transfer-20260918/e0.joblib'
BANKS = {'admission': tuple(range(907100, 907106)),
         'transfer_b': tuple(range(907200, 907212)),
         'transfer_c': tuple(range(907300, 907312))}
BUDGET = 3
INITIAL_PANEL = 'candidate-query-cost-transfer-20260918'
PARENTS = ('initial', 'later', 'duplicate', 'scrambled', 'empty')
FIXED_POLICIES = ('largest_pool', 'all_six', 'e0')
SCRAMBLE_SEED = 907001


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- improver ---

def opened_repayment():
    """Per-panel, per-region repayment the parents may inherit."""
    source = json.loads((ROOT / 'analysis'
                         / 'region-specialist-repayment-development-20260920.json'
                         ).read_text())
    return {panel: {region: value['own_region_repayment'][region]['gain']
                    for region in REGIONS}
            for panel, value in source['panels'].items()}


def inherited_records():
    """Records each parent carries into the transfer, before any fresh bank."""
    opened = opened_repayment()
    initial = [opened[INITIAL_PANEL]]
    later = [opened[name] for name in OPENED_PANELS]
    rng = np.random.default_rng(SCRAMBLE_SEED)
    scrambled = []
    for panel in later:
        values = rng.permutation([panel[region] for region in REGIONS])
        scrambled.append(dict(zip(REGIONS, (int(v) for v in values))))
    return {'initial': initial, 'later': later,
            'duplicate': initial * len(later), 'scrambled': scrambled,
            'empty': []}


def select(records, pool_size, budget=BUDGET):
    """The one selection rule every parent and child shares."""
    if not records:
        ranked = sorted(REGIONS, key=lambda r: (-pool_size[r], r))
        return tuple(sorted(ranked[:budget]))
    mean = {region: float(np.mean([panel[region] for panel in records]))
            for region in REGIONS}
    ranked = sorted(REGIONS, key=lambda r: (-mean[r], r))
    return tuple(sorted(ranked[:budget]))


# -------------------------------------------------------------------- prep ---

def build_bank(seeds):
    return [{**task, 'seed': seed} for seed in seeds
            for task in random_bank(seed, 48, FAMILIES, visible=1, hidden=23)]


def prepare():
    if (DEST / 'bank_manifest.json').exists():
        raise RuntimeError('already prepared')
    start = time.perf_counter()
    DEST.mkdir(parents=True, exist_ok=True)
    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(E0)
    manifest = {'protocol_sha256': sha(PROTOCOL), 'runner_sha256': sha(SCRIPT),
                'e0_sha256': sha(E0), 'budget': BUDGET, 'width': WIDTH,
                'specialist_sha256': {region: sha(SPECIALISTS / f'{region}.joblib')
                                      for region in REGIONS},
                'banks': {}}
    for name, seeds in BANKS.items():
        tasks = build_bank(seeds)
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
            assert len(record['orders']['e0']) == len(pool)
            assert len(set(record['orders']['e0'])) == len(pool)
            rescored += len(x)
            records.append(record)
        write_json(DEST / f'{name}_bank.json', tasks)
        write_json(DEST / f'{name}_base_pools.json', base)
        write_json(DEST / f'{name}_wide_pools.json', wide)
        write_json(DEST / f'{name}_records.json', records)
        manifest['banks'][name] = {
            'seeds': list(seeds), 'tasks': len(tasks),
            'base_candidates': sum(len(v) for v in base.values()),
            'extra_ast_candidates': sum(len(v) - len(base[k])
                                        for k, v in wide.items()),
            'candidates_rescored': rescored,
            'generation_seconds': sum(times.values()),
            'records_sha256': sha(DEST / f'{name}_records.json')}
        print('prepared', name, manifest['banks'][name]['tasks'], flush=True)
    manifest['preparation_wall_seconds'] = time.perf_counter() - start
    write_json(DEST / 'bank_manifest.json', manifest)
    print(json.dumps({'status': 'banks frozen', **manifest}, indent=2))


# ------------------------------------------------------------------ scoring ---

def choices_for(name):
    """Zero-query top choice and its verified label, per task, per specialist."""
    tasks = json.loads((DEST / f'{name}_bank.json').read_text())
    base = json.loads((DEST / f'{name}_base_pools.json').read_text())
    wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
    records = json.loads((DEST / f'{name}_records.json').read_text())
    models = {region: joblib.load(SPECIALISTS / f'{region}.joblib')
              for region in REGIONS}
    rows = []
    labels_checked = 0
    for task, record in zip(tasks, records):
        pool = wide.get(task['id'], base[task['id']])
        old = record['orders']['old']
        head = old[:min(WIDTH, len(old))]
        x = features(task, pool, record, len(head))
        verified = [int(bool(evaluate_program(pool[i]['program'],
                                              task['hidden'][8:]))) for i in head]
        labels_checked += len(verified)
        e0_index = record['orders']['e0'][0]
        e0_label = (verified[head.index(e0_index)] if e0_index in head
                    else int(bool(evaluate_program(pool[e0_index]['program'],
                                                   task['hidden'][8:]))))
        picks = {'e0': e0_label}
        for region, model in models.items():
            p = model.predict_proba(x)[:, 1]
            picks[region] = verified[max(range(len(head)),
                                         key=lambda i: (float(p[i]), -i))]
        rows.append({'seed': record['seed'], 'region': task['family'],
                     'reachable_head': int(any(verified)),
                     'pool': len(pool), 'labels': picks})
    return rows, labels_checked


def apply_policy(rows, installed):
    """A system routes a task to its region specialist only if that region was
    bought; otherwise the frozen E0 order stands."""
    banks = defaultdict(int)
    for row in rows:
        key = row['region'] if row['region'] in installed else 'e0'
        banks[row['seed']] += row['labels'][key]
    return banks


def compare(rows, left, right):
    a = apply_policy(rows, left)
    b = apply_policy(rows, right)
    diffs = [a[seed] - b[seed] for seed in sorted(a)]
    return {'left': sum(a.values()), 'right': sum(b.values()),
            'gain': sum(diffs), 'banks': len(diffs),
            'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def realized(rows, region):
    """Repayment a region's specialist actually earned on this fresh bank."""
    banks = defaultdict(lambda: [0, 0])
    for row in rows:
        if row['region'] != region:
            continue
        pair = banks[row['seed']]
        pair[0] += row['labels'][region]
        pair[1] += row['labels']['e0']
    return sum(a - b for a, b in banks.values())


def component_gate(result):
    """G1 as predeclared: positive total gain with a positive interval bound."""
    return bool(result['gain'] > 0 and result['interval'][0] > 0)


def growth_gate(result):
    """G2 and G3 as predeclared."""
    return bool(result['gain'] >= 6
                and result['losing_banks'] <= 4
                and result['interval'][0] > 0)


def best_set(rows, budget=BUDGET):
    from itertools import combinations
    return max(combinations(sorted(REGIONS), budget),
               key=lambda combo: sum(apply_policy(rows, combo).values()))


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    manifest = json.loads((DEST / 'bank_manifest.json').read_text())
    assert manifest['protocol_sha256'] == sha(PROTOCOL)
    assert all(manifest['specialist_sha256'][region]
               == sha(SPECIALISTS / f'{region}.joblib') for region in REGIONS)
    for name in BANKS:
        assert manifest['banks'][name]['records_sha256'] \
            == sha(DEST / f'{name}_records.json')

    scored = {}
    labels_checked = 0
    for name in BANKS:
        rows, checked = choices_for(name)
        scored[name] = rows
        labels_checked += checked
        print('scored', name, len(rows), flush=True)

    pool_size = {region: float(np.mean([r['pool'] for r in scored['transfer_b']
                                        if r['region'] == region]))
                 for region in REGIONS}
    records = inherited_records()
    parents = {name: select(records[name], pool_size) for name in PARENTS}

    admission = {region: realized(scored['admission'], region)
                 for region in REGIONS}
    children = {name: select(records[name] + [admission], pool_size)
                for name in PARENTS}

    fixed = {'largest_pool': tuple(sorted(sorted(
                 REGIONS, key=lambda r: (-pool_size[r], r))[:BUDGET])),
             'all_six': tuple(sorted(REGIONS)),
             'e0': ()}
    oracle_b = best_set(scored['transfer_b'])
    oracle_c = best_set(scored['transfer_c'])

    totals = {
        'transfer_b': {**{f'parent_{k}': sum(apply_policy(
                              scored['transfer_b'], v).values())
                          for k, v in parents.items()},
                       **{k: sum(apply_policy(scored['transfer_b'], v).values())
                          for k, v in fixed.items()},
                       'oracle_b3': sum(apply_policy(
                           scored['transfer_b'], oracle_b).values())},
        'transfer_c': {**{f'child_{k}': sum(apply_policy(
                              scored['transfer_c'], v).values())
                          for k, v in children.items()},
                       **{k: sum(apply_policy(scored['transfer_c'], v).values())
                          for k, v in fixed.items()},
                       'oracle_b3': sum(apply_policy(
                           scored['transfer_c'], oracle_c).values())}}

    g1 = compare(scored['transfer_b'], parents['later'], ())
    g2 = compare(scored['transfer_b'], parents['later'], parents['initial'])
    g2_dup = compare(scored['transfer_b'], parents['later'], parents['duplicate'])
    g3 = compare(scored['transfer_c'], children['later'], children['initial'])
    g3_dup = compare(scored['transfer_c'], children['later'],
                     children['duplicate'])

    result = {
        'scope': 'frozen fresh-bank region-acquisition improver transfer',
        'protocol_sha256': manifest['protocol_sha256'],
        'runner_sha256': manifest['runner_sha256'],
        'budget': BUDGET,
        'selections': {'parents': {k: list(v) for k, v in parents.items()},
                       'children': {k: list(v) for k, v in children.items()},
                       'fixed': {k: list(v) for k, v in fixed.items()},
                       'oracle_transfer_b': list(oracle_b),
                       'oracle_transfer_c': list(oracle_c)},
        'inherited_panels': {k: len(v) for k, v in records.items()},
        'admission_observation': admission,
        'realized_repayment': {
            name: {region: realized(scored[name], region) for region in REGIONS}
            for name in BANKS},
        'reachable_head': {name: sum(r['reachable_head'] for r in scored[name])
                           for name in BANKS},
        'totals': totals,
        'gates': {
            'g1_evaluator_component': {**g1, 'passed': component_gate(g1)},
            'g2_improver_growth': {
                'later_minus_initial': g2,
                'later_minus_duplicate': g2_dup,
                'passed': bool(growth_gate(g2) and g2_dup['gain'] >= 0)},
            'g3_recursive_child_growth': {
                'later_minus_initial': g3,
                'later_minus_duplicate': g3_dup,
                'passed': bool(growth_gate(g3) and g3_dup['gain'] >= 0)}},
        'cost': {'acquisition_units_per_parent': BUDGET,
                 'candidate_labels_checked': labels_checked,
                 'candidates_rescored': {
                     name: manifest['banks'][name]['candidates_rescored']
                     for name in BANKS},
                 'preparation_wall_seconds':
                     manifest['preparation_wall_seconds']},
        'limits': [
            'One synthetic string/program benchmark.',
            'Specialists share E0 pools and candidate order; ranking only.',
            'Budget 3 was chosen on opened development data so the arms differ.']}
    write_json(DEST / 'results.json', result)
    print(json.dumps({k: v for k, v in result.items()
                      if k in ('selections', 'totals', 'gates',
                               'realized_repayment', 'admission_observation')},
                     indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
