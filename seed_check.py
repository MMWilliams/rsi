"""Two checks on a seed after a run, both scoring only.

1. Fresh held-out: the carried state against the state it started from on a
   held-out set it never proved against, so that adaptive reuse of the fixed
   set cannot be what the ledger's gains are.
2. What it invented: each kept invented atom labelled by the true family whose
   atom it reproduces (or 'novel'); labels never reach the seed.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import warnings
from collections import Counter

from rsi.common import ROOT, write_json
from rsi.growth_coach import world_seed
from rsi.mechanism_space import FULL, atom_expressions, mask_of
from rsi.seed import MechanismArea, Seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--per-pool', type=int, default=24)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    area = MechanismArea(args.seed)
    seed = Seed(ROOT / 'seeds' / args.name)
    rng = random.Random(args.seed + 9999)
    fresh = []
    for pool in ('trained', 'untrained', 'unfamiliar'):
        fresh += area.draw(pool, args.per_pool, rng)
    for i, w in enumerate(fresh):
        w['rng'] = world_seed(args.seed + 31, i)
    start = dict(seed.state, language=[list(a) for a in area.seed_language], model=None, prior=False)
    before = seed.score(seed.run(fresh, args.budget, state=start), fresh, args.budget)
    after = seed.score(seed.run(fresh, args.budget), fresh, args.budget)
    family = {}
    for key, fam, expr in atom_expressions():
        m = mask_of(expr)
        family[m] = fam
        family[FULL & ~m] = fam
    kept = [a for a in seed.state['language'] if a[0].startswith('inv:')]
    labels = Counter(family.get(mask_of(a[2]), 'novel') for a in kept)
    out = {'name': args.name, 'version': seed.state['version'], 'budget': args.budget,
           'fresh_held_out': {'start': before, 'carried': after,
                              'gain': after['total'] - before['total']},
           'fixed_held_out': seed.state['held_out_score'],
           'invented': {'kept': len(kept), 'by_true_family': dict(labels)},
           'kept_changes': seed.state['kept'], 'lives': seed.lives,
           'experience_worlds': len(seed.state['experience'])}
    write_json(ROOT / f'analysis/seed-check-{args.name}.json', out)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    sys.exit(main())
