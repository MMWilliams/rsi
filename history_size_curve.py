"""How much of the +80 is the single-observation baseline?

Replication one compared a parent holding one development bank against a parent
holding twelve, and the gap was +80. One bank is the weakest informative
baseline, so that number overstates what an extra bank of history is worth in
general. This measures the whole curve: parents holding 1, 2, 3, 4, 6, 8, 10 and
12 banks, each averaged over every contiguous window of that size from the
development panel, deployed on the untouched transfer panel.

It also reports, at each history size, how much of the gain is constant
estimation and how much is context, by comparing each parent against the best
constant chosen with hindsight on the transfer panel.

Reads the audited rows, so it inherits the audit's provenance. No new gate.
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
OUT = ROOT / 'analysis/history-size-curve-20260920.json'
SIZES = (1, 2, 3, 4, 6, 8, 10, 12)


def table(dest, panel):
    """Per-bank public share and action gains, from the audited rows."""
    rows = json.loads((dest / f'audit_rows_{panel}.json').read_text())['rows']
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


def curve(dev, target):
    best_constant = max(ACTIONS,
                        key=lambda a: sum(b['gain'][a] for b in target))
    constant_total = sum(b['gain'][best_constant] for b in target)
    hindsight = sum(max(b['gain'].values()) for b in target)
    out = {}
    for size in SIZES:
        windows = [dev[start:start + size]
                   for start in range(len(dev) - size + 1)]
        totals = []
        for records in windows:
            _, gains = improver.deploy(records, target)
            totals.append(sum(gains))
        mean_total = float(np.mean(totals))
        out[str(size)] = {
            'windows': len(windows),
            'mean_total': mean_total,
            'min_total': int(min(totals)),
            'max_total': int(max(totals)),
            'mean_minus_best_constant': mean_total - constant_total,
            'fraction_of_hindsight': mean_total / hindsight if hindsight else 0.}
    # Paired comparison of the full-history parent against each smaller size,
    # using the first window of that size so the interval is bank-paired.
    _, full = improver.deploy(dev, target)
    for size in SIZES:
        _, small = improver.deploy(dev[:size], target)
        diffs = [a - b for a, b in zip(full, small)]
        out[str(size)]['full_minus_this_first_window'] = {
            'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}
    return {'best_constant_action': best_constant,
            'best_constant_total': constant_total,
            'hindsight_total': hindsight, 'sizes': out}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    result = {'scope': 'history-size curve from audited rows; no new gate',
              'question': 'how much of the replication-one +80 comes from the '
                          'single-observation baseline',
              'sizes': list(SIZES), 'runs': {}}
    for name, dest in RUNS.items():
        if not (dest / 'audit_rows_beta_dev.json').exists():
            print('skipping', name, '(not audited yet)')
            continue
        dev = table(dest, 'beta_dev')
        target = table(dest, 'beta_transfer')
        result['runs'][name] = curve(dev, target)
        value = result['runs'][name]
        print(f'== {name}  best_constant={value["best_constant_total"]} '
              f'({value["best_constant_action"]})  '
              f'hindsight={value["hindsight_total"]}')
        for size in SIZES:
            row = value['sizes'][str(size)]
            print(f'   history={size:2d}  mean={row["mean_total"]:6.1f} '
                  f'[{row["min_total"]:4d},{row["max_total"]:4d}]  '
                  f'vs_best_constant={row["mean_minus_best_constant"]:+6.1f}  '
                  f'{row["fraction_of_hindsight"]:.0%} of hindsight')
    result['limits'] = [
        'Windows are contiguous slices of the development panel, so they are '
        'not independent samples.',
        'The paired interval uses the first window of each size, a single '
        'draw, while the mean averages every window.',
        'Best constant is chosen with final labels and is not deployable.']
    write_json(OUT, result)


if __name__ == '__main__':
    main()
