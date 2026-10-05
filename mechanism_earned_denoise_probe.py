"""Development: denoise earned atom sets by recurrence across the world's picks.

The rehearsal of `mechanism_earned_confirmation.py` on seed 643101 failed:
earned sets at 4096 are 63% precise and groups learned from them lose to the
champion at 256-512, with 1,600 earned worlds worse than 400. Keeping only atoms
that recur in at least m of a world's own picks raises precision to 0.86 (m=2)
and 0.94 (m=3) on that journal, from the picks alone. This re-evaluates m in
{1, 2, 3} from the rehearsal's journaled earning, without earning again.
Development evidence on an opened seed; the frozen choice is rehearsed on a
fresh one.
"""
from __future__ import annotations

import json
import multiprocessing
import sys
import warnings

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import Simulator
from rsi.learned_groups import learn_groups
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf

SEED = 643101
MINIMA = (1, 2, 3)
OUT = ROOT / f'analysis/mechanism-earned-denoise-probe-{SEED}.json'
JOURNAL = ROOT / f'runs/mechanism-earned-confirmation-dev-{SEED}/decisions-dev.jsonl'


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    rng, groups, training, _solved, streams, handed, prior, _new = conf.setup(harness, SEED)
    earning = {}
    with JOURNAL.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['kind'] != 'earn':
                break
            earning[row['world']] = row
    assert [earning[w]['stream'] for w in range(len(streams))] == streams
    keys = len(harness.key_names)
    true_sets = [{harness.key_index[k] for k in w['keys']} for w in training]
    labels, quality = {}, {}
    labels['handed'], _ = learn_groups(handed, keys, choices=conf.GROUP_CHOICES,
                                       select='likelihood')
    for m in MINIMA:
        sets = [conf.earned_set(earning[w]['decisions'], simulator.row_keys, m)
                for w in range(len(streams))]
        for name, part in ((f'earned{m}', sets), (f'early{m}', sets[:conf.EARLY_WORLDS])):
            labels[name], count = learn_groups(part, keys, choices=conf.GROUP_CHOICES,
                                               select='likelihood')
            quality[name] = {'groups': int(count)}
        nonempty = [(s, true_sets[w]) for w, s in enumerate(sets) if s]
        quality[f'earned{m}'].update(
            precision=float(np.mean([len(set(s) & t) / len(s) for s, t in nonempty])),
            mean_atoms=float(np.mean([len(s) for s in sets])))
    print('quality', quality, flush=True)

    views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng, examples=True)
             for split, worlds in groups.items() for n, world in enumerate(worlds)}
    order = list(views)
    conf.GROUPED = tuple(labels)
    arms = ('champion',) + conf.GROUPED
    with multiprocessing.get_context('spawn').Pool(
            conf.WORKERS, initializer=_init, initargs=(SEED, prior, views, labels)) as pool:
        lives = dict(zip(order, pool.map(conf._live, order, chunksize=1)))
    totals = {split: {arm: np.array([[sum(h for _p, h in d) for d in lives[k][arm]]
                                     for k in order if k.startswith(split + ':')])
                      for arm in arms} for split in conf.SPLITS}
    contrasts = {arm: {split: conf.paired(totals[split][arm], totals[split]['champion'],
                                          SEED + 3) for split in conf.SPLITS}
                 for arm in arms[1:]}
    growth = {m: conf.pooled(totals, f'earned{m}', f'early{m}', SEED + 4) for m in MINIMA}
    write_json(OUT, {'seed': SEED, 'scope': 'development, opened seed', 'quality': quality,
                     'contrasts': contrasts, 'growth': {str(m): g for m, g in growth.items()}})
    for arm in arms[1:]:
        print(f'{arm} minus champion')
        for split in conf.SPLITS:
            e = contrasts[arm][split]
            print('  {:12s}'.format(split) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))
    for m, g in growth.items():
        print(f'growth m={m}: {g["sum"]:+.0f} [{g["low"]:.0f}, {g["high"]:.0f}]')


def _init(seed, prior, views, labels):
    conf.GROUPED = tuple(labels)
    conf._init_live(seed, prior, views, labels)


if __name__ == '__main__':
    sys.exit(main())
