"""Consistency check: rotate the held-out panel through every cached panel.

`construction_improver_development.py` held one panel out and reported D1 and D2
on it. A single split is one draw. This repeats the whole construction-improver
experiment five times, holding out each cached panel in turn, and reports whether
the gates hold every time and how the built-minus-pooled gap behaves.

Reproducibility is the point: same code, same sizes, same windows, only the
held-out panel changes.
"""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT, write_json
from region_specialist_repayment_development import SOURCE, TARGET
import construction_improver_development as dev


OUT = ROOT / 'analysis/construction-improver-rotation-20260921.json'
PANELS = list(SOURCE) + list(TARGET)


def run_for(panels, held):
    transfer = panels[held]
    history_pool = [bank for name, banks in panels.items()
                    if name != held for bank in banks]
    curve = {}
    for size in dev.SIZES:
        span = len(history_pool) - size + 1
        starts = list(range(0, span, max(1, span // dev.MAX_WINDOWS)))[:dev.MAX_WINDOWS]
        built = np.zeros(len(transfer))
        pooled = np.zeros(len(transfer))
        for start in starts:
            history = history_pool[start:start + size]
            specialists = dev.build_system(history)
            order = sorted(specialists)
            actions = order + ['e0']
            router = dev.fit_router(history, specialists, actions, order)
            built += np.asarray(
                dev.deploy(transfer, specialists, router, actions, order), float)
            pooled += np.asarray(dev.pooled_only(transfer, specialists), float)
        built /= len(starts)
        pooled /= len(starts)
        curve[str(size)] = {'windows': len(starts),
                            'built_total': float(built.sum()),
                            'pooled_total': float(pooled.sum()),
                            'built_per_bank': [float(v) for v in built],
                            'pooled_per_bank': [float(v) for v in pooled],
                            'built_minus_pooled': dev.compare(list(built),
                                                              list(pooled))}
    largest = curve[str(dev.SIZES[-1])]
    smallest = curve[str(dev.SIZES[0])]
    growth = dev.compare(largest['built_per_bank'], smallest['built_per_bank'])
    pooled_growth = dev.compare(largest['pooled_per_bank'],
                                smallest['pooled_per_bank'])
    against = largest['built_minus_pooled']
    monotone = all(curve[str(a)]['built_total'] <= curve[str(b)]['built_total']
                   for a, b in zip(dev.SIZES, dev.SIZES[1:]))
    return {'held_out': held, 'history_banks': len(history_pool),
            'curve': curve, 'monotone_built': bool(monotone),
            'D1_construction_beats_pooling': {
                **against,
                'passed': bool(against['gain'] > 0 and against['interval'][0] > 0)},
            'D2_construction_growth': {
                **growth,
                'passed': bool(growth['gain'] >= dev.THRESHOLD
                               and growth['losing_banks'] <= 4
                               and growth['interval'][0] > 0)},
            'pooled_growth_for_reference': pooled_growth}


def main():
    if OUT.exists():
        raise RuntimeError('rotation exists')
    panels = dev.load_banks()
    runs = {}
    for held in PANELS:
        runs[held] = run_for(panels, held)
        value = runs[held]
        d1 = value['D1_construction_beats_pooling']
        d2 = value['D2_construction_growth']
        print('{:34s} D1={:+4d} {} {:5s}  D2={:+4d} {} {:5s}  mono={}'.format(
            held[:34], d1['gain'], d1['interval'], str(d1['passed']),
            d2['gain'], d2['interval'], str(d2['passed']),
            value['monotone_built']), flush=True)

    d1_pass = sum(v['D1_construction_beats_pooling']['passed']
                  for v in runs.values())
    d2_pass = sum(v['D2_construction_growth']['passed'] for v in runs.values())
    gaps = [v['curve'][str(s)]['built_minus_pooled']['gain']
            for v in runs.values() for s in dev.SIZES]
    result = {
        'scope': 'opened development; five-fold rotation of the held-out panel',
        'panels': PANELS, 'sizes': list(dev.SIZES), 'runs': runs,
        'summary': {
            'D1_passed_folds': d1_pass, 'D2_passed_folds': d2_pass,
            'folds': len(PANELS),
            'monotone_folds': sum(v['monotone_built'] for v in runs.values()),
            'built_minus_pooled_mean_by_size': {
                str(s): float(np.mean([v['curve'][str(s)]['built_minus_pooled']['gain']
                                       for v in runs.values()]))
                for s in dev.SIZES},
            'built_growth_mean': float(np.mean(
                [v['D2_construction_growth']['gain'] for v in runs.values()])),
            'pooled_growth_mean': float(np.mean(
                [v['pooled_growth_for_reference']['gain'] for v in runs.values()]))},
        'limits': [
            'Opened cached panels; development evidence only.',
            'Folds share history banks, so they are not independent replications; '
            'this measures split sensitivity, not fresh-bank transfer.',
            'The partition rule is researcher written; the improver computes the '
            'partition and trains every model.']}
    write_json(OUT, result)
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
