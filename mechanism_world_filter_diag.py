"""Real against imagined worlds at the family level, before and after the
viability filter (>= MINIMUM_MEMBERS rules), and under two ways of applying it:
redraw the group set after a rejection (what `imagine` did) or keep it and
redraw the atoms, as the true generator does. Seed 644101, confident picks.
No agent simulation; only world draws."""
import itertools, random, sys, warnings
from collections import Counter
import numpy as np
from rsi.growth_coach import Simulator, draw_worlds, triples
from rsi.mechanism_space import world_members
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import fit_restarts
import mechanism_earned_confirmation as conf
from mechanism_earn_traced import load
SEED = 644101
N = 1600


def stats(fam, fams, worlds, members):
    counts = np.array([np.bincount(fam[w], minlength=len(fams)) for w in worlds])
    return {'atoms/world': counts.mean(0), 'present': (counts > 0).mean(0),
            'atoms|present': np.array([counts[counts[:, f] > 0, f].mean() if (counts[:, f] > 0).any() else 0
                                       for f in range(len(fams))]),
            'members': (np.mean(members), np.percentile(members, 10), np.percentile(members, 90))}


def show(name, s, fams):
    print(f'{name}: members mean {s["members"][0]:.0f} p10 {s["members"][1]:.0f} p90 {s["members"][2]:.0f}')
    for f, n in enumerate(fams):
        print(f'   {n:10s} present {s["present"][f]:.2f}  atoms/world {s["atoms/world"][f]:.2f}  '
              f'atoms|present {s["atoms|present"][f]:.2f}')


def members_of(h, w):
    return len(world_members(h.catalog, h.by_key, sorted(h.key_names[k] for k in w)))


def main():
    warnings.filterwarnings('ignore')
    h = Harness(); s = Simulator(h); K = len(h.key_names)
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    print({f: len(v) for f, v in h.by_family.items()})
    seen = [f for f in h.by_family if f not in conf.HELD_OUT_FAMILIES]
    rng = random.Random(SEED + 4242)
    pool = triples(h, seen, rng, conf.KEYS_PER_WORLD, conf.MINIMUM_MEMBERS)
    print('viable triples', len(pool), 'of', len(list(itertools.combinations(seen, 3))))
    real = draw_worlds(h, pool, N, rng, conf.KEYS_PER_WORLD, conf.MINIMUM_MEMBERS, conf.EARN_STREAM)
    rw = [[h.key_index[k] for k in w['keys']] for w in real]
    show('REAL (filtered, triple kept on rejection)', stats(fam, fams, rw, [len(w['members']) for w in real]), fams)
    print('  real triple marginal:', Counter(w['triple'] for w in real).most_common())
    pre, mem = [], []
    for _ in range(N):
        t = pool[rng.randrange(len(pool))]
        p = [k for f in t for k in h.by_family[f]]
        while True:
            keys = rng.sample(p, conf.KEYS_PER_WORLD)
            if {k.split(':')[0] for k in keys} == set(t):
                break
        pre.append([h.key_index[k] for k in keys])
        mem.append(len(world_members(h.catalog, h.by_key, keys)))
    show('REAL pre-filter', stats(fam, fams, pre, mem), fams)
    print('  acceptance rate overall', np.mean(np.array(mem) >= conf.MINIMUM_MEMBERS).round(2))
    sets = [sorted({int(k) for p, _h, n, _s in w if p >= 0 and n <= 1 for k in s.row_keys[p]}) for w in load(SEED)]
    m, _ = fit_restarts(sets[:1280], K, 6, restarts=4)
    print('groups:', [Counter(fams[f] for f in fam[m.labels == g]).most_common(3) for g in range(m.groups)])
    print('pi:', [(tuple(int(x) for x in t), round(float(p), 3)) for t, p in zip(m.triples, m.pi)])
    nrng = np.random.default_rng(SEED * 10 + 7)
    raw = m.sample_worlds(N, nrng)
    rmem = np.array([members_of(h, w) for w in raw])
    show('IMAGINED pre-filter', stats(fam, fams, raw, rmem), fams)
    ok = rmem >= conf.MINIMUM_MEMBERS
    print('  acceptance rate overall', ok.mean().round(2))
    show('IMAGINED filtered, group set redrawn (current)',
         stats(fam, fams, [w for w, o in zip(raw, ok) if o], rmem[ok]), fams)
    kept, kmem = [], []
    while len(kept) < N:
        index = nrng.choice(len(m.triples), p=m.pi)
        for _ in range(40):
            w = m.sample_worlds(1, nrng, triple_index=index)[0]
            n = members_of(h, w)
            if n >= conf.MINIMUM_MEMBERS:
                kept.append(w); kmem.append(n)
                break
    show('IMAGINED filtered, group set kept', stats(fam, fams, kept, kmem), fams)


if __name__ == '__main__':
    sys.exit(main())
