"""A second evaluation draw for the review-002 arms.

Every reported number so far comes from one draw (salt 999) of 24 worlds per
pool. This scores the same retained states again on a salt that no life, proof,
meta-test or check has used, and saves the hits of every world.

Committed with its salt before any state was scored on it. The preregistered
rules were read on salt 999 and their verdicts stand whatever this shows; the
second draw is reported beside them, never instead. Reported per seed:
G of every arm on the new draw; the paired 95% bootstrap interval of
G(arm) - G(full), resampling worlds within pools, with a difference called
ahead or behind only when that interval excludes zero; and a start with nothing
withheld (every generator atom, no model, no prior), which measures how much of
the growth the two withheld families give back before anything is learned.

  second_draw.py score   scores, about 40 minutes at RSI_WORKERS=6; resumes
  second_draw.py         summarises the saved hits
"""
import json
import sys
import warnings

import numpy as np

from rsi.common import ROOT, write_json
from summarize_arms import AREAS, TAGS

SALT, PER_POOL, BUDGET, DRAWS = 20001, 24, 1024, 10_000
ARMS = ('full', 'accept-all', 'point', 'matched', 'no-guidance', 'no-invention', 'frequency')   # frequency last: use_arm patches the workers for good
HITS = ROOT / 'analysis/second-draw-hits.json'
OUT = ROOT / 'analysis/review002-second-draw.json'


def score():
    # imported here so that summarising the saved hits needs only numpy, not the agent or the vendored string language
    from rsi.mechanism_space import atom_expressions
    from rsi.seed import Seed, make_area
    from rsi.seed_arms import use_arm
    from rsi.seed_string import GENERATOR_KEYS
    OPEN = [list(a) for a in atom_expressions()] + [[f'str:{k}', 'str', k] for k in GENERATOR_KEYS]
    warnings.filterwarnings('ignore')
    out = json.loads(HITS.read_text()) if HITS.exists() else {'salt': SALT, 'per_pool': PER_POOL, 'pools': {}, 'hits': {}}
    assert (out['salt'], out['per_pool']) == (SALT, PER_POOL)

    def hits(key, seed, worlds, area, state=None):
        if key not in out['hits']:
            out['hits'][key] = [r['hits'] for r in seed.run(worlds, BUDGET, area, state=state)]
            write_json(HITS, out)
            print(key, sum(out['hits'][key]), flush=True)

    for arm in ARMS:
        use_arm(arm)
        for tag in TAGS:
            seed = Seed(ROOT / 'seeds' / f'{arm}_{tag}')
            for name in AREAS:
                worlds = make_area(name, seed.state['seed']).held_out(PER_POOL, salt=SALT)
                out['pools'][f'{tag}/{name}'] = [w['pool'] for w in worlds]
                if arm == 'full':   # the two starts are the same for every arm of a seed
                    for label, language in (('start', seed.state['initial_language']), ('open', OPEN)):
                        state = seed.candidate()
                        state['language'] = language
                        state['areas'] = {name: {'model': None, 'prior': False, 'held_out_score': None}}
                        hits(f'{label}/{tag}/{name}', seed, worlds, name, state)
                hits(f'{arm}/{tag}/{name}', seed, worlds, name)


def interval(values):
    return [float(x) for x in np.percentile(values, [2.5, 97.5])]


def summarize():
    d = json.loads(HITS.read_text())
    first = json.loads((ROOT / 'analysis/review002-arms.json').read_text())['arms']
    rng = np.random.default_rng(SALT)
    runs = {}
    for tag in TAGS:
        pools = {a: np.array(d['pools'][f'{tag}/{a}']) for a in AREAS}
        # one set of resampled worlds per area, shared by every state, so differences are paired
        index = {a: np.concatenate([rng.choice(np.flatnonzero(p == pool), size=(DRAWS, int((p == pool).sum())))
                                    for pool in sorted(set(p))], axis=1) for a, p in pools.items()}

        def hits(label):
            return {a: np.array(d['hits'][f'{label}/{tag}/{a}']) for a in AREAS}

        def logs(h):   # ln of the total per area: row 0 observed, the rest resampled
            return np.log(np.array([np.concatenate(([h[a].sum()], h[a][index[a]].sum(axis=1))) for a in AREAS])).T

        first_hits = hits('start')
        start, full = logs(first_hits), logs(hits('full'))
        runs[tag] = {}
        for arm in ARMS + ('open',):
            h = hits(arm)
            mine = logs(h)
            g, diff = (mine - start).mean(axis=1), (mine - full).mean(axis=1)
            pool_ratio = {f'{a}/{pool}': float(h[a][p == pool].sum() / first_hits[a][p == pool].sum())
                          for a, p in pools.items() for pool in sorted(set(p))}
            row = {'G': float(g[0]), 'G_interval': interval(g[1:]), 'min_pool_ratio': min(pool_ratio.values()),
                   'pools_below_start': {k: v for k, v in pool_ratio.items() if v < 1},
                   'area_ratio': dict(zip(AREAS, (float(x) for x in np.exp(mine[0] - start[0]))))}
            if arm in first:
                row['G_first_draw'] = first[arm]['runs'][tag]['G']
            if arm not in ('full', 'open'):
                low, high = interval(diff[1:])
                row.update(G_minus_full=float(diff[0]), G_minus_full_interval=[low, high],
                           verdict='ahead' if low > 0 else 'behind' if high < 0 else 'tie')
            if arm == 'open':   # what the withheld atoms alone give back, and where full stands against that start
                row.update(full_over_open=dict(zip(AREAS, (float(x) for x in np.exp(full[0] - mine[0])))),
                           G_full_minus_open=float(-diff[0]), G_full_minus_open_interval=interval(-diff[1:]))
            runs[tag][arm] = row
    arms = {arm: {'mean_G': float(np.mean([runs[t][arm]['G'] for t in TAGS])),
                  'verdicts': [runs[t][arm].get('verdict') for t in TAGS]} for arm in ARMS + ('open',)}
    write_json(OUT, {'salt': SALT, 'per_pool': PER_POOL, 'draws': DRAWS, 'tags': TAGS, 'arms': arms, 'runs': runs})
    for arm, a in arms.items():
        print(f'{arm:13s} G {a["mean_G"]:.3f}  ' + '  '.join(
            f'{runs[t][arm].get("G_minus_full", 0):+.3f} {runs[t][arm].get("verdict", "")}' for t in TAGS))


if __name__ == '__main__':
    score() if sys.argv[1:] == ['score'] else summarize()
