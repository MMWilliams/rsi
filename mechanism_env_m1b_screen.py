"""Phase 2 screen M1b: M1 on a widened, balanced meta-distribution.

M1 (`mechanism-env-m1-screen-20261005.json`) failed at 10% regret with the
environment parameters drawn at random (8 of 12 had four groups per world).
Here every combination of groups per world (2, 3, 4), group count (6, 12) and
group-size skew (equal, Dirichlet 0.5) appears once, slip drawn from (0, .15);
48 held-out worlds per environment; and the per-environment oracle is
cross-fitted (chosen on one half of the worlds, scored on the other, both
ways) so selection noise cannot manufacture regret. Same pass rule.

Original M1 description:

For each of 12 drawn environments (`rsi/environments.py`): 400 training worlds
with handed solved sets (screening the class before charging it), the champion's
pair prior fitted on them, and the family agent on groups learned under each of
six level-2 configurations (likelihood per-world count 2, 3, 4 x group weight
0.5, 2). Every arm lives 32 held-out worlds of that environment at budgets 256
and 1024. Oracle: the best configuration per environment. Fixed: the best single
configuration across environments. M1 passes if the fixed configuration's regret
to the oracle is at least a quarter of the oracle's gain over the champion,
summed over environments; otherwise one fixed level 2 is near-oracle and the
meta-distribution must be widened before anything is built.
"""
from __future__ import annotations

import multiprocessing
import random
import sys
import warnings

import numpy as np

from rsi.common import ROOT, write_json
from rsi.environments import draw, learn, make_environment
from rsi.growth_coach import CHAMPION, UNHEDGED, Prior, Simulator
from rsi.learned_groups import LearnedFamilySimulator
from rsi.mechanism_worlds import Harness

SEED = 1102000
THETAS = [{'groups': g, 'per_world': p, 'skew': k} for p in (2, 3, 4) for g in (6, 12)
          for k in (0., .5)]
TRAINING_WORLDS = 400
SOLVED = 64
EVAL_WORLDS = 48
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
BUDGETS = (256, 1024)
PER_WORLD = (2, 3, 4)
WEIGHTS = (.5, 2.)
SLIP = .2
WORKERS = 12
OUT = ROOT / 'analysis/mechanism-env-m1b-screen-20261005.json'
_STATE = {}


def _init(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    agents = {'champion': Simulator(harness)}
    for (p, w), lab in labels.items():
        agents[f'p{p}w{w}'] = LearnedFamilySimulator(harness, lab, w, SLIP, per_world=p)
    _STATE.update(prior=prior, views=views, agents=agents)


def _live(key):
    s = _STATE
    out = {}
    for arm, agent in s['agents'].items():
        out[arm] = [int(agent.lifetime(CHAMPION if arm == 'champion' or b > 256 else UNHEDGED,
                                       s['views'][key], s['prior'], b).sum())
                    for b in BUDGETS]
    return out


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    result = {}
    for e, theta in enumerate(THETAS):
        env_seed = SEED + e
        theta = dict(theta, slip=random.Random(env_seed).choice((0., .15)))
        env = make_environment(harness, env_seed, theta)
        rng = random.Random(env_seed + 1)
        harness.set_tiebreak(env_seed + 77)
        held = draw(harness, env, EVAL_WORLDS, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS, STREAM)
        reserved = {i for w in held for i in w['stream']}
        training = draw(harness, env, TRAINING_WORLDS, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS, 0)
        observed = []
        for world in training:
            allowed = [i for i in world['members'] if i not in reserved]
            chosen = rng.sample(allowed, min(SOLVED, len(allowed)))
            observed.append(sorted({harness.key_index[k] for k in harness.observed_keys(chosen)}))
        prior = Prior(harness, observed)
        labels, counts = {}, {}
        for p in PER_WORLD:
            lab, count = learn(observed, keys, p)
            counts[p] = int(count)
            for w in WEIGHTS:
                labels[(p, w)] = lab
        views = {f'{n:03d}': simulator.views(w['stream'], rng) for n, w in enumerate(held)}
        order = list(views)
        with multiprocessing.get_context('spawn').Pool(
                WORKERS, initializer=_init, initargs=(env_seed, prior, views, labels)) as pool:
            lives = dict(zip(order, pool.map(_live, order, chunksize=1)))
        totals = {arm: int(sum(sum(lives[k][arm]) for k in order)) for arm in lives[order[0]]}
        halves = [{arm: int(sum(sum(lives[k][arm]) for k in order[h::2])) for arm in totals}
                  for h in (0, 1)]
        result[str(env_seed)] = {'theta': env['theta'], 'group_counts': counts, 'totals': totals,
                                 'halves': halves}
        best = max((a for a in totals if a != 'champion'), key=totals.get)
        print(e, env['theta'], counts, 'champion', totals['champion'], 'best', best,
              totals[best] - totals['champion'],
              {a: v - totals['champion'] for a, v in totals.items() if a != 'champion'},
              flush=True)
    arms = [a for a in next(iter(result.values()))['totals'] if a != 'champion']
    gain = {a: sum(r['totals'][a] - r['totals']['champion'] for r in result.values())
            for a in arms}
    fixed = max(gain, key=gain.get)
    oracle = 0
    for r in result.values():
        for h in (0, 1):
            pick = max(arms, key=lambda a: r['halves'][h][a])
            other = r['halves'][1 - h]
            oracle += other[pick] - other['champion']
    regret = oracle - gain[fixed]
    summary = {'fixed': fixed, 'fixed_gain': gain[fixed], 'oracle_gain': oracle,
               'regret': regret, 'regret_share': regret / oracle if oracle > 0 else None,
               'passed': oracle > 0 and regret >= .25 * oracle, 'gain_by_arm': gain}
    write_json(OUT, {'environments': result, 'summary': summary})
    print('\nM1:', summary)


if __name__ == '__main__':
    sys.exit(main())
