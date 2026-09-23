"""Does a mechanism-heterogeneous environment clear the P2b regret threshold?

`heterogeneous_regret_simulation.py` showed that varying the *family mix* of
i.i.d. banks cannot lift fixed regret past +17, because every region specialist
helps a little and none of them harms. The familiar/shifted AST split does harm.
Measured on the audited dual-specialist transfer, per 96 tasks:

                     familiar tasks   shifted tasks
  familiar model         +35              -2
  shifted model          -14             +26

The sign flips, so the best action genuinely depends on the instance. This
resamples those audited per-task labels into banks whose familiar/shifted
proportion varies *between* banks, and measures fixed regret against the best
constant policy.

The control that matters is `balanced`: every bank 50/50, which is what the
original dual-specialist run actually used. If balanced shows low regret and the
varying profiles show high regret, then between-bank heterogeneity, not
within-bank difficulty, is what makes improver growth measurable.

Simulation on opened audited rows. Nothing is generated and no policy is frozen.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json


SOURCE = ROOT / 'runs/dual-specialist-integration-transfer-20260918/results.json'
OUT = ROOT / 'analysis/mechanism-regret-simulation-20260920.json'
ACTIONS = ('e0', 'familiar', 'shifted')
DOMAINS = ('familiar', 'shifted')
BANK_TASKS = 48
BANKS = 12
DRAWS = 200
THRESHOLD = 20
SEED = 907700


def audited_rows():
    data = json.loads(SOURCE.read_text())
    assert len(data['tasks']) == 192
    pool = defaultdict(list)
    for task in data['tasks']:
        pool[task['domain']].append({action: task['labels'][action]
                                     for action in ACTIONS})
    return pool


def profiles_for(kind, rng):
    """Probability of a familiar task, per bank."""
    if kind == 'balanced':
        return [.5] * BANKS
    if kind == 'split':
        return [1. if index % 2 == 0 else 0. for index in range(BANKS)]
    if kind == 'beta':
        return list(rng.beta(.4, .4, size=BANKS))
    if kind == 'drifting':
        return list(np.linspace(0., 1., BANKS))
    raise ValueError(kind)


def compose(share, pool, rng):
    tasks = []
    for _ in range(BANK_TASKS):
        domain = 'familiar' if rng.random() < share else 'shifted'
        choices = pool[domain]
        tasks.append(choices[rng.integers(len(choices))])
    return tasks


def evaluate(kind, pool, rng):
    banks = [compose(share, pool, rng) for share in profiles_for(kind, rng)]
    table = np.array([[sum(task[action] for task in tasks)
                       for action in ACTIONS] for tasks in banks])
    e0 = table[:, ACTIONS.index('e0')]
    gain = table - e0[:, None]

    best_constant = int(gain.sum(axis=0).max())
    hindsight = int(gain.max(axis=1).sum())

    # Learnability: pick by the observed familiar share, nearest neighbour among
    # the other eleven banks. The share is public: it is a count of task blocks.
    shares = np.array([sum(1 for task in tasks
                           if task['familiar'] >= task['shifted'])
                       for tasks in banks], float) / BANK_TASKS
    contextual = 0
    for held in range(BANKS):
        rest = [i for i in range(BANKS) if i != held]
        neighbour = rest[int(np.abs(shares[rest] - shares[held]).argmin())]
        contextual += int(gain[held, int(gain[neighbour].argmax())])

    return {'best_constant': best_constant, 'hindsight': hindsight,
            'fixed_regret': hindsight - best_constant,
            'contextual': contextual,
            'contextual_minus_constant': contextual - best_constant,
            'distinct_optima': len(set(gain.argmax(axis=1).tolist()))}


def main():
    if OUT.exists():
        raise RuntimeError('simulation exists')
    pool = audited_rows()
    rng = np.random.default_rng(SEED)
    summary = {}
    for kind in ('balanced', 'beta', 'drifting', 'split'):
        draws = [evaluate(kind, pool, rng) for _ in range(DRAWS)]
        keys = ('fixed_regret', 'contextual_minus_constant', 'best_constant',
                'hindsight', 'distinct_optima')
        summary[kind] = {
            key: {'mean': float(np.mean([d[key] for d in draws])),
                  'p10': float(np.percentile([d[key] for d in draws], 10)),
                  'p90': float(np.percentile([d[key] for d in draws], 90))}
            for key in keys}
        beaten = [d['contextual_minus_constant'] > 0 for d in draws]
        summary[kind]['draws_where_context_wins'] = float(np.mean(beaten))
        value = summary[kind]
        print(f'{kind:10s} fixed_regret={value["fixed_regret"]["mean"]:6.1f} '
              f'(p10 {value["fixed_regret"]["p10"]:.0f}, '
              f'p90 {value["fixed_regret"]["p90"]:.0f})  '
              f'contextual-constant='
              f'{value["contextual_minus_constant"]["mean"]:+6.1f} '
              f'(p10 {value["contextual_minus_constant"]["p10"]:+.0f}, '
              f'p90 {value["contextual_minus_constant"]["p90"]:+.0f}, '
              f'wins {value["draws_where_context_wins"]:.0%})  '
              f'best_constant={value["best_constant"]["mean"]:5.1f}', flush=True)

    result = {
        'scope': 'resampling simulation on audited dual-specialist rows; '
                 'nothing generated, no policy frozen',
        'question': 'does between-bank mechanism heterogeneity clear the P2b '
                    f'fixed-regret threshold of +{THRESHOLD} per 576 tasks',
        'source': str(SOURCE.relative_to(ROOT)),
        'per_domain_repayment': {
            'familiar_model': {'familiar_tasks': 35, 'shifted_tasks': -2},
            'shifted_model': {'familiar_tasks': -14, 'shifted_tasks': 26}},
        'draws': DRAWS, 'banks': BANKS, 'bank_tasks': BANK_TASKS,
        'threshold': THRESHOLD, 'profiles': summary,
        'verdict': {kind: bool(value['fixed_regret']['mean'] > THRESHOLD)
                    for kind, value in summary.items()},
        'limits': [
            'Rows are resampled with replacement from audited tasks, so bank '
            'composition is synthetic while every label is real.',
            'Both specialists were trained before this simulation; a real '
            'generator would retrain them per environment.',
            'The contextual arm is nearest-neighbour on the public familiar '
            'share, a deliberately weak learner.',
            'balanced is the control and matches the original run design.']}
    write_json(OUT, result)
    print(json.dumps({'verdict': result['verdict'],
                      'fixed_regret': {k: v['fixed_regret']['mean']
                                       for k, v in summary.items()}}, indent=2))


if __name__ == '__main__':
    main()
