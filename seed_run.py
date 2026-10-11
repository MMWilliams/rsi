"""Run the seed for some lives in one area and report what it kept.

Each life: live (earn in fresh worlds), extend (invent atoms for the worlds it
could not solve; prove), prune (drop invented atoms that never earned their
keep; prove), reflect (refit the area's model and prior; prove). Every proof
is on a held-out set drawn fresh for that life. The state is saved after every
operation, so a run resumes, and the ledger records every candidate change
with its held-out score against the carried state.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings

from rsi.common import ROOT
from rsi.invention import candidates
from rsi.seed import DrawnArea, MechanismArea, Seed

THETA = {'groups': 9, 'per_world': 3, 'slip': .15, 'skew': 0.}


def make_area(name, seed):
    if name == 'mech':
        return MechanismArea(seed)
    if name.startswith('drawn'):
        return DrawnArea(seed, int(name[5:] or 7), THETA)
    if name.startswith('metric'):
        from rsi.seed_areas import MetricArea
        return MetricArea(seed, int(name[6:] or 777001))
    raise ValueError(name)


def fmt(score):
    return json.dumps({k: round(v, 1) for k, v in score['by_pool'].items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--area', default='mech')
    ap.add_argument('--lives', type=int, default=4)
    ap.add_argument('--worlds', type=int, default=48)
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--held-out', type=int, default=24)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    import faulthandler
    faulthandler.dump_traceback_later(600, repeat=True)   # where the main process is, if it stalls
    area = make_area(args.area, args.seed)
    mech = area if args.area == 'mech' else MechanismArea(args.seed)
    seed = Seed(ROOT / 'seeds' / args.name, language=mech.seed_language, name=args.name)
    cands = candidates()
    print(f'seed {seed.state["name"]} version {seed.state["version"]}, area {area.name}, lives there '
          f'{seed.lives(area.name)}, language {len(seed.state["language"])} atoms', flush=True)
    for _ in range(args.lives):
        t = time.time()
        life, worlds, records = seed.live(area, args.worlds, args.budget)
        entry = seed.state['ledger'][-1]
        print(f'{area.name} life {life}: solved {entry["total"]} of {args.worlds * 100}; by pool '
              f'{fmt(entry)}; {time.time() - t:.0f} s', flush=True)
        salt = 1000 * (1 + sorted(seed.state['areas']).index(area.name)) + life if area.name in seed.state['areas'] else life
        held = area.held_out(args.held_out, salt=salt)
        atoms, tests, provenance = seed.extend(worlds, records, cands)
        if atoms:
            cand = seed.candidate()
            cand['language'] += [list(a) for a in atoms]
            for a in atoms:
                cand['inventions'][a[0]] = {'life': seed.lives(), 'area': area.name}
            kept, carried, new = seed.prove(area, held, salt, cand, args.budget, f'language +{len(atoms)}',
                                            note={'tests': tests, 'atoms': [p['atom'] for p in provenance],
                                                  'from_pools': sorted({p['pool'] for p in provenance})})
            print(f'  extend: {len(atoms)} atoms from {tests} tests; held-out {carried["total"]} -> {new["total"]} '
                  f'{"KEPT" if kept else "dropped"}; {fmt(new)}', flush=True)
        else:
            print('  extend: nothing invented', flush=True)
        drop = seed.prune()
        if drop:
            cand = seed.candidate()
            cand['language'] = [a for a in cand['language'] if a[0] not in drop]
            for k in drop:
                cand['inventions'].pop(k, None)
            kept, carried, new = seed.prove(area, held, salt, cand, args.budget, f'prune -{len(drop)}',
                                            note={'atoms': drop})
            print(f'  prune: {len(drop)} unearned atoms; held-out {carried["total"]} -> {new["total"]} '
                  f'{"KEPT" if kept else "dropped"}; {fmt(new)}', flush=True)
        model = seed.reflect(area.name)
        if model and 'labels' in model:
            cand = seed.candidate()
            cand['areas'][area.name]['model'] = model
            cand['areas'][area.name]['prior'] = True
            kept, carried, new = seed.prove(area, held, salt, cand, args.budget,
                                            f'model g={model["groups"]} from {model["worlds"]} worlds + prior')
            print(f'  reflect: {model["groups"]} groups over {len(model["labels"])} atoms from {model["worlds"]} '
                  f'worlds; held-out {carried["total"]} -> {new["total"]} {"KEPT" if kept else "dropped"}; '
                  f'{fmt(new)}', flush=True)
        elif model:
            print(f'  reflect: fit failed {model["error"]}', flush=True)
        else:
            print(f'  reflect: too little experience here', flush=True)
        a = seed.state['areas'][area.name]
        r = seed.state['resource']
        print(f'  carried: version {seed.state["version"]}, language {len(seed.state["language"])}, '
              f'model {"yes" if a["model"] else "no"}, prior {"yes" if a["prior"] else "no"}, '
              f'held-out {a["held_out_score"]["total"]}; resource live {r["live_scans"] / 1e6:.1f}M '
              f'proof {r["proof_scans"] / 1e6:.1f}M tests {r["invention_tests"]}; {time.time() - t:.0f} s',
              flush=True)
    print('kept:', json.dumps(seed.state['kept']), flush=True)


if __name__ == '__main__':
    sys.exit(main())
