"""Would a heterogeneous-mix environment have measurable fixed regret?

`ACTION-SPACE-STATIONARITY-2026-09-20.md` showed the current i.i.d. banks give a
perfectly context-conditioned policy only +6 and +12 over the best constant
policy, so no improver can show growth on them at any action space. P2b in the
technical design requires a candidate environment to clear +20 per 576 tasks
before any improver is built for it.

This measures that cheaply and without generating anything. Every audited task
row carries its region and its verified label under E0 and under each of the six
region specialists, so banks with any family mix can be composed by resampling
those rows. The composition is a simulation on opened data; it decides whether
building the real generator is worth the compute, and nothing more.

Three profiles families are compared:

- `iid`: the current generator, equal mix, as a control that must reproduce the
  measured +6 and +12.
- `split`: banks drawn from one of two disjoint region triples, so no single
  budget-3 purchase can serve both.
- `dirichlet`: per-bank mixes drawn from a Dirichlet prior, the realistic case.

Fixed regret is reported with a learnability check: a policy that conditions on
the publicly countable region mix, fitted on held-out banks, against the best
constant policy.
"""
from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval


DEST = ROOT / 'runs/region-acquisition-improver-transfer-20260920'
OUT = ROOT / 'analysis/heterogeneous-regret-simulation-20260920.json'
REGIONS = ('transform_transition', 'ast_transition', 'novel_operator_transition',
           'stack_transition', 'mutation_transition', 'self_edit_transition')
BUDGET = 3
BANK_TASKS = 48
BANKS = 12
DRAWS = 200
SPLIT_A = ('ast_transition', 'novel_operator_transition', 'stack_transition')
SPLIT_B = ('transform_transition', 'mutation_transition', 'self_edit_transition')
SETS = tuple(combinations(REGIONS, BUDGET))
SEED = 907600


def audited_rows():
    """Every audited fresh task, pooled by region."""
    pool = defaultdict(list)
    for name in ('transfer_b', 'transfer_c'):
        part = json.loads((DEST / f'audit_rows_{name}.json').read_text())
        for row in part['rows']:
            pool[row['region']].append(row['labels'])
    return pool


def bank_value(tasks, installed):
    """Correct choices on one composed bank under one purchase."""
    return sum(labels[region] if region in installed else labels['e0']
               for region, labels in tasks)


def compose(profile, pool, rng):
    """Draw one bank of tasks with the given region probabilities."""
    regions = rng.choice(len(REGIONS), size=BANK_TASKS, p=profile)
    tasks = []
    for index in regions:
        region = REGIONS[index]
        choices = pool[region]
        tasks.append((region, choices[rng.integers(len(choices))]))
    return tasks


def profiles_for(kind, rng):
    if kind == 'iid':
        return [np.full(len(REGIONS), 1 / len(REGIONS)) for _ in range(BANKS)]
    if kind == 'split':
        out = []
        for index in range(BANKS):
            triple = SPLIT_A if index % 2 == 0 else SPLIT_B
            weights = np.array([1. if r in triple else 0. for r in REGIONS])
            out.append(weights / weights.sum())
        return out
    if kind == 'dirichlet':
        return [rng.dirichlet(np.full(len(REGIONS), .35)) for _ in range(BANKS)]
    raise ValueError(kind)


def mix_features(tasks):
    counts = np.zeros(len(REGIONS))
    for region, _ in tasks:
        counts[REGIONS.index(region)] += 1
    return counts / len(tasks)


def evaluate(kind, pool, rng):
    """One draw of an environment: its fixed regret and learnable fraction."""
    banks = [compose(profile, pool, rng) for profile in profiles_for(kind, rng)]
    e0 = [bank_value(tasks, ()) for tasks in banks]
    table = np.array([[bank_value(tasks, combo) - base
                       for combo in SETS]
                      for tasks, base in zip(banks, e0)])

    constant = table.sum(axis=0)
    best_constant = int(constant.max())
    hindsight = int(table.max(axis=1).sum())

    # Learnability: choose per bank using only the public mix, fitted on the
    # other eleven banks by nearest mix profile.
    features = np.array([mix_features(tasks) for tasks in banks])
    contextual = 0
    for held in range(len(banks)):
        rest = [i for i in range(len(banks)) if i != held]
        distance = np.linalg.norm(features[rest] - features[held], axis=1)
        neighbour = rest[int(distance.argmin())]
        contextual += int(table[held, int(table[neighbour].argmax())])

    return {'best_constant': best_constant, 'hindsight': hindsight,
            'fixed_regret': hindsight - best_constant,
            'contextual_nearest_mix': contextual,
            'contextual_minus_constant': contextual - best_constant,
            'distinct_optima': len(set(table.argmax(axis=1).tolist()))}


def main():
    if OUT.exists():
        raise RuntimeError('simulation exists')
    pool = audited_rows()
    rng = np.random.default_rng(SEED)
    summary = {}
    for kind in ('iid', 'split', 'dirichlet'):
        draws = [evaluate(kind, pool, rng) for _ in range(DRAWS)]
        keys = ('fixed_regret', 'contextual_minus_constant', 'best_constant',
                'hindsight', 'distinct_optima')
        summary[kind] = {
            key: {'mean': float(np.mean([d[key] for d in draws])),
                  'p10': float(np.percentile([d[key] for d in draws], 10)),
                  'p90': float(np.percentile([d[key] for d in draws], 90))}
            for key in keys}
        summary[kind]['interval_contextual_minus_constant'] = interval(
            [d['contextual_minus_constant'] for d in draws])
        print(f'{kind:10s} fixed_regret={summary[kind]["fixed_regret"]["mean"]:6.1f} '
              f'(p10 {summary[kind]["fixed_regret"]["p10"]:.0f}, '
              f'p90 {summary[kind]["fixed_regret"]["p90"]:.0f})  '
              f'contextual-constant='
              f'{summary[kind]["contextual_minus_constant"]["mean"]:+6.1f}  '
              f'distinct_optima='
              f'{summary[kind]["distinct_optima"]["mean"]:.1f}', flush=True)

    result = {
        'scope': 'resampling simulation on audited fresh-bank rows; no new '
                 'tasks generated and no policy frozen',
        'question': 'does a heterogeneous-mix environment clear the P2b fixed '
                    'regret threshold of +20 per 576 tasks',
        'draws': DRAWS, 'banks': BANKS, 'bank_tasks': BANK_TASKS,
        'budget': BUDGET,
        'threshold': 20,
        'profiles': summary,
        'verdict': {kind: bool(value['fixed_regret']['mean'] > 20)
                    for kind, value in summary.items()},
        'limits': [
            'Rows are resampled with replacement from audited fresh tasks, so '
            'bank composition is synthetic while every label is real.',
            'The specialists were trained on the current i.i.d. source panels; '
            'a real heterogeneous generator would retrain them.',
            'The contextual arm uses nearest-mix transfer, a weak learner '
            'chosen to avoid overstating learnability.',
            'iid is the control and should reproduce the measured +6 and +12.']}
    write_json(OUT, result)
    print(json.dumps({'verdict': result['verdict'],
                      'fixed_regret': {k: v['fixed_regret']['mean']
                                       for k, v in summary.items()}}, indent=2))


if __name__ == '__main__':
    main()
