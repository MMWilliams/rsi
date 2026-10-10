"""The completeness benchmark under the agent's own world distribution: worlds
drawn from the family triples its training worlds used (80% of the viable
ones; the rest are reserved as untrained combinations), no held-out mechanism
removal, the agent's own tie-break. `mechanism_world_benchmark.py` drew from
every viable triple, so its family mix differs from the agent's experience by
construction (seed 644101: mod in 47% of its worlds against 35% in training)
and a world model true to that experience is scored wrong by it. Two
independent halves as before.
"""
from __future__ import annotations

import multiprocessing
import os
import random
import sys

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import Simulator, draw_worlds
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf
import mechanism_self_simulation as sim

SEEDS = (643101, 644101, 645101)
WORLDS = 1600
OUT = ROOT / 'analysis/mechanism-world-benchmark-trained-20261010.json'
conf.WORKERS = int(os.environ.get('RSI_WORKERS', conf.WORKERS))   # each worker commits ~1.6 GB


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    result = {}
    for seed in SEEDS:
        *_, training, _s, _e, _h, _p, new_triples = conf.setup(harness, seed)
        pool = sorted({w['triple'] for w in training})
        assert not set(pool) & set(new_triples)
        rng = random.Random(seed + 4343)
        worlds = draw_worlds(harness, pool, WORLDS, rng, conf.KEYS_PER_WORLD,
                             conf.MINIMUM_MEMBERS, conf.EARN_STREAM)
        with multiprocessing.get_context('spawn').Pool(conf.WORKERS, initializer=sim._init_self,
                                                       initargs=(seed, seed * 10 + 4)) as p:
            out = p.map(sim._earn_self, [(i, w['stream']) for i, w in enumerate(worlds)],
                        chunksize=8)
        halves = []
        for part in (range(0, WORLDS, 2), range(1, WORLDS, 2)):
            present, found = np.zeros(keys), np.zeros(keys)
            for i in part:
                got = set(conf.earned_set(out[i], simulator.row_keys, 1))
                for k in (harness.key_index[n] for n in worlds[i]['keys']):
                    present[k] += 1
                    found[k] += k in got
            halves.append({'present': present.tolist(), 'found': found.tolist()})
        result[str(seed)] = {'pool': [list(t) for t in pool], 'halves': halves}
        print(seed, 'done', len(pool), 'triples', flush=True)
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
