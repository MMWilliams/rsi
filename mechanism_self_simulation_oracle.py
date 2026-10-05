"""Diagnostic: self-simulation inside the TRUE world generator.

Self-simulation inside the agent's fitted world model made its discovery-rate
estimates worse (Pearson 0.14-0.40 against 0.54-0.71 from EM alone). This asks
whether the method or its input is at fault: imagined worlds are drawn from the
real generator (training family triples), which the agent never has. If the
rates measured there match the true rates, self-simulation is sound and the
world model is the bottleneck. Seed 643101; diagnostic only.
"""
from __future__ import annotations

import multiprocessing
import random
import sys

import numpy as np

from rsi.growth_coach import Simulator, draw_worlds, triples
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix
import mechanism_self_simulation as sim
import mechanism_earned_confirmation as conf
from mechanism_earned_trust_screen import earning_of

SEED = 643101
TRAIN = 1280
IMAGINED = 800


def main():
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    _rng, groups, training, _s, streams, _h, _p, _n = conf.setup(harness, SEED)
    reserved = {i for ws in groups.values() for w in ws for i in w['stream']}
    earning = earning_of(SEED, streams)
    earned = _matrix([conf.earned_set(d, simulator.row_keys, 1) for d in earning], keys)
    truth = _matrix([[harness.key_index[k] for k in w['keys']] for w in training], keys)
    has = truth[:TRAIN].sum(0)
    true_r = np.where(has > 0, (earned[:TRAIN] * truth[:TRAIN]).sum(0) / np.maximum(has, 1), np.nan)
    rng = random.Random(SEED + 999)
    seen = [f for f in harness.by_family if f not in conf.HELD_OUT_FAMILIES]
    pool = triples(harness, seen, rng, conf.KEYS_PER_WORLD, conf.MINIMUM_MEMBERS)
    worlds = draw_worlds(harness, pool, IMAGINED, rng, conf.KEYS_PER_WORLD, conf.MINIMUM_MEMBERS,
                         10 ** 6)
    if '--reserved' in sys.argv:
        for w in worlds:
            w['stream'] = [i for i in w['stream'] if i not in reserved]
    for w in worlds:
        w['stream'] = w['stream'][:conf.EARN_STREAM]
    with multiprocessing.get_context('spawn').Pool(conf.WORKERS, initializer=sim._init_self,
                                                   initargs=(SEED, SEED * 10 + 7)) as p:
        out = p.map(sim._earn_self, [(i, w['stream']) for i, w in enumerate(worlds)], chunksize=8)
    present, found = np.zeros(keys), np.zeros(keys)
    for w, d in zip(worlds, out):
        got = set(conf.earned_set(d, simulator.row_keys, 1))
        for k in (harness.key_index[n] for n in w['keys']):
            present[k] += 1
            found[k] += k in got
    sim_r = np.where(present >= 3, found / np.maximum(present, 1), np.nan)
    ok = ~np.isnan(true_r) & ~np.isnan(sim_r)
    print('atoms', int(ok.sum()), 'pearson', round(float(np.corrcoef(sim_r[ok], true_r[ok])[0, 1]), 3),
          'mae', round(float(np.abs(sim_r[ok] - true_r[ok]).mean()), 3))
    # split-half reliability of the true rate itself, the ceiling for any estimate
    a = np.where(truth[:640].sum(0) > 0, (earned[:640] * truth[:640]).sum(0) / np.maximum(truth[:640].sum(0), 1), np.nan)
    b = np.where(truth[640:TRAIN].sum(0) > 0, (earned[640:TRAIN] * truth[640:TRAIN]).sum(0) / np.maximum(truth[640:TRAIN].sum(0), 1), np.nan)
    ok2 = ~np.isnan(a) & ~np.isnan(b)
    print('true-rate split-half pearson', round(float(np.corrcoef(a[ok2], b[ok2])[0, 1]), 3))


if __name__ == '__main__':
    sys.exit(main())
