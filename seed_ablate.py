"""Which carried part moves each held-out pool? Scoring only: the seed's
carried state and ablations of it on an area's fresh held-out set."""
from __future__ import annotations

import argparse
import json
import sys
import warnings

from rsi.common import ROOT, write_json
from rsi.seed import Seed, make_area


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--area', default='mech')
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--per-pool', type=int, default=24)
    ap.add_argument('--salt', type=int, default=999)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    seed = Seed(ROOT / 'seeds' / args.name)
    area = make_area(args.area, args.seed)
    held = area.held_out(args.per_pool, salt=args.salt)
    base = seed.candidate()
    variants = {'carried': base}
    v = seed.candidate(); v['areas'][area.name]['prior'] = False; variants['no prior'] = v
    v = seed.candidate(); v['areas'][area.name]['model'] = None; variants['no model'] = v
    v = seed.candidate(); v['areas'][area.name]['model'] = None; v['areas'][area.name]['prior'] = False
    variants['language only'] = v
    v = seed.candidate(); v['language'] = v['initial_language']; variants['initial language, carried model + prior'] = v
    v = seed.candidate(); v['language'] = v['initial_language']; v['areas'][area.name]['model'] = None
    v['areas'][area.name]['prior'] = False; variants['initial'] = v
    out = {}
    for name, state in variants.items():
        score = seed.score(seed.run(held, args.budget, area.name, state=state), held, args.budget)
        out[name] = score
        print(f'{name:40s} {score["total"]:5d}  {json.dumps({k: round(x, 1) for k, x in score["by_pool"].items()})}',
              flush=True)
    write_json(ROOT / f'analysis/seed-ablate-{args.name}-{area.name}.json', out)


if __name__ == '__main__':
    sys.exit(main())
