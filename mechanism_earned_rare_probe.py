"""Development: leave rarely earned atoms ungrouped.

PMI cancels per-atom discovery rates when discovery is independent across atoms,
so the earned groupings' failure on seed 643101 is more likely that hard-family
atoms are earned in too few worlds to cluster, get placed in a wrong group, and
steer the posterior. Here atoms earned in fewer than c training worlds are
dropped before learning, so they join the unseen group the agent treats
neutrally. Label-free: c reads only the agent's own earned sets. Reuses the
rehearsal's journaled earning; development evidence on the opened seed.
"""
from __future__ import annotations

import json
import multiprocessing
import sys
import warnings
from collections import Counter

import numpy as np
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import Simulator
from rsi.learned_groups import learn_groups
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf

SEED = 643101
MINIMA = (1, 3)
CUTS = (0, 10, 25, 50)
EVAL_PER_SPLIT = 48
OUT = ROOT / f'analysis/mechanism-earned-rare-probe-{SEED}.json'
JOURNAL = ROOT / f'runs/mechanism-earned-confirmation-dev-{SEED}/decisions-dev.jsonl'


def _init(seed, prior, views, labels):
    conf.GROUPED = tuple(labels)
    conf._init_live(seed, prior, views, labels)


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    rng, groups, _training, _solved, streams, handed, prior, _new = conf.setup(harness, SEED)
    earning = {}
    with JOURNAL.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] != 'earn':
                break
            earning[row['world']] = row['decisions']
    keys = len(harness.key_names)
    families = sorted(harness.by_family)
    family_of = np.array([families.index(k.split(':')[0]) for k in harness.key_names])

    def learn(sets):
        lab, count = learn_groups(sets, keys, choices=conf.GROUP_CHOICES, select='likelihood')
        mask = lab >= 0
        return lab, {'groups': int(count), 'assigned': int(mask.sum()),
                     'ari': float(adjusted_rand_score(family_of[mask], lab[mask]))}

    labels, quality = {}, {}
    labels['handed'], quality['handed'] = learn(handed)
    for m in MINIMA:
        sets = [conf.earned_set(earning[w], simulator.row_keys, m) for w in range(len(streams))]
        worlds_with = Counter(k for s in sets for k in s)
        for c in CUTS:
            kept = [[k for k in s if worlds_with[k] >= c] for s in sets]
            name = f'm{m}c{c}'
            labels[name], quality[name] = learn(kept)
            print(name, quality[name], flush=True)

    views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng, examples=True)
             for split, worlds in groups.items() for n, world in enumerate(worlds)
             if n < EVAL_PER_SPLIT}
    order = list(views)
    arms = ('champion',) + tuple(labels)
    with multiprocessing.get_context('spawn').Pool(
            conf.WORKERS, initializer=_init, initargs=(SEED, prior, views, labels)) as pool:
        lives = dict(zip(order, pool.map(conf._live, order, chunksize=1)))
    totals = {split: {arm: np.array([[sum(h for _p, h in d) for d in lives[k][arm]]
                                     for k in order if k.startswith(split + ':')])
                      for arm in arms} for split in conf.SPLITS}
    contrasts = {arm: {split: conf.paired(totals[split][arm], totals[split]['champion'],
                                          SEED + 3) for split in conf.SPLITS}
                 for arm in arms[1:]}
    overall = {arm: conf.pooled(totals, arm, 'champion', SEED + 4) for arm in arms[1:]}
    write_json(OUT, {'seed': SEED, 'scope': 'development, opened seed', 'quality': quality,
                     'contrasts': contrasts, 'pooled_vs_champion': overall})
    for arm in arms[1:]:
        print(f'{arm} {quality[arm]} minus champion, pooled {overall[arm]["sum"]:+.0f} '
              f'[{overall[arm]["low"]:.0f}, {overall[arm]["high"]:.0f}]')
        for split in conf.SPLITS:
            e = contrasts[arm][split]
            print('  {:12s}'.format(split) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))


if __name__ == '__main__':
    sys.exit(main())
