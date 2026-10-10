"""What each group count buys: groups against families, held-out likelihood,
and the family presence the fitted model implies for imagined worlds, against
the true generator. Seed 644101, confident picks. No agent simulation."""
import sys, warnings
from collections import Counter
import numpy as np
from sklearn.metrics import adjusted_rand_score
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix, fit_restarts
from mechanism_earn_traced import load
SEED = 644101
TRAIN = 1280
TRUE = {'bit': (.36, 1.38), 'divmod': (.43, 2.90), 'gcd': (.44, 1.03), 'mod': (.47, 4.42),
        'parity': (.49, 1.83), 'rotmod': (.35, .62), 'threshold': (.47, 1.82)}


def main():
    warnings.filterwarnings('ignore')
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in s.row_keys[p]}) for w in load(SEED)]
    held = _matrix(sets[TRAIN:], K)
    for g in (6, 7, 8, 9):
        m, trace = fit_restarts(sets[:TRAIN], K, g, restarts=4)
        grouped = m.labels >= 0
        print(f'groups {g}: held-out ll {m.log_likelihood(held):.0f}  train ll {trace[-1]:.0f}  '
              f'ARI {adjusted_rand_score(fam[grouped], m.labels[grouped]):.3f}  atoms {int(grouped.sum())}')
        for k in range(g):
            print('   ', k, Counter(fams[f] for f in fam[m.labels == k]).most_common(4))
        rng = np.random.default_rng(1)
        worlds = m.sample_worlds(1600, rng)
        counts = np.array([np.bincount(fam[w], minlength=len(fams)) for w in worlds])
        print('    family     present  true   atoms/world  true')
        for f, name in enumerate(fams):
            if name in TRUE:
                print(f'    {name:10s} {(counts[:, f] > 0).mean():6.2f}  {TRUE[name][0]:.2f}   '
                      f'{counts[:, f].mean():6.2f}  {TRUE[name][1]:.2f}')
        print(flush=True)


if __name__ == '__main__':
    sys.exit(main())
