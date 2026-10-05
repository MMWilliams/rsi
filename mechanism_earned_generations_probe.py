"""Development: does the representation improve the experience it is learned from?

Blind earning is biased toward easy families (recall 0.74-0.84 for mod against
0.23-0.31 for rotmod and gcd on seed 643101), so groups learned from it recover
the families at ARI 0.17-0.55 against 0.87 from handed sets, and more earned
worlds make it worse. Here each generation lives fresh training worlds with the
family agent on the previous generation's groups (generation 0 lives them
blind), and the next groups are learned from that generation's earned sets
alone. The loop is closed through the agent's own picks: nothing from a
training world reaches the learner otherwise. Reported per generation: earned
precision, per-family recall, ARI of the groups against the families, and the
agent on those groups living held-out worlds next to the champion and a blind
control earned on the same number of worlds. Development evidence on the
opened seed 643101.
"""
from __future__ import annotations

import multiprocessing
import random
import sys
import warnings
from collections import Counter

import numpy as np
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import BLIND, CHAMPION, Simulator, world_seed
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf

SEED = 643101
GENERATIONS = 4
PER_GENERATION = 400
MINIMUM = 3
EVAL_PER_SPLIT = 48
OUT = ROOT / f'analysis/mechanism-earned-generations-probe-{SEED}.json'
_STATE = {}


def _init_earn(seed, prior, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    agent = Simulator(harness) if labels is None else \
        LearnedFamilySimulator(harness, labels, conf.WEIGHT, conf.SLIP)
    _STATE.update(agent=agent, seed=seed, prior=prior, blind=labels is None)


def _earn(job):
    index, stream = job
    s = _STATE
    views = s['agent'].views(stream, random.Random(world_seed(s['seed'] + 5, index)))
    trace = []
    if s['blind']:
        s['agent'].lifetime(BLIND, views, None, conf.EARN_BUDGET, trace=trace)
    else:
        s['agent'].lifetime(CHAMPION, views, s['prior'], conf.EARN_BUDGET, trace=trace)
    return [(int(d['pick']), int(d['hit'])) for d in trace]


def earn(seed, prior, labels, jobs):
    with multiprocessing.get_context('spawn').Pool(
            conf.WORKERS, initializer=_init_earn, initargs=(seed, prior, labels)) as pool:
        return pool.map(_earn, jobs, chunksize=8)


def _init(seed, prior, views, labels):
    conf.GROUPED = tuple(labels)
    conf._init_live(seed, prior, views, labels)


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    rng, groups, training, _solved, streams, _handed, prior, _new = conf.setup(harness, SEED)
    keys = len(harness.key_names)
    families = sorted(harness.by_family)
    family_of = np.array([families.index(k.split(':')[0]) for k in harness.key_names])
    truth = [{harness.key_index[k] for k in w['keys']} for w in training]

    def describe(sets, worlds, lab):
        recall, total = Counter(), Counter()
        for s, w in zip(sets, worlds):
            for k in truth[w]:
                total[families[family_of[k]]] += 1
                recall[families[family_of[k]]] += k in s
        nonempty = [(s, truth[w]) for s, w in zip(sets, worlds) if s]
        mask = lab >= 0
        return {'precision': float(np.mean([len(set(s) & t) / len(s) for s, t in nonempty])),
                'mean_atoms': float(np.mean([len(s) for s in sets])),
                'recall': {f: round(recall[f] / total[f], 3) for f in sorted(total)},
                'ari': float(adjusted_rand_score(family_of[mask], lab[mask]))}

    labels, report, blind_sets = {}, {}, []
    current = None
    for g in range(GENERATIONS):
        worlds = range(g * PER_GENERATION, (g + 1) * PER_GENERATION)
        jobs = [(w, streams[w]) for w in worlds]
        decisions = earn(SEED, prior, current, jobs)
        sets = [conf.earned_set(d, simulator.row_keys, MINIMUM) for d in decisions]
        current, count = learn_groups(sets, keys, choices=conf.GROUP_CHOICES, select='likelihood')
        labels[f'gen{g}'] = current
        report[f'gen{g}'] = {'groups': int(count), **describe(sets, worlds, current),
                             'solved_per_world': float(np.mean([sum(h for _p, h in d)
                                                                for d in decisions]))}
        if g == 0:
            blind_sets = sets
        else:
            blind = earn(SEED, None, None, jobs)
            blind_sets = blind_sets + [conf.earned_set(d, simulator.row_keys, MINIMUM)
                                       for d in blind]
        lab, count = learn_groups(blind_sets, keys, choices=conf.GROUP_CHOICES,
                                  select='likelihood')
        labels[f'blind{g}'] = lab
        report[f'blind{g}'] = {'groups': int(count),
                               **describe(blind_sets, range(len(blind_sets)), lab)}
        print(f'gen {g}:', report[f'gen{g}'], '\n  blind:', report[f'blind{g}'], flush=True)

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
    write_json(OUT, {'seed': SEED, 'scope': 'development, opened seed', 'report': report,
                     'contrasts': contrasts, 'pooled_vs_champion': overall})
    for arm in arms[1:]:
        print(f'{arm} minus champion, pooled {overall[arm]["sum"]:+.0f} '
              f'[{overall[arm]["low"]:.0f}, {overall[arm]["high"]:.0f}]')
        for split in conf.SPLITS:
            e = contrasts[arm][split]
            print('  {:12s}'.format(split) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(e['sum'], e['low'], e['high'])))


if __name__ == '__main__':
    sys.exit(main())
