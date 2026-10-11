"""Run the seed for some lives in one area and report what it kept.

Each life: live (earn in fresh worlds), then propose every change at once
(invented atoms, pruned atoms, a refit model and prior) and prove the
combination; if it fails, prove each part on its own. Every proof is on a
held-out set drawn fresh for that life, and a change to the shared language
must also leave every other area the seed has lived in no worse. The state is
saved after every operation, so a run resumes, and the ledger records every
candidate change with its proof.
"""
from __future__ import annotations

import argparse
import faulthandler
import json
import sys
import time
import warnings

from rsi.common import ROOT
from rsi.invention import candidates
from rsi.seed import MechanismArea, Seed, make_area


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
    faulthandler.dump_traceback_later(600, repeat=True)   # where the main process is, if it stalls
    area = make_area(args.area, args.seed)
    mech = area if args.area == 'mech' else MechanismArea(args.seed)
    seed = Seed(ROOT / 'seeds' / args.name, language=mech.seed_language, name=args.name, seed=args.seed)
    cands = candidates()
    print(f'seed {seed.state["name"]} version {seed.state["version"]}, area {area.name}, lives there '
          f'{seed.lives(area.name)}, language {len(seed.state["language"])} atoms', flush=True)

    def report(label, kept, carried, new, elsewhere):
        where = '' if not elsewhere else ' elsewhere ' + json.dumps(
            {k: f'{v["carried"]}->{v["candidate"]}' for k, v in elsewhere.items()})
        lo, hi = new.get('interval', (0., 0.))
        print(f'  {label}: held-out {carried["total"]} -> {new["total"]} [{lo:+.1f}, {hi:+.1f}] per world '
              f'{"KEPT" if kept else "dropped"}; {fmt(new)}{where}', flush=True)

    for _ in range(args.lives):
        t = time.time()
        life, worlds, records = seed.live(area, args.worlds, args.budget)
        entry = seed.state['ledger'][-1]
        print(f'{area.name} life {life}: solved {entry["total"]} of {args.worlds * 100}; by pool '
              f'{fmt(entry)}; {time.time() - t:.0f} s', flush=True)
        salt = 1000 * (1 + sorted(seed.state['areas']).index(area.name)) + life
        held = area.held_out(max(args.held_out, -(-48 // len(area.pools))), salt=salt)   # at least 48 worlds
        atoms, tests, provenance = seed.extend(worlds, records, cands)
        drop = seed.prune()
        model = seed.reflect(area.name)
        if model and 'error' in model:
            print(f'  reflect: fit failed {model["error"]}', flush=True)
            model = None
        parts = []
        if atoms:
            parts.append(('extend', f'language +{len(atoms)}', True,
                          {'tests': tests, 'atoms': [p['atom'] for p in provenance],
                           'from_pools': sorted({p['pool'] for p in provenance})}))
        if drop:
            parts.append(('prune', f'prune -{len(drop)}', True, {'atoms': drop}))
        if model:
            parts.append(('model', f'model g={model["groups"]} pw={model["per_world"]} '
                                   f'from {model["worlds"]} worlds + prior', False, None))

        def apply(cand, names):
            if 'extend' in names:
                cand['language'] += [list(a) for a in atoms]
                for a in atoms:
                    cand['inventions'][a[0]] = {'life': seed.lives(), 'area': area.name}
            if 'prune' in names:
                cand['language'] = [a for a in cand['language'] if a[0] not in drop]
                for k in drop:
                    cand['inventions'].pop(k, None)
            if 'model' in names:
                cand['areas'][area.name]['model'] = model
                cand['areas'][area.name]['prior'] = True
            return cand

        done = False
        if len(parts) >= 2:
            cand = apply(seed.candidate(), {p[0] for p in parts})
            kept, carried, new, elsewhere = seed.prove(
                area, held, salt, cand, args.budget, ' + '.join(p[1] for p in parts),
                note={'parts': [p[0] for p in parts]}, shared=any(p[2] for p in parts))
            report('together', kept, carried, new, elsewhere)
            done = kept
        if not done:
            for kind, change, shared, note in parts:
                cand = apply(seed.candidate(), {kind})
                kept, carried, new, elsewhere = seed.prove(area, held, salt, cand, args.budget, change,
                                                           note=note, shared=shared)
                report(kind, kept, carried, new, elsewhere)
        if not parts:
            print('  nothing to propose', flush=True)
        a = seed.state['areas'][area.name]
        r = seed.state['resource']
        print(f'  carried: version {seed.state["version"]}, language {len(seed.state["language"])}, '
              f'model {"g=%d pw=%d" % (a["model"]["groups"], a["model"].get("per_world", 3)) if a["model"] else "no"}, '
              f'prior {"yes" if a["prior"] else "no"}, held-out {a["held_out_score"]["total"]}; '
              f'resource live {r["live_scans"] / 1e6:.1f}M proof {r["proof_scans"] / 1e6:.1f}M '
              f'tests {r["invention_tests"]}; {time.time() - t:.0f} s', flush=True)
    print('kept:', json.dumps(seed.state['kept'][-12:]), flush=True)


if __name__ == '__main__':
    sys.exit(main())
