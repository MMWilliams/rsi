"""Phase E: build the non-stationary bank generator and measure its fixed regret.

`MECHANISM-HETEROGENEITY-ENVIRONMENT-2026-09-20.md` simulated, by resampling
audited rows, that drawing a per-bank familiar/shifted share from Beta(0.4, 0.4)
lifts fixed regret from 2.9 to about 48 per 576 tasks. That simulation justifies
spending compute; it does not substitute for it. This module generates real
banks under that prior, runs the full pipeline, and recomputes fixed regret on
generated data.

The share is never handed to any policy. Note that the familiar and shifted
generators both emit Unicode block 0x800, so the block carries no signal here,
unlike the cross-family studies where it recovers the task family exactly. The
only public context is label-free model confidence: per task, the top-candidate
probability of the familiar reranker against that of the shifted one. A bank's
public statistic is the fraction of its tasks where the familiar reranker is the
more confident. The true domain is recorded for diagnosis and never exposed.

`prepare` freezes banks, pools and candidate orders. `score` opens final labels
and reports fixed regret, the learnable fraction and the P2b verdict.
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
from seed_casebanks import random_bank, shifted_ast_bank
from gated_ast_feedback import pools_for, public_block, BLOCK_AST, FIXED
from gated_ast_replay_integration import models as evaluator_models
from ast_feedback_replay_update import updated_model
from ast_probe_sensor_transfer import rank
from shifted_ast_seed_transfer import route_for_generation
from wide_candidate_reranker_development import features
from familiar_ast_zero_query_development import MODELS as FAMILIAR_MODELS
from shifted_zero_query_reranker_development import MODELS as SHIFTED_MODELS


DEST = ROOT / 'runs/heterogeneous-ast-environment-20260920'
SCRIPT = ROOT / 'heterogeneous_ast_environment.py'
E0 = ROOT / 'runs/candidate-reranker-transfer-20260918/e0.joblib'
ACTIONS = ('e0', 'familiar', 'shifted')
WIDTH = 100
BANK_TASKS = 48
SHARE_PRIOR = (.4, .4)
THRESHOLD = 20
# Two independent panels: a development panel the improver may observe, and a
# transfer panel it may not. Balanced is the control the prior runs all used.
PANELS = {'beta_dev': (tuple(range(908100, 908112)), 'beta', 908001),
          'beta_transfer': (tuple(range(908200, 908212)), 'beta', 908002),
          'balanced_control': (tuple(range(908300, 908312)), 'balanced', 908003)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shares_for(kind, seeds, seed):
    rng = np.random.default_rng(seed)
    if kind == 'balanced':
        return {bank: .5 for bank in seeds}
    if kind == 'beta':
        return {bank: float(rng.beta(*SHARE_PRIOR)) for bank in seeds}
    raise ValueError(kind)


def build_bank(bank_seed, share, rng):
    """One bank whose familiar/shifted composition follows `share`."""
    familiar_count = int(rng.binomial(BANK_TASKS, share))
    shifted_count = BANK_TASKS - familiar_count
    tasks = []
    if familiar_count:
        tasks += [{**t, 'domain': 'familiar'} for t in
                  random_bank(bank_seed, familiar_count, ('ast_transition',),
                              visible=1, hidden=23)]
    if shifted_count:
        tasks += [{**t, 'domain': 'shifted'} for t in
                  shifted_ast_bank(bank_seed + 50000, shifted_count,
                                   visible=1, hidden=23)]
    return [{**t, 'seed': bank_seed} for t in tasks]


def prepare():
    if (DEST / 'manifest.json').exists():
        raise RuntimeError('already prepared')
    DEST.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    evaluators = evaluator_models()
    replay = updated_model()
    e0 = joblib.load(E0)
    manifest = {'runner_sha256': sha(SCRIPT), 'e0_sha256': sha(E0),
                'width': WIDTH, 'bank_tasks': BANK_TASKS,
                'share_prior': list(SHARE_PRIOR), 'panels': {}}
    for name, (seeds, kind, prior_seed) in PANELS.items():
        shares = shares_for(kind, seeds, prior_seed)
        rng = np.random.default_rng(prior_seed + 7)
        tasks = []
        for bank_seed in seeds:
            tasks.extend(build_bank(bank_seed, shares[bank_seed], rng))
        # Shifted tasks carry family 'shifted_ast', which the generator's arm
        # map does not know; every shifted study routes them onto the AST arms.
        base, wide, times = pools_for(route_for_generation(tasks))
        records = []
        rescored = 0
        for task in tasks:
            key = task['id']
            block = public_block(task)
            pool = wide.get(key, base[key])
            ranker = replay if block == BLOCK_AST else evaluators[FIXED[block]]
            scores, old_order = rank(task, pool, ranker)
            record = {'id': key, 'seed': task['seed'], 'domain': task['domain'],
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
            'seeds': list(seeds), 'kind': kind, 'tasks': len(tasks),
            'intended_shares': {str(k): v for k, v in shares.items()},
            'realized_familiar': sum(t['domain'] == 'familiar' for t in tasks),
            'candidates_rescored': rescored,
            'generation_seconds': sum(times.values()),
            'records_sha256': sha(DEST / f'{name}_records.json')}
        print('prepared', name, len(tasks),
              'familiar', manifest['panels'][name]['realized_familiar'],
              flush=True)
    manifest['preparation_wall_seconds'] = time.perf_counter() - start
    write_json(DEST / 'manifest.json', manifest)
    print(json.dumps({'status': 'panels frozen', **manifest['panels']}, indent=2))


def action_models():
    return {'familiar': joblib.load(FAMILIAR_MODELS / 'early.joblib'),
            'shifted': joblib.load(SHIFTED_MODELS / 'ab_top100.joblib')}


def rows_for(name):
    """Verified label of every action's top choice, per task."""
    tasks = json.loads((DEST / f'{name}_bank.json').read_text())
    base = json.loads((DEST / f'{name}_base_pools.json').read_text())
    wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
    records = json.loads((DEST / f'{name}_records.json').read_text())
    models = action_models()
    rows = []
    checked = 0
    for task, record in zip(tasks, records):
        pool = wide.get(task['id'], base[task['id']])
        old = record['orders']['old']
        head = old[:min(WIDTH, len(old))]
        x = features(task, pool, record, len(head))
        verified = [int(bool(evaluate_program(pool[i]['program'],
                                              task['hidden'][8:]))) for i in head]
        checked += len(verified)
        e0_index = record['orders']['e0'][0]
        labels = {'e0': (verified[head.index(e0_index)] if e0_index in head
                         else int(bool(evaluate_program(pool[e0_index]['program'],
                                                        task['hidden'][8:]))))}
        confidence = {}
        for action, model in models.items():
            p = model.predict_proba(x)[:, 1]
            pick = max(range(len(head)), key=lambda i: (float(p[i]), -i))
            labels[action] = verified[pick]
            confidence[action] = float(p[pick])
        rows.append({'seed': record['seed'], 'domain': task['domain'],
                     'public_block': record['public_block'],
                     'reachable_head': int(any(verified)), 'labels': labels,
                     'confidence': confidence})
    return rows, checked


def regret(rows):
    """Fixed regret and the learnable fraction, on generated banks."""
    banks = defaultdict(lambda: defaultdict(int))
    leaning = defaultdict(list)
    truth = defaultdict(list)
    for row in rows:
        for action in ACTIONS:
            banks[row['seed']][action] += row['labels'][action]
        leaning[row['seed']].append(
            row['confidence']['familiar'] >= row['confidence']['shifted'])
        truth[row['seed']].append(row['domain'] == 'familiar')
    seeds = sorted(banks)
    gain = np.array([[banks[s][a] - banks[s]['e0'] for a in ACTIONS]
                     for s in seeds])
    best_constant_index = int(gain.sum(axis=0).argmax())
    best_constant = int(gain.sum(axis=0)[best_constant_index])
    hindsight = int(gain.max(axis=1).sum())

    # Public context. The familiar and shifted generators share Unicode block
    # 0x800, so the block carries no signal. The label-free statistic the
    # dual-specialist route already used is model confidence: the fraction of a
    # bank's tasks where the familiar reranker is more confident than the
    # shifted one. `true_familiar_share` is recorded for diagnosis only and is
    # never available to a policy.
    share = np.array([float(np.mean(leaning[s])) for s in seeds])
    true_share = np.array([float(np.mean(truth[s])) for s in seeds])
    contextual = 0
    for held in range(len(seeds)):
        rest = [i for i in range(len(seeds)) if i != held]
        neighbour = rest[int(np.abs(share[rest] - share[held]).argmin())]
        contextual += int(gain[held, int(gain[neighbour].argmax())])

    return {'banks': len(seeds),
            'public_confidence_share': [float(v) for v in share],
            'true_familiar_share': [float(v) for v in true_share],
            'share_correlation': float(np.corrcoef(share, true_share)[0, 1])
                                 if share.std() > 0 else 0.,
            'per_bank_gain': {str(s): dict(zip(ACTIONS, map(int, g)))
                              for s, g in zip(seeds, gain)},
            'best_constant_action': ACTIONS[best_constant_index],
            'best_constant': best_constant,
            'hindsight': hindsight,
            'fixed_regret': hindsight - best_constant,
            'contextual_nearest_share': contextual,
            'contextual_minus_constant': contextual - best_constant,
            'distinct_optima': len(set(gain.argmax(axis=1).tolist()))}


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    manifest = json.loads((DEST / 'manifest.json').read_text())
    for name in PANELS:
        assert manifest['panels'][name]['records_sha256'] \
            == sha(DEST / f'{name}_records.json')
    panels = {}
    checked_total = 0
    for name in PANELS:
        rows, checked = rows_for(name)
        checked_total += checked
        write_json(DEST / f'rows_{name}.json', {'panel': name, 'rows': rows})
        panels[name] = {
            'tasks': len(rows),
            'familiar_tasks': sum(r['domain'] == 'familiar' for r in rows),
            'reachable_head': sum(r['reachable_head'] for r in rows),
            'totals': {a: sum(r['labels'][a] for r in rows) for a in ACTIONS},
            **regret(rows)}
        value = panels[name]
        print(f'{name:18s} fixed_regret={value["fixed_regret"]:+4d} '
              f'contextual-constant={value["contextual_minus_constant"]:+4d} '
              f'best_constant={value["best_constant"]:+4d} '
              f'({value["best_constant_action"]})', flush=True)

    verdict = {name: bool(value['fixed_regret'] > THRESHOLD)
               for name, value in panels.items()}
    result = {
        'scope': 'Phase E: fixed regret measured on generated, not resampled, '
                 'banks',
        'runner_sha256': manifest['runner_sha256'],
        'threshold': THRESHOLD,
        'candidate_labels_checked': checked_total,
        'panels': panels,
        'verdict': verdict,
        'p2b_satisfied': bool(verdict['beta_dev'] and verdict['beta_transfer']
                              and not verdict['balanced_control']),
        'limits': [
            'The familiar share is observable only through public Unicode '
            'blocks, which the benchmark already exposes.',
            'Specialists are the frozen models from the 2026-09-18 runs; they '
            'were not retrained for this environment.',
            'Fixed regret bounds what any contextual policy could gain; it does '
            'not show that a parent with more history captures it.']}
    write_json(DEST / 'results.json', result)
    print(json.dumps({'verdict': verdict,
                      'p2b_satisfied': result['p2b_satisfied'],
                      'fixed_regret': {k: v['fixed_regret']
                                       for k, v in panels.items()}}, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score}[sys.argv[1]]()
