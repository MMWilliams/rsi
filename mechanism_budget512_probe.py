"""Development: why does no grouping beat the champion at budget 512?

On 645101 even the handed true-set grouping is level with the champion at 512
(+20, -9, -6) while it gains at 256 and 1024. Hypothesis: the half hedge
splits 512 scans so that neither the grouped order nor the hedged order reaches
the depth where they differ. Varies the hedge share at 512 and 256 only, for
the earned grouping (weight 0.5) and the handed one (weight 2), on the three
opened development seeds with their earning reused. Development evidence.
"""
from __future__ import annotations

import json
import multiprocessing
import sys
import warnings
from dataclasses import replace

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, Simulator
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf
from mechanism_earned_trust_screen import earning_of

SEEDS = (643101, 644101, 645101)
BUDGETS = (256, 512)
HEDGES = (0., .25, .5)
EVAL_PER_SPLIT = 64
OUT = ROOT / 'analysis/mechanism-budget512-probe-20261005.json'
_STATE = {}


def _init(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    _STATE.update(prior=prior, views=views, agents={
        'champion': Simulator(harness),
        'earned': LearnedFamilySimulator(harness, labels['earned'], .5, conf.SLIP),
        'handed': LearnedFamilySimulator(harness, labels['handed'], 2., conf.SLIP)})


def _live(key):
    s = _STATE
    out = {}
    for b in BUDGETS:
        for hedge in HEDGES:
            coach = replace(CHAMPION, hedge=hedge)
            for arm, agent in s['agents'].items():
                out[f'{arm}|h{hedge}|{b}'] = int(agent.lifetime(coach, s['views'][key],
                                                                s['prior'], b).sum())
    return out


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    result = {}
    for seed in SEEDS:
        rng, groups, _t, _s, streams, handed, prior, _n = conf.setup(harness, seed)
        if seed == 645101:
            cache = ROOT / 'runs/mechanism-earned-confirmation2-dev-645101/earning-dev.json'
            earning = json.loads(cache.read_text())['earning']
        else:
            earning = earning_of(seed, streams)
        earned = [conf.earned_set(d, simulator.row_keys, conf.MINIMUM_PICKS) for d in earning]
        labels = {'earned': conf.grouping(conf.confident(earned), keys)[0],
                  'handed': learn_groups(handed, keys, choices=conf.GROUP_CHOICES,
                                         select='likelihood')[0]}
        views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng)
                 for split, worlds in groups.items() for n, world in enumerate(worlds)
                 if n < EVAL_PER_SPLIT}
        order = list(views)
        with multiprocessing.get_context('spawn').Pool(
                conf.WORKERS, initializer=_init, initargs=(seed, prior, views, labels)) as pool:
            lives = dict(zip(order, pool.map(_live, order, chunksize=1)))
        names = list(lives[order[0]])
        totals = {name: np.array([lives[k][name] for k in order]) for name in names}
        block = {}
        print(f'seed {seed}: minus the champion at hedge 0.5, all splits pooled', flush=True)
        for name in names:
            arm, hedge, budget = name.split('|')
            base = totals[f'champion|h0.5|{budget}']
            diff = totals[name] - base
            draws = np.random.default_rng(seed).integers(0, len(diff), (5000, len(diff)))
            sums = diff[draws].sum(axis=1)
            block[name] = {'sum': int(diff.sum()), 'low': float(np.percentile(sums, 2.5)),
                           'high': float(np.percentile(sums, 97.5))}
            print(f'  {name:22s} {diff.sum():+6d} [{block[name]["low"]:.0f}, '
                  f'{block[name]["high"]:.0f}]', flush=True)
        result[str(seed)] = block
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
