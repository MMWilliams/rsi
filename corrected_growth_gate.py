"""The corrected improver-growth gate, applied post hoc to both replications.

G2 as predeclared compared a twelve-bank parent against a *single* development
bank fixed by lowest seed. Replication one drew a bank scoring 46 and passed at
+80; replication two drew one scoring 92, equal to the best constant, and failed
at +26. The history-size curve had already shown single-bank parents span 46 to
104, so the gate was measuring the baseline draw, not the learner.

The correction: score a small-history parent as its **expected** value over every
contiguous window of that size, then pair against the large-history parent by
transfer bank. That removes the draw from the comparison while keeping the
bank-level pairing the interval needs.

This is a **post hoc** analysis. Redesigning a gate after seeing its results
cannot produce a pass; the numbers here are diagnostic and say what a corrected
gate would need to be predeclared against on fresh banks. Nothing here is
reported as growth.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
import contextual_improver_transfer as improver
from heterogeneous_ast_environment import ACTIONS


RUNS = {'replication_one': ROOT / 'runs/heterogeneous-ast-environment-20260920',
        'replication_two':
            ROOT / 'runs/heterogeneous-ast-environment-rep2-20260920'}
OUT = ROOT / 'analysis/corrected-growth-gate-20260920.json'
SMALL = 1
LARGE = 12


def table(dest, panel):
    rows = json.loads((dest / f'audit_rows_{panel}.json').read_text())['rows']
    totals = defaultdict(lambda: defaultdict(int))
    leaning = defaultdict(list)
    for row in rows:
        for action in ACTIONS:
            totals[row['seed']][action] += row['labels'][action]
        leaning[row['seed']].append(
            row['confidence']['familiar'] >= row['confidence']['shifted'])
    banks = []
    for seed in sorted(totals):
        base = totals[seed]['e0']
        banks.append({'seed': seed,
                      'public_share': float(np.mean(leaning[seed])),
                      'e0': base,
                      'gain': {a: totals[seed][a] - base for a in ACTIONS}})
    return banks


def expected_small(dev, target, size):
    """Per-transfer-bank mean gain of a size-`size` parent, over all windows."""
    windows = [dev[start:start + size] for start in range(len(dev) - size + 1)]
    per_bank = np.zeros(len(target))
    for records in windows:
        _, gains = improver.deploy(records, target)
        per_bank += np.asarray(gains, float)
    return per_bank / len(windows)


def analyse(dest):
    dev = table(dest, 'beta_dev')
    target = table(dest, 'beta_transfer')
    _, large = improver.deploy(dev[:LARGE], target)
    small = expected_small(dev, target, SMALL)
    diffs = [float(a - b) for a, b in zip(large, small)]

    best_constant = max(ACTIONS,
                        key=lambda a: sum(b['gain'][a] for b in target))
    constant = [b['gain'][best_constant] for b in target]
    against_constant = [a - b for a, b in zip(large, constant)]
    hindsight = sum(max(b['gain'].values()) for b in target)

    return {
        'large_total': sum(large),
        'expected_small_total': float(small.sum()),
        'corrected_gain': float(np.sum(diffs)),
        'corrected_positive_banks': int(sum(d > 0 for d in diffs)),
        'corrected_losing_banks': int(sum(d < 0 for d in diffs)),
        'corrected_interval': interval([int(round(d)) for d in diffs]),
        'best_constant_action': best_constant,
        'best_constant_total': sum(constant),
        'large_minus_best_constant': {
            'gain': sum(against_constant),
            'positive_banks': int(sum(d > 0 for d in against_constant)),
            'losing_banks': int(sum(d < 0 for d in against_constant)),
            'interval': interval(against_constant)},
        'hindsight_total': hindsight}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    runs = {}
    for name, dest in RUNS.items():
        if not (dest / 'audit_rows_beta_transfer.json').exists():
            print('skipping', name, '(transfer panel not audited yet)')
            continue
        runs[name] = analyse(dest)
        value = runs[name]
        print(f'== {name}')
        print(f'   large(12) total          {value["large_total"]}')
        print(f'   expected small(1) total  {value["expected_small_total"]:.1f}')
        print(f'   CORRECTED gain           {value["corrected_gain"]:+.1f} '
              f'{value["corrected_positive_banks"]}w/'
              f'{value["corrected_losing_banks"]}l '
              f'{value["corrected_interval"]}')
        c = value['large_minus_best_constant']
        print(f'   large - best constant    {c["gain"]:+d} '
              f'{c["positive_banks"]}w/{c["losing_banks"]}l {c["interval"]}')

    consistent = None
    if len(runs) == 2:
        gains = [v['corrected_gain'] for v in runs.values()]
        lows = [v['corrected_interval'][0] for v in runs.values()]
        consistent = bool(all(g > 0 for g in gains) and all(l > 0 for l in lows))

    write_json(OUT, {
        'scope': 'post hoc corrected gate; diagnostic only, not a pass',
        'why': 'G2 as predeclared measured the single-bank baseline draw. '
               'Replication one drew 46 and passed, replication two drew 92 '
               'and failed, while single-bank parents span 46 to 104.',
        'correction': 'score the small-history parent as its expected value '
                      'over every contiguous window of that size, paired by '
                      'transfer bank',
        'small_history': SMALL, 'large_history': LARGE,
        'runs': runs,
        'both_replications_positive_with_clean_intervals': consistent,
        'limits': [
            'Post hoc. A gate redesigned after seeing results cannot produce a '
            'pass; these numbers say what to predeclare on fresh banks.',
            'Contiguous windows over one development panel are not independent '
            'samples, so the expected-small estimate has unmodelled dependence.',
            'The large-history arm is still a single parent, so its own draw is '
            'not averaged over.',
            'Best constant uses final labels and is not deployable.']})


if __name__ == '__main__':
    main()
