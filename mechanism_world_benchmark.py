"""Benchmark for world-model completeness: the agent's discovery rate per atom
in worlds from the TRUE generator under test conditions (no held-out removal),
with the agent's own tie-break. A world model is complete to the extent that
self-simulation inside it reproduces these rates. Ground truth for scoring
only; never given to the agent. Two independent halves are saved so the
benchmark's own reliability is the ceiling any model can be held to.
"""
from __future__ import annotations

import multiprocessing
import random
import sys

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import Simulator, draw_worlds, triples
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf
import mechanism_self_simulation as sim

SEEDS = (643101, 644101, 645101)
WORLDS = 1600
OUT = ROOT / 'analysis/mechanism-world-benchmark-20261005.json'


def main():
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    result = {}
    for seed in SEEDS:
        rng = random.Random(seed + 4242)
        seen = [f for f in harness.by_family if f not in conf.HELD_OUT_FAMILIES]
        pool = triples(harness, seen, rng, conf.KEYS_PER_WORLD, conf.MINIMUM_MEMBERS)
        worlds = draw_worlds(harness, pool, WORLDS, rng, conf.KEYS_PER_WORLD,
                             conf.MINIMUM_MEMBERS, conf.EARN_STREAM)
        with multiprocessing.get_context('spawn').Pool(conf.WORKERS, initializer=sim._init_self,
                                                       initargs=(seed, seed * 10 + 3)) as p:
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
        result[str(seed)] = halves
        print(seed, 'done', flush=True)
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
