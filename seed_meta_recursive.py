"""Does a procedure the meta-level adopted make the next lives of improvement
faster or cheaper? The recursive step, tested directly. From one seed state,
three branches live the same lives in one area on identical world draws: P
under the adopted procedure (--adopt), Q under the procedure as it stands,
R under an adversarial change of the same size (--adversary: another knob
the meta-level could have moved). Each branch proposes and proves under its
own procedure, exactly as seed_run does. The three final states are scored
on a meta set no proof used, paired over worlds against Q, and the proof
scans each branch spent are compared. The recursive step is confirmed only
if P beats Q (interval above zero, or no worse at 10% less proof cost) and
R does not. Development seeds only; the branches are kept for the auditor
(audit_seed.py --name <name>/branches/P)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np

from rsi.common import ROOT, write_json
from rsi.invention import candidates
from rsi.seed import Seed, form_of, make_area
from seed_run import MARGIN, phase

RECURSIVE_SALT = 9000   # above every proof, extension and meta salt


def knobs(spec):
    out = {}
    for item in filter(None, spec.split(',')):
        k, v = item.split('=')
        out[k] = float(v) if '.' in v else int(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True, help='a new development seed folder for this test')
    ap.add_argument('--source', required=True, help='seed folder whose state.json the branches start from')
    ap.add_argument('--seed', type=int, default=644101)
    ap.add_argument('--area', default='mech')
    ap.add_argument('--lives', type=int, default=2)
    ap.add_argument('--worlds', type=int, default=96)
    ap.add_argument('--budget', type=int, default=1024)
    ap.add_argument('--held-out', type=int, default=48)
    ap.add_argument('--adopt', required=True, help='the adopted procedure, e.g. recurrence=3,prune_r=0.05')
    ap.add_argument('--adversary', required=True, help='a change the meta-level did not adopt, e.g. extend_cap=80')
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    root = ROOT / 'seeds' / args.name
    if not root.exists():
        root.mkdir(parents=True)
        shutil.copyfile(Path(args.source) / 'state.json', root / 'state.json')
    seed = Seed(root, seed=args.seed)
    area = make_area(args.area, args.seed)
    form = form_of(area.spec)
    arms = {'Q': {}, 'P': knobs(args.adopt), 'R': knobs(args.adversary)}
    cands = candidates()
    base = dict(seed.state['resource'])
    kept0, lived0 = len(seed.state['kept']), seed.lives(area.name)
    branches = {}
    for label, change in arms.items():
        b = seed.branch(label)
        b.state['procedure'][form].update(change)
        b.save()
        print(f'[{label}] procedure {json.dumps(b.procedure(form))}', flush=True)
        for _ in range(args.lives):
            life, worlds, records = b.live(area, args.worlds, args.budget)
            e = b.state['ledger'][-1]
            print(f'[{label}] {area.name} life {life}: solved {e["total"]} of {args.worlds * 100}', flush=True)
            phase(b, area, worlds, records, cands, args.budget, args.held_out, f'[{label}] ')
        branches[label] = b
    salt = RECURSIVE_SALT + 100 * sorted(branches['Q'].state['areas']).index(area.name) + lived0
    held = area.held_out(-(-args.held_out // len(area.pools)), salt=salt)
    hits = {label: [r['hits'] for r in seed.run(held, args.budget, area.name, state=b.state)]
            for label, b in branches.items()}
    cost = {label: b.state['resource']['proof_scans'] - base['proof_scans'] for label, b in branches.items()}
    report = {'name': args.name, 'source': args.source, 'area': area.name, 'lives': args.lives,
              'salt': salt, 'worlds': len(held), 'arms': {}}
    for label, b in branches.items():
        arm = {'procedure': b.procedure(form), 'meta_total': int(sum(hits[label])), 'hits': hits[label],
               'proof_scans': cost[label], 'live_scans': b.state['resource']['live_scans'] - base['live_scans'],
               'kept': b.state['kept'][kept0:], 'version': b.state['version']}
        if label != 'Q':
            diff = np.array(hits[label], dtype=float) - np.array(hits['Q'], dtype=float)
            draws = np.random.default_rng(salt).integers(len(diff), size=(4000, len(diff)))
            means = diff[draws].mean(axis=1)
            lo, hi = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
            cheaper = diff.mean() >= 0 and lo <= 0 <= hi and cost[label] <= cost['Q'] * (1 - MARGIN)
            arm.update(mean=float(diff.mean()), interval=[lo, hi],
                       verdict='better' if lo > 0 else 'cheaper' if cheaper else 'worse' if hi < 0 else 'no gain')
        report['arms'][label] = arm
    wins = {label: report['arms'][label]['verdict'] in ('better', 'cheaper') for label in ('P', 'R')}
    report['recursive_step'] = wins['P'] and not wins['R']
    write_json(ROOT / f'analysis/meta-recursive-{args.name}.json', report)
    for label, arm in report['arms'].items():
        tail = f' [{arm["interval"][0]:+.2f}, {arm["interval"][1]:+.2f}] {arm["verdict"]}' if label != 'Q' else ''
        print(f'{label}: meta {arm["meta_total"]} proof {arm["proof_scans"] / 1e6:.1f}M kept {len(arm["kept"])}{tail}', flush=True)
    print('recursive step', 'CONFIRMED' if report['recursive_step'] else 'NOT CONFIRMED', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
