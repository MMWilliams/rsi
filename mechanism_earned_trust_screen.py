"""Screen: how much should the agent trust an earned grouping?

C-earned failed on safety: the earned grouping loses significantly to the
champion at 256-512 with the hedge at half and group weight 2. Grid over the
hedge share (0.5, 0.75) and group weight (2, 1, 0.5) at budgets above 128, on
the two opened development seeds with their earning reused. A configuration is
a candidate only if no cell is significantly below the champion on either seed;
among those, report the pooled gain. Development screen; the confirmation seeds
991101/992101 are not touched.
"""
from __future__ import annotations

import json
import multiprocessing
import sys
import warnings
from dataclasses import replace

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, UNHEDGED, Simulator
from rsi.mechanism_worlds import Harness
from rsi.learned_groups import LearnedFamilySimulator
import mechanism_earned_confirmation as conf

SEEDS = (643101, 644101)
HEDGES = (.5, .75)
WEIGHTS = (2., 1., .5)
EVAL_PER_SPLIT = 64
OUT = ROOT / 'analysis/mechanism-earned-trust-screen-20261005.json'
_STATE = {}


def earning_of(seed, streams):
    dest = ROOT / f'runs/mechanism-earned-confirmation-dev-{seed}'
    cache = dest / 'earning-dev.json'
    if cache.exists():
        saved = json.loads(cache.read_text())
        assert saved['streams'] == streams
        return saved['earning']
    rows = {}
    with (dest / 'decisions-dev.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] != 'earn':
                break
            rows[row['world']] = row
    assert [rows[w]['stream'] for w in range(len(streams))] == streams
    return [rows[w]['decisions'] for w in range(len(streams))]


def _init(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    agents = {'champion': Simulator(harness)}
    agents.update({w: LearnedFamilySimulator(harness, labels, w, conf.SLIP) for w in WEIGHTS})
    _STATE.update(prior=prior, views=views, agents=agents)


def _live(key):
    s = _STATE
    out = {'champion': [int(s['agents']['champion'].lifetime(
        CHAMPION, s['views'][key], s['prior'], b).sum()) for b in conf.BUDGETS]}
    for hedge in HEDGES:
        for weight in WEIGHTS:
            row = []
            for b in conf.BUDGETS:
                coach = UNHEDGED if b <= 128 else replace(CHAMPION, hedge=hedge)
                row.append(int(s['agents'][weight].lifetime(coach, s['views'][key],
                                                             s['prior'], b).sum()))
            out[f'h{hedge}w{weight}'] = row
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
        rng, groups, _training, _solved, streams, _handed, prior, _new = conf.setup(harness, seed)
        earned = [conf.earned_set(d, simulator.row_keys, conf.MINIMUM_PICKS)
                  for d in earning_of(seed, streams)]
        labels, count = conf.grouping(conf.confident(earned), keys)
        views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng)
                 for split, worlds in groups.items() for n, world in enumerate(worlds)
                 if n < EVAL_PER_SPLIT}
        order = list(views)
        with multiprocessing.get_context('spawn').Pool(
                conf.WORKERS, initializer=_init, initargs=(seed, prior, views, labels)) as pool:
            lives = dict(zip(order, pool.map(_live, order, chunksize=1)))
        arms = list(lives[order[0]])
        totals = {split: {arm: np.array([lives[k][arm] for k in order
                                         if k.startswith(split + ':')]) for arm in arms}
                  for split in conf.SPLITS}
        block = {}
        for arm in arms[1:]:
            cells = {split: conf.paired(totals[split][arm], totals[split]['champion'], seed + 3)
                     for split in conf.SPLITS}
            block[arm] = {'cells': cells,
                          'worst_high': min(min(c['high']) for c in cells.values()),
                          'unsafe_cells': sum(h < 0 for c in cells.values() for h in c['high']),
                          'pooled': conf.pooled(totals, arm, 'champion', seed + 4)}
        result[str(seed)] = {'groups': int(count), 'arms': block}
        print(f'seed {seed}, groups {count}', flush=True)
        for arm, b in block.items():
            p = b['pooled']
            print(f'  {arm:10s} unsafe cells {b["unsafe_cells"]}  worst upper {b["worst_high"]:+.0f}'
                  f'  pooled {p["sum"]:+.0f} [{p["low"]:.0f}, {p["high"]:.0f}]', flush=True)
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
