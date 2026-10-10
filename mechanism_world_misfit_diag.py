"""Which atoms does the misfit restart free a group for, and where do the
rotmod atoms rank? Seed 644101, confident picks, 7 groups."""
import sys, warnings
from collections import Counter
import numpy as np
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _atom_scores, _matrix, fit_restarts
from mechanism_earn_traced import load
SEED = 644101
TRAIN = 1280


def main():
    warnings.filterwarnings('ignore')
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in s.row_keys[p]}) for w in load(SEED)]
    earned = _matrix(sets[:TRAIN], K)
    m, _ = fit_restarts(sets[:TRAIN], K, 7, restarts=4)
    post, _ = m.world_posterior(earned)
    score, none = _atom_scores(m, earned, post)
    grouped = np.flatnonzero(m.labels >= 0)
    for name, margin in (('per atom', score.max(0) - none),
                         ('per earn', (score.max(0) - none) / np.maximum(earned.sum(0), 1.))):
        order = grouped[np.argsort(margin[grouped])]
        rank = {int(k): i for i, k in enumerate(order)}
        print(name, 'worst 12:', [(fams[fam[k]], round(float(margin[k]), 1), int(earned[:, k].sum())) for k in order[:12]])
        rot = [k for k in grouped if fams[fam[k]] == 'rotmod']
        print('   rotmod ranks of', len(grouped), ':', sorted(rank[int(k)] for k in rot),
              'earns', [int(earned[:, k].sum()) for k in rot], 'r', [round(float(m.r[k]), 2) for k in rot])
    mod = [k for k in grouped if fams[fam[k]] == 'mod']
    print('mod earns: median', int(np.median(earned[:, mod].sum(0))), 'min', int(earned[:, mod].sum(0).min()))


if __name__ == '__main__':
    sys.exit(main())
