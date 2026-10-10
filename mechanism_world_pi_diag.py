"""Is the world model's picture of family mix wrong, or is the benchmark drawn
from a different mix? Training worlds use 80% of the viable family triples; the
benchmark uses all of them. Seed 644101, confident picks, 7 groups."""
import sys, warnings
from collections import Counter
import numpy as np
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix, fit_restarts
import mechanism_earned_confirmation as conf
from mechanism_earn_traced import load
SEED = 644101
TRAIN = 1280
BENCH = {'bit': (.36, 1.38), 'divmod': (.43, 2.90), 'gcd': (.44, 1.03), 'mod': (.47, 4.42),
         'parity': (.49, 1.83), 'rotmod': (.35, .62), 'threshold': (.47, 1.82)}


def mix(fam, fams, worlds):
    counts = np.array([np.bincount(fam[w], minlength=len(fams)) for w in worlds])
    return (counts > 0).mean(0), counts.mean(0)


def main():
    warnings.filterwarnings('ignore')
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    _r, _g, training, _s, _e, _h, _p, new_triples = conf.setup(h, SEED)
    print('new (untrained) triples:', new_triples)
    tw = [[h.key_index[k] for k in w['keys']] for w in training[:TRAIN]]
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in s.row_keys[p]}) for w in load(SEED)]
    m, _ = fit_restarts(sets[:TRAIN], K, 7, restarts=4)
    name_of = [Counter(fams[f] for f in fam[m.labels == g]).most_common(1)[0][0] if (m.labels == g).any() else '?'
               for g in range(m.groups)]
    print('group names:', name_of)
    worlds = m.sample_worlds(1600, np.random.default_rng(1))
    tp, ta = mix(fam, fams, tw); ip, ia = mix(fam, fams, worlds)
    print('family     train-present imagined  bench | train-atoms imagined bench')
    for f, n in enumerate(fams):
        if n in BENCH:
            print(f'{n:10s} {tp[f]:8.2f} {ip[f]:8.2f} {BENCH[n][0]:6.2f} | {ta[f]:8.2f} {ia[f]:8.2f} {BENCH[n][1]:6.2f}')
    train_triples = Counter(w['triple'] for w in training[:TRAIN])
    pi = Counter()
    for t, p in zip(m.triples, m.pi):
        pi[tuple(sorted(name_of[g] for g in t))] += p
    print('triple                              train  pi')
    for t, c in sorted(train_triples.items(), key=lambda x: -x[1]):
        print(f'{str(t):36s} {c / TRAIN:5.3f} {pi.get(t, 0):5.3f}')
    extra = {t: p for t, p in pi.items() if t not in train_triples and p > .005}
    print('pi mass on group sets that are not a training triple:', round(sum(extra.values()), 3), extra)
    post, _ = m.world_posterior(_matrix(sets[:TRAIN], K))
    guess = [tuple(sorted(name_of[g] for g in m.triples[i])) for i in post.argmax(1)]
    truth = [w['triple'] for w in training[:TRAIN]]
    print('posterior triple = true triple:', round(np.mean([g == t for g, t in zip(guess, truth)]), 3))
    wrong = Counter((t, g) for g, t in zip(guess, truth) if g != t)
    print('most common confusions (true -> guessed):', wrong.most_common(6))


if __name__ == '__main__':
    sys.exit(main())
