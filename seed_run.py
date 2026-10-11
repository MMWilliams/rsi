"""Run the seed for some lives in the mechanism area and report what it kept.

Each life: live (earn in fresh worlds), extend (invent atoms for the worlds it
could not solve, prove, keep if better), reflect (refit the world and self
model and the prior from all experience, prove, keep if better). The state is
saved after every operation, so a run can be resumed, and the ledger records
every candidate change with its held-out score against the carried state.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings

from rsi.common import ROOT
from rsi.invention import candidates
from rsi.seed import MechanismArea, Seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--lives', type=int, default=4)
    ap.add_argument('--worlds', type=int, default=48)
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--held-out', type=int, default=24)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    area = MechanismArea(args.seed)
    seed = Seed(ROOT / 'seeds' / args.name, language=area.seed_language, name=args.name)
    held = area.held_out(args.held_out)
    cands = candidates()
    print(f'seed {seed.state["name"]} version {seed.state["version"]} lives so far {seed.lives} '
          f'language {len(seed.state["language"])} atoms; {len(cands)} grammar candidates', flush=True)
    for _ in range(args.lives):
        t = time.time()
        life, worlds, records = seed.live(area, args.worlds, args.budget)
        entry = seed.state['ledger'][-1]
        print(f'life {life}: solved {entry["total"]} of {args.worlds * 100}; by pool '
              f'{json.dumps({k: round(v, 1) for k, v in entry["by_pool"].items()})}; '
              f'{time.time() - t:.0f} s', flush=True)
        atoms, tests, provenance = seed.extend(worlds, records, cands)
        if atoms:
            candidate = dict(seed.state, language=seed.state['language'] + [list(a) for a in atoms])
            kept, carried, new = seed.prove(held, candidate, args.budget, f'language +{len(atoms)} atoms',
                                            note={'tests': tests, 'atoms': [p['atom'] for p in provenance][:40],
                                                  'from_pools': sorted({p['pool'] for p in provenance})})
            print(f'  extend: {len(atoms)} atoms from {tests} tests; held-out {carried["total"]} -> {new["total"]} '
                  f'{"KEPT" if kept else "dropped"}; by pool {json.dumps({k: round(v, 1) for k, v in new["by_pool"].items()})}',
                  flush=True)
        else:
            print('  extend: nothing invented', flush=True)
        model = seed.reflect()
        if model and 'labels' in model:
            candidate = dict(seed.state, model=model, prior=True)
            kept, carried, new = seed.prove(held, candidate, args.budget,
                                            f'model g={model["groups"]} from {model["worlds"]} worlds + prior')
            print(f'  reflect: {model["groups"]} groups over {len(model["labels"])} atoms from {model["worlds"]} worlds; '
                  f'held-out {carried["total"]} -> {new["total"]} {"KEPT" if kept else "dropped"}; '
                  f'by pool {json.dumps({k: round(v, 1) for k, v in new["by_pool"].items()})}', flush=True)
        elif model:
            print(f'  reflect: fit failed {model["error"]}', flush=True)
        else:
            print(f'  reflect: too little experience ({len(seed.state["experience"])} worlds)', flush=True)
        print(f'  carried: version {seed.state["version"]}, language {len(seed.state["language"])}, '
              f'model {"yes" if seed.state["model"] else "no"}, prior {"yes" if seed.state["prior"] else "no"}, '
              f'held-out {seed.state["held_out_score"]["total"] if seed.state["held_out_score"] else "?"}; '
              f'{time.time() - t:.0f} s', flush=True)
    print('kept:', json.dumps(seed.state['kept']), flush=True)


if __name__ == '__main__':
    sys.exit(main())
