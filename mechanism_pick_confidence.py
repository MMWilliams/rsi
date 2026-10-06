"""Can the agent tell its own right picks from wrong ones?

Re-earns 400 real training worlds of seed 643101 with the full trace and
reports P(pick correct | number of consistent hypotheses found within budget),
the candidate self-assessment signal for weighting earned evidence.
"""
from __future__ import annotations

import multiprocessing
import random
import sys
from collections import defaultdict

from rsi.growth_coach import BLIND, Simulator, world_seed
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf

SEED, N = 643101, 400
_STATE = {}


def _init(seed):
    h = Harness()
    h.set_tiebreak(seed + 77)
    _STATE.update(sim=Simulator(h), seed=seed)


def _earn(job):
    i, stream = job
    s = _STATE['sim']
    views = s.views(stream, random.Random(world_seed(_STATE['seed'] + 5, i)))
    trace = []
    s.lifetime(BLIND, views, None, conf.EARN_BUDGET, trace=trace)
    return [(d['pick'], d['hit'], d['window_consistent'], d['step']) for d in trace]


def main():
    h = Harness()
    _r, _g, training, _s, streams, *_ = conf.setup(h, SEED)
    with multiprocessing.get_context('spawn').Pool(12, initializer=_init, initargs=(SEED,)) as p:
        out = p.map(_earn, [(i, streams[i]) for i in range(N)], chunksize=8)
    by = defaultdict(lambda: [0, 0])
    for world in out:
        for pick, hit, n, step in world:
            if pick < 0:
                continue
            b = n if n <= 4 else (8 if n <= 8 else (16 if n <= 16 else 99))
            by[b][0] += hit
            by[b][1] += 1
    for b in sorted(by):
        print(f'consistent found <= {b:>2}: picks {by[b][1]:6d}  correct {by[b][0] / by[b][1]:.3f}')


if __name__ == '__main__':
    sys.exit(main())
