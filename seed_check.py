"""Two checks on a seed after a run, both scoring only.

1. Fresh held-out, per area: the carried state against the state the seed
   started from (its initial language, no model, no prior) on a held-out set
   it never proved against.
2. What it invented: each kept invented atom labelled by the true family whose
   atom it reproduces (or 'novel'); labels never reach the seed.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter

from rsi.common import ROOT, write_json
from rsi.mechanism_space import FULL, atom_expressions, mask_of
from rsi.seed import Seed, make_area


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--areas', default='mech')
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--per-pool', type=int, default=24)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    seed = Seed(ROOT / 'seeds' / args.name)
    out = {'name': args.name, 'version': seed.state['version'], 'budget': args.budget, 'areas': {},
           'lives': {a: seed.lives(a) for a in seed.state['areas']}, 'resource': seed.state['resource'],
           'kept_changes': seed.state['kept']}
    for name in args.areas.split(','):
        area = make_area(name, args.seed)
        fresh = area.held_out(args.per_pool, salt=999)
        start = seed.candidate()
        start['language'] = start['initial_language']
        start['areas'] = {area.name: {'model': None, 'prior': False, 'held_out_score': None}}
        before = seed.score(seed.run(fresh, args.budget, area.name, state=start), fresh, args.budget)
        after = seed.score(seed.run(fresh, args.budget, area.name), fresh, args.budget)
        out['areas'][area.name] = {'start': before, 'carried': after, 'gain': after['total'] - before['total']}
        print(area.name, 'fresh held-out', before['total'], '->', after['total'], flush=True)
    family = {}
    for key, fam, expr in atom_expressions():
        m = mask_of(expr)
        family[m] = fam
        family[FULL & ~m] = fam
    kept = [a for a in seed.state['language'] if a[0].startswith('inv:')]
    out['invented'] = {'kept': len(kept),
                       'by_true_family': dict(Counter(family.get(mask_of(a[2]), 'novel') for a in kept))}
    write_json(ROOT / f'analysis/seed-check-{args.name}.json', out)
    print(json.dumps({k: v for k, v in out.items() if k != 'kept_changes'}, indent=1))


if __name__ == '__main__':
    sys.exit(main())
