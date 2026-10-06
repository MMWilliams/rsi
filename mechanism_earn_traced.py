"""Re-earn every training world of the three dev seeds with the full trace
(pick, hit, consistent hypotheses found), cached per seed. Identical picks to
the original earning (same tie-break, same task draws)."""
from __future__ import annotations

import json
import multiprocessing
import sys

from rsi.common import ROOT, write_json
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf
from mechanism_pick_confidence import _earn, _init

SEEDS = (643101, 644101, 645101)


def path(seed):
    return ROOT / f'analysis/mechanism-earn-traced-{seed}.json'


def load(seed):
    return json.loads(path(seed).read_text())['earning']


def main():
    h = Harness()
    for seed in SEEDS:
        if path(seed).exists():
            continue
        _r, _g, _t, _s, streams, *_ = conf.setup(h, seed)
        with multiprocessing.get_context('spawn').Pool(12, initializer=_init, initargs=(seed,)) as p:
            out = p.map(_earn, list(enumerate(streams)), chunksize=8)
        write_json(path(seed), {'seed': seed, 'earning': out})
        print(seed, 'cached', flush=True)


if __name__ == '__main__':
    sys.exit(main())
