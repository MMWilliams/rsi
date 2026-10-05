"""Phase 2 screen M1: does the right level-2 configuration vary by environment?

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

SEED = 1101000
ENVIRONMENTS = 12
TRAINING_WORLDS = 400
SOLVED = 64
EVAL_WORLDS = 32
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
BUDGETS = (256, 1024)
PER_WORLD = (2, 3, 4)
WEIGHTS = (.5, 2.)
SLIP = .2
WORKERS = 12
OUT = ROOT / 'analysis/mechanism-env-m1-screen-20261005.json'
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
    for e in range(ENVIRONMENTS):
        env_seed = SEED + e
        env = make_environment(harness, env_seed)
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
        result[str(env_seed)] = {'theta': env['theta'], 'group_counts': counts, 'totals': totals}
        best = max((a for a in totals if a != 'champion'), key=totals.get)
        print(e, env['theta'], counts, 'champion', totals['champion'], 'best', best,
              totals[best] - totals['champion'],
              {a: v - totals['champion'] for a, v in totals.items() if a != 'champion'},
              flush=True)
    arms = [a for a in next(iter(result.values()))['totals'] if a != 'champion']
    gain = {a: sum(r['totals'][a] - r['totals']['champion'] for r in result.values())
            for a in arms}
    fixed = max(gain, key=gain.get)
    oracle = sum(max(r['totals'][a] for a in arms) - r['totals']['champion']
                 for r in result.values())
    regret = oracle - gain[fixed]
    summary = {'fixed': fixed, 'fixed_gain': gain[fixed], 'oracle_gain': oracle,
               'regret': regret, 'regret_share': regret / oracle if oracle > 0 else None,
               'passed': oracle > 0 and regret >= .25 * oracle, 'gain_by_arm': gain}
    write_json(OUT, {'environments': result, 'summary': summary})
    print('\nM1:', summary)


if __name__ == '__main__':
    sys.exit(main())
