"""Why do imagined worlds carry more mod atoms after the retry filter than
before it? Same model as the completeness run (644101, confident picks, 7
groups): raw draws, filtered draws, acceptance and redraws per group set."""
import sys, warnings
from collections import Counter
import numpy as np
from rsi.growth_coach import Simulator
from rsi.mechanism_space import world_members
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import fit_restarts
import mechanism_earned_confirmation as conf
from mechanism_earn_traced import load
SEED = 644101
TRAIN = 1280
N = 800


def mix(fam, fams, worlds):
    counts = np.array([np.bincount(fam[w], minlength=len(fams)) for w in worlds])
    return {fams[f]: (round(float(counts[:, f].mean()), 2), round(float((counts[:, f] > 0).mean()), 2))
            for f in range(len(fams)) if counts[:, f].sum()}


def main():
    warnings.filterwarnings('ignore')
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in s.row_keys[p]}) for w in load(SEED)]
    m, _ = fit_restarts(sets[:TRAIN], K, 7, restarts=4)
    name_of = [Counter(fams[f] for f in fam[m.labels == g]).most_common(1)[0][0] + str(int((m.labels == g).sum()))
               for g in range(m.groups)]
    rng = np.random.default_rng(SEED * 10 + 7)
    raw = m.sample_worlds(N, rng)
    print('raw      ', mix(fam, fams, raw))
    rng = np.random.default_rng(SEED * 10 + 7)
    kept, tried, accepted, exhausted, attempts_used = [], Counter(), Counter(), Counter(), []
    while len(kept) < N:
        index = int(rng.choice(len(m.triples), p=m.pi))
        name = tuple(name_of[g] for g in m.triples[index])
        tried[name] += 1
        for a in range(40):
            keys = m.sample_worlds(1, rng, triple_index=index)[0]
            n = len(world_members(h.catalog, h.by_key, sorted(h.key_names[k] for k in keys)))
            if n >= conf.MINIMUM_MEMBERS:
                kept.append(keys); accepted[name] += 1; attempts_used.append(a + 1)
                break
        else:
            exhausted[name] += 1
    print('filtered ', mix(fam, fams, kept))
    print('mean attempts per kept world', round(float(np.mean(attempts_used)), 1),
          'exhausted draws', sum(exhausted.values()), 'of', sum(tried.values()))
    print('group set                                   pi    tried accepted exhausted')
    for name, t in tried.most_common():
        pi = float(m.pi[[tuple(name_of[g] for g in tr) == name for tr in m.triples]].sum())
        print(f'{str(name):44s} {pi:.3f} {t:5d} {accepted[name]:8d} {exhausted[name]:9d}')


if __name__ == '__main__':
    sys.exit(main())
