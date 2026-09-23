"""Does a grouping learned from worlds do what the syntactic families did?

C-family (`EXPERIMENT-mechanism-family-confirmation.md`) is confirmed with each
atom's family read from its program text. `rsi/learned_groups.py` learns a
grouping instead, from which atoms appear together across training worlds
(adjusted Rand against the true families 0.41, 0.84, 0.89, 0.89 at 100, 400,
1600 and 6400 worlds on seed 632101; small families merge into large ones).

Here the family agent, with the configuration C-family confirmed, runs on
groups learned from 100, 400, 1600 and 6400 training worlds, beside the
champion and the syntactic agent. The champion's pair prior is fitted on the
first 400 training worlds in every arm, so the only thing that changes with
experience is the learned grouping; the pair prior itself stops improving at
about 400 (`mechanism-prior-scaling-20260923.json`). Three held-out splits, six
budgets. Development evidence.
"""
from __future__ import annotations

import multiprocessing
import random
import sys
import time

import numpy as np
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.family_inference import FamilySimulator
from rsi.growth_coach import (CHAMPION, UNHEDGED, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-learned-groups-probe-20260923.json'
SEED = 633101
WORLDS = 48
STREAM = 100
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
SIZES = (100, 400, 1600, 6400)
PRIOR_WORLDS = 400
WEIGHT, SLIP = 2., .2
WORKERS = 8
BOOT = 20000
_STATE = {}


def coach_for(budget):
    return UNHEDGED if budget <= 256 else CHAMPION


def setup():
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    plain = Simulator(harness)
    rng = random.Random(SEED)
    seen = [f for f in harness.by_family if f not in ('popcount', 'xormod')]
    seen_pool = triples(harness, seen, rng, 14, 130)
    rng.shuffle(seen_pool)
    cut = max(1, round(.2 * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held = [t for t in triples(harness, harness.by_family, rng, 14, 130)
            if set(t) & {'popcount', 'xormod'}]
    groups = {g: draw_worlds(harness, p, WORLDS, rng, 14, 130, STREAM)
              for g, p in (('seen_triple', train_triples), ('new_triple', new_triples),
                           ('new_family', held))}
    reserved = {i for ws in groups.values() for w in ws for i in w['stream']}
    training = draw_worlds(harness, train_triples, max(SIZES), rng, 14, 130, 0)
    observed = observed_sets(harness, training, reserved, 64, rng)
    prior = Prior(harness, observed[:PRIOR_WORLDS])
    views = {(g, n): plain.views(w['stream'], rng) for g, ws in groups.items()
             for n, w in enumerate(ws)}
    return harness, plain, prior, observed, groups, views


def _init(labels):
    harness, plain, prior, _observed, _groups, views = setup()
    agents = {'champion': plain, 'syntax': FamilySimulator(harness, [], WEIGHT, SLIP)}
    agents.update({f'learned@{n}': LearnedFamilySimulator(harness, labels[n], WEIGHT, SLIP)
                   for n in SIZES})
    _STATE.update(prior=prior, views=views, agents=agents)


def _world(key):
    s = _STATE
    out = {}
    for arm, agent in s['agents'].items():
        out[arm] = [int(agent.lifetime(CHAMPION if arm == 'champion' else coach_for(b),
                                       s['views'][key], s['prior'], b).sum()) for b in BUDGETS]
    return out


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    harness, _plain, _prior, observed, _groups, _views = setup()
    truth = np.array([key.split(':')[0] for key in harness.key_names])
    labels, recovery = {}, {}
    for n in SIZES:
        labels[n], count = learn_groups(observed[:n], len(harness.key_names))
        seen = labels[n] >= 0
        recovery[n] = {'groups': count, 'atoms_seen': int(seen.sum()),
                       'adjusted_rand': adjusted_rand_score(truth[seen], labels[n][seen])}
        print(n, recovery[n], flush=True)
    keys = [(g, n) for g in ('seen_triple', 'new_triple', 'new_family') for n in range(WORLDS)]
    with multiprocessing.get_context('spawn').Pool(WORKERS, initializer=_init,
                                                   initargs=(labels,)) as pool:
        rows = pool.map(_world, keys, chunksize=1)
    arms = list(rows[0])
    draws = np.random.default_rng(SEED + 3).integers(0, WORLDS, (BOOT, WORLDS))
    result = {'scope': 'family agent on learned groups against syntactic families',
              'seed': SEED, 'budgets': list(BUDGETS), 'sizes': list(SIZES),
              'prior_worlds': PRIOR_WORLDS, 'recovery': {str(n): r for n, r in recovery.items()},
              'groups': {}}
    for group in ('seen_triple', 'new_triple', 'new_family'):
        totals = {a: np.array([r[a] for k, r in zip(keys, rows) if k[0] == group]) for a in arms}
        block = {'mean_by_budget': {a: v.mean(axis=0).tolist() for a, v in totals.items()},
                 'per_world': {a: v.tolist() for a, v in totals.items()}, 'contrasts': {}}
        for arm in arms[1:]:
            difference = totals[arm] - totals['champion']
            sums = difference[draws].sum(axis=1)
            block['contrasts'][arm] = {'sum': difference.sum(axis=0).tolist(),
                                       'low': np.percentile(sums, 2.5, axis=0).tolist(),
                                       'high': np.percentile(sums, 97.5, axis=0).tolist()}
        result['groups'][group] = block
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)
    for group, block in result['groups'].items():
        print(f'\n== {group}: mean solved of 100 by budget {BUDGETS}; minus champion [interval]')
        for arm in arms:
            line = '  {:14s}'.format(arm) + ''.join('{:6.1f}'.format(v)
                                                    for v in block['mean_by_budget'][arm])
            if arm in block['contrasts']:
                e = block['contrasts'][arm]
                line += ' |' + ''.join('{:+5.0f}[{:.0f},{:.0f}]'.format(s, lo, hi).rjust(16)
                                       for s, lo, hi in zip(e['sum'], e['low'], e['high']))
            print(line)


if __name__ == '__main__':
    sys.exit(main())
