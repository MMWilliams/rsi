"""Screen: can the agent tell, from its own grouping, how far to trust it?

At budget 512 the true-set grouping beats the champion only unhedged and the
earned grouping has no edge at any hedge, so the right hedge depends on the
representation's quality. Candidate label-free signal: split-half stability,
the adjusted Rand agreement between groupings learned (at the full grouping's
count) on two random halves of the same training sets. For several groupings
per seed, at two weights, measure the gain of trusting fully (hedge 0) over the
half hedge at budgets 256-1024. The screen passes if stability ranks that gain
(Spearman over grouping-weight pairs, every seed) and a single threshold
separates positive from negative gains on all three seeds. Development screen
on the opened seeds; no confirmation seed is touched.
"""
from __future__ import annotations

import json
import multiprocessing
import random
import sys
import warnings
from dataclasses import replace

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, Simulator
from rsi.learned_groups import LearnedFamilySimulator, learn_groups
from rsi.mechanism_worlds import Harness
import mechanism_earned_confirmation as conf
from mechanism_earned_trust_screen import earning_of

SEEDS = (643101, 644101, 645101)
BUDGETS = (256, 512, 1024)
WEIGHTS = (.5, 2.)
EVAL_PER_SPLIT = 48
SPLITS_FOR_STABILITY = 4
OUT = ROOT / 'analysis/mechanism-trust-quality-screen-20261005.json'
_STATE = {}


def stability(sets, keys, count, seed):
    """Mean split-half ARI over a few random halvings, at a fixed group count."""
    rng = random.Random(seed)
    scores = []
    for _ in range(SPLITS_FOR_STABILITY):
        order = list(range(len(sets)))
        rng.shuffle(order)
        half = len(order) // 2
        a, _ = learn_groups([sets[i] for i in order[:half]], keys, choices=[count],
                            select='likelihood')
        b, _ = learn_groups([sets[i] for i in order[half:]], keys, choices=[count],
                            select='likelihood')
        both = (a >= 0) & (b >= 0)
        scores.append(adjusted_rand_score(a[both], b[both]) if both.sum() > count else 0.)
    return float(np.mean(scores))


def _init(seed, prior, views, labels):
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    agents = {'champion': Simulator(harness)}
    for name, lab in labels.items():
        for w in WEIGHTS:
            agents[f'{name}|w{w}'] = LearnedFamilySimulator(harness, lab, w, conf.SLIP)
    _STATE.update(prior=prior, views=views, agents=agents)


def _live(key):
    s = _STATE
    out = {}
    for b in BUDGETS:
        out[f'champion|{b}'] = int(s['agents']['champion'].lifetime(
            CHAMPION, s['views'][key], s['prior'], b).sum())
        for name, agent in s['agents'].items():
            if name == 'champion':
                continue
            for hedge in (0., .5):
                out[f'{name}|h{hedge}|{b}'] = int(agent.lifetime(
                    replace(CHAMPION, hedge=hedge), s['views'][key], s['prior'], b).sum())
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

        def bar(sets, c):
            from collections import Counter
            n = Counter(k for s in sets for k in s)
            return [[k for k in s if n[k] >= c] for s in sets]

        sources = {'handed1600': handed, 'handed400': handed[:400],
                   'earned_c50': bar(earned, 50), 'earned_c25': bar(earned, 25),
                   'earned800_c50': bar(earned[:800], 50)}
        labels, quality = {}, {}
        for name, sets in sources.items():
            lab, count = conf.grouping(sets, keys)
            if lab is None:
                continue
            labels[name] = lab
            quality[name] = {'groups': int(count),
                             'stability': stability(sets, keys, count, seed + 1)}
            print(seed, name, quality[name], flush=True)
        views = {f'{split}:{n:03d}': simulator.views(world['stream'], rng)
                 for split, worlds in groups.items() for n, world in enumerate(worlds)
                 if n < EVAL_PER_SPLIT}
        order = list(views)
        with multiprocessing.get_context('spawn').Pool(
                conf.WORKERS, initializer=_init, initargs=(seed, prior, views, labels)) as pool:
            lives = dict(zip(order, pool.map(_live, order, chunksize=1)))
        rows = []
        for name in labels:
            for w in WEIGHTS:
                arm = f'{name}|w{w}'
                full = sum(lives[k][f'{arm}|h0.0|{b}'] for k in order for b in BUDGETS)
                half = sum(lives[k][f'{arm}|h0.5|{b}'] for k in order for b in BUDGETS)
                champ = sum(lives[k][f'champion|{b}'] for k in order for b in BUDGETS)
                rows.append({'arm': arm, 'stability': quality[name]['stability'],
                             'trust_gain': full - half, 'full_vs_champion': full - champ,
                             'half_vs_champion': half - champ})
        rho = spearmanr([r['stability'] for r in rows], [r['trust_gain'] for r in rows])
        result[str(seed)] = {'quality': quality, 'rows': rows, 'spearman': float(rho.statistic)}
        print(f'seed {seed}: spearman(stability, trust gain) = {rho.statistic:+.2f}')
        for r in sorted(rows, key=lambda r: r['stability']):
            print('  {arm:22s} stability {stability:.3f}  trust gain {trust_gain:+6d}  '
                  'full {full_vs_champion:+6d}  half {half_vs_champion:+6d}'.format(**r),
                  flush=True)
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
