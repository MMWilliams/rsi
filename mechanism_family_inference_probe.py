"""How much of the family oracle's gain can inference recover?

`mechanism-oracle-structure-probe-20260923.json` showed that knowing a world's
three families roughly doubles what the earned loop solves at budgets 128-512.
`rsi/family_inference.py` infers them from the agent's own evidence, with a
posterior over family triples. Same worlds and seed as that probe; single
lever settings, reported as the share of the oracle's gain over the champion
they recover. Development evidence: a screen, not a claim.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.family_inference import FamilySimulator
from rsi.growth_coach import (CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds, observed_sets,
                              triples)
from rsi.mechanism_worlds import Harness
from mechanism_oracle_structure_probe import oracle

OUT = ROOT / 'analysis/mechanism-family-inference-probe-20260923.json'
SEED = 628101
WORLDS = 32
STREAM = 100
BUDGETS = (128, 256, 512, 1024)
SETTINGS = [(w, s) for w in (1., 2., 4.) for s in (.2, .5)]
BOOT = 20000


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    plain = Simulator(harness)
    rng = random.Random(SEED)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    pool = triples(harness, seen, rng, 14, 130)
    worlds = draw_worlds(harness, pool, WORLDS, rng, 14, 130, STREAM)
    reserved = {i for w in worlds for i in w['stream']}
    training = draw_worlds(harness, pool, 400, rng, 14, 130, 0)
    learned = Prior(harness, observed_sets(harness, training, reserved, 64, rng))
    inference = {(w, s): FamilySimulator(harness, [t['triple'] for t in training], w, s)
                 for w, s in SETTINGS}

    arms = ['champion', 'warm', 'family oracle']
    arms += [f'infer w={w:g} slip={s:g}{suffix}' for w, s in SETTINGS for suffix in ('', ' hedged')]
    totals = {arm: np.zeros((WORLDS, len(BUDGETS))) for arm in arms}
    for number, world in enumerate(worlds):
        views = plain.views(world['stream'], rng)
        families = oracle(harness, learned,
                          [k for f in world['triple'] for k in harness.by_family[f]])
        runs = {'champion': (plain, CHAMPION, learned), 'warm': (plain, UNHEDGED, learned),
                'family oracle': (plain, UNHEDGED, families)}
        for (w, s), simulator in inference.items():
            runs[f'infer w={w:g} slip={s:g}'] = (simulator, UNHEDGED, learned)
            runs[f'infer w={w:g} slip={s:g} hedged'] = (simulator, CHAMPION, learned)
        for arm, (simulator, coach, prior) in runs.items():
            for b, budget in enumerate(BUDGETS):
                totals[arm][number, b] = simulator.lifetime(coach, views, prior, budget).sum()
        print('world', number, round(time.perf_counter() - wall), 's', flush=True)

    draws = np.random.default_rng(SEED + 3).integers(0, WORLDS, (BOOT, WORLDS))
    gain = totals['family oracle'].sum(axis=0) - totals['champion'].sum(axis=0)
    result = {'scope': 'family-triple inference against the family oracle', 'seed': SEED,
              'budgets': list(BUDGETS),
              'mean_by_budget': {a: v.mean(axis=0).tolist() for a, v in totals.items()},
              'per_world': {a: v.tolist() for a, v in totals.items()}, 'contrasts': {}}
    for arm in arms[1:]:
        difference = totals[arm] - totals['champion']
        sums = difference[draws].sum(axis=1)
        result['contrasts'][arm] = {
            'sum': difference.sum(axis=0).tolist(),
            'low': np.percentile(sums, 2.5, axis=0).tolist(),
            'high': np.percentile(sums, 97.5, axis=0).tolist(),
            'share_of_oracle_gain': (difference.sum(axis=0) / np.maximum(gain, 1)).tolist()}
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)
    print('\nmean solved of 100 at', BUDGETS, '| minus champion [interval] | share of oracle gain')
    for arm in arms:
        line = '  {:26s}'.format(arm) + ''.join('{:7.1f}'.format(v)
                                                for v in result['mean_by_budget'][arm])
        if arm in result['contrasts']:
            e = result['contrasts'][arm]
            line += ' |' + ''.join('{:+5.0f}[{:.0f}]'.format(s, lo).rjust(12)
                                   for s, lo in zip(e['sum'], e['low']))
            line += ' |' + ''.join('{:6.2f}'.format(x) for x in e['share_of_oracle_gain'])
        print(line)


if __name__ == '__main__':
    sys.exit(main())
