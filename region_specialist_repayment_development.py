"""Opened screen of per-region candidate-specialist repayment.

Every prior improver test chose among whole-bank policies, where oracle
selection was worth only 5-8 correct tasks per 576. This screen measures a
task-level action with far more headroom: spend one fixed acquisition unit of
verified candidate labels on one public region and train a specialist reranker
for it. It reports realized repayment per region, its stability across opened
panels, and whether repayment is predictable from public region statistics.
Development evidence only; no policy is frozen here.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from wide_candidate_reranker_development import features
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval


SOURCE = ('candidate-reranker-transfer-20260918',
          'candidate-reranker-replication-20260918')
TARGET = ('candidate-query-cost-transfer-20260918',
          'combined-ranker-query-transfer-20260918',
          'candidate-conditioned-query-transfer-20260918')
OUT = ROOT / 'analysis/region-specialist-repayment-development-20260920.json'
MODELS = ROOT / 'analysis/region-specialist-models-20260920'
CACHE = ROOT / 'analysis/region-specialist-cache-20260920'
REGIONS = ('transform_transition', 'ast_transition', 'novel_operator_transition',
           'stack_transition', 'mutation_transition', 'self_edit_transition')
WIDTH = 100


def region_stats(pool, record, head):
    """Public-only summary of one task, averaged later into region statistics."""
    old = record['orders']['old']
    scores = np.asarray(record['old_scores'], float)
    std = max(float(scores.std()), .05)
    top = float(scores[old[0]])
    margin = (top - float(scores[old[1]])) / std if len(old) > 1 else 0.
    return {'pool': float(len(pool)),
            'head': float(len(head)),
            'margin': float(margin),
            'spread': float(np.mean([(top - scores[i]) / std for i in head])),
            'distinct': len({str(pool[i]['program']) for i in head}) / len(head),
            'log_pool': float(np.log1p(len(pool)))}


def lean_panel(path):
    """load_panel without the predicted-probe matrix, which zero-query ranking
    never reads. That file alone costs hundreds of megabytes of commit."""
    assert json.loads((path / 'audit.json').read_text())['passed']
    bank = json.loads((path / 'sealed_bank.json').read_text())
    base = json.loads((path / 'base_pools.json').read_text())
    wide = json.loads((path / 'ast_wide_pools.json').read_text())
    records = json.loads((path / 'frozen_records.json').read_text())
    return bank, base, wide, records


def build_cache(name):
    """Parse one opened panel once, then keep only the arrays we need."""
    path = ROOT / 'runs' / name
    bank, base, wide, records = lean_panel(path)
    xs = []
    meta = []
    offset = 0
    for task, record in zip(bank, records):
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
        meta.append({'id': task['id'], 'seed': record['seed'],
                     'region': task['family'], 'start': offset, 'count': len(head),
                     'labels': labels, 'e0_label': e0_label,
                     'stats': region_stats(pool, record, head)})
        offset += len(head)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE / f'{name}.npz', x=np.concatenate(xs))
    write_json(CACHE / f'{name}.json', {'panel': name, 'tasks': meta})


def load_cache(name):
    x = np.load(CACHE / f'{name}.npz')['x']
    meta = json.loads((CACHE / f'{name}.json').read_text())['tasks']
    return x, meta


def region_arrays(region):
    """Candidate rows and verified labels for one region's acquisition unit."""
    xs = []
    ys = []
    tasks = 0
    for name in SOURCE:
        x, meta = load_cache(name)
        for task in meta:
            if task['region'] != region:
                continue
            xs.append(x[task['start']:task['start'] + task['count']])
            ys.append(np.asarray(task['labels'], np.int8))
            tasks += 1
    return np.concatenate(xs), np.concatenate(ys), tasks


def score_panel(name, models):
    """Zero-query top choice for E0 and every trained specialist."""
    x, meta = load_cache(name)
    probs = {key: model.predict_proba(x)[:, 1] for key, model in models.items()}
    rows = []
    stats = defaultdict(list)
    for task in meta:
        start, count = task['start'], task['count']
        labels = task['labels']
        picks = {'e0': task['e0_label']}
        for key, p in probs.items():
            window = p[start:start + count]
            picks[key] = labels[max(range(count),
                                    key=lambda i: (float(window[i]), -i))]
        rows.append({'seed': task['seed'], 'region': task['region'],
                     'reachable_head': int(any(labels)), 'labels': picks})
        stats[task['region']].append(task['stats'])
    return rows, {region: {key: float(np.mean([s[key] for s in group]))
                           for key in group[0]}
                  for region, group in stats.items()}


def repayment(rows, region, name):
    """Paired per-bank gain of one specialist over E0, inside its region."""
    banks = defaultdict(lambda: {'e0': 0, 'spec': 0})
    for row in rows:
        if row['region'] != region:
            continue
        bank = banks[row['seed']]
        bank['e0'] += row['labels']['e0']
        bank['spec'] += row['labels'][name]
    diffs = [b['spec'] - b['e0'] for b in banks.values()]
    return {'tasks': sum(r['region'] == region for r in rows),
            'e0': sum(b['e0'] for b in banks.values()),
            'specialist': sum(b['spec'] for b in banks.values()),
            'gain': sum(diffs), 'banks': len(diffs),
            'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development exists')
    for name in SOURCE + TARGET:
        if not (CACHE / f'{name}.npz').exists():
            build_cache(name)
            print('cached', name, flush=True)

    models = {}
    source = {}
    for region in REGIONS:
        x, y, tasks = region_arrays(region)
        models[region] = model_for(15).fit(x, y)
        source[region] = {'tasks': tasks, 'labels': int(len(y)),
                          'positive': int(y.sum())}
        print('trained', region, source[region], flush=True)
    MODELS.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, MODELS / f'{name}.joblib', compress=3)

    panels = {}
    for name in TARGET:
        rows, stats = score_panel(name, models)
        panels[name] = {
            'tasks': len(rows),
            'reachable_head': sum(r['reachable_head'] for r in rows),
            'e0_total': sum(r['labels']['e0'] for r in rows),
            'own_region_total': sum(r['labels'][r['region']] for r in rows),
            'own_region_repayment': {region: repayment(rows, region, region)
                                     for region in REGIONS},
            'cross_region_gain': {region: {other: repayment(rows, region, other)['gain']
                                           for other in REGIONS}
                                  for region in REGIONS},
            'region_statistics': stats}
        print('scored', name, panels[name]['e0_total'],
              panels[name]['own_region_total'], flush=True)

    order = {name: sorted(REGIONS,
                          key=lambda r: -panel['own_region_repayment'][r]['gain'])
             for name, panel in panels.items()}
    result = {
        'scope': 'opened development only; no frozen policy',
        'question': 'does one acquisition unit repay differently by region, '
                    'and is that repayment stable and publicly predictable',
        'acquisition_unit': 'all verified top-100 candidate labels for one '
                            'region across both source panels',
        'width': WIDTH,
        'source_panels': list(SOURCE),
        'target_panels': list(TARGET),
        'source': source,
        'panels': panels,
        'repayment_rank_by_panel': order,
        'limits': ['Opened panels; all gains are development evidence.',
                   'Specialists share E0 candidate order and pool, so this '
                   'isolates ranking, not coverage.',
                   'Region identity is public via the Unicode block audit.']}
    write_json(OUT, result)
    print(json.dumps({'source': source,
                      'repayment_rank_by_panel': order,
                      'totals': {name: {'e0': panel['e0_total'],
                                        'own_region': panel['own_region_total'],
                                        'reachable_head': panel['reachable_head']}
                                 for name, panel in panels.items()},
                      'gains': {name: {r: panel['own_region_repayment'][r]['gain']
                                       for r in REGIONS}
                                for name, panel in panels.items()}}, indent=2))


if __name__ == '__main__':
    main()
