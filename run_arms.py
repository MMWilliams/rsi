"""One review arm on one seed: the v11.1 schedule with the meta-level off, then
the fresh-set check, the audit where the arm's rule can be replayed, and the
harmful-acceptance count. Usage: run_arms.py <arm> <tag> <seed>; state goes to
seeds/<arm>_<tag>. A killed run resumes at its next life.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
import warnings
from collections import Counter

import audit_seed
import seed_check
import seed_run
from rsi.common import ROOT, write_json
from rsi.invention import candidates
from rsi.seed import MechanismArea, make_area
from rsi.seed_arms import ARMS, use_arm
from rsi.seed_string import SEED_LANGUAGE

SCHEDULE = 'mech:4,drawn7:3,metric777001:3,drawn11:2,drawn13:2,metric555001:2,str7:3,mech:2'   # confirm_seed.sh
BUDGET = 1024
REPLAYABLE = ('full', 'no-guidance', 'frequency', 'no-invention')   # arms proved by the unchanged rule
HARM_COUNTED = ('full', 'point', 'accept-all')                      # shortcut: matched has ~4x the acceptances; count it if accept-all's rate is in doubt
HARM_PER_POOL = 12
MIN_COMMIT = 8 * 2 ** 30


class MemoryStatus(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
        (f, ctypes.c_ulonglong) for f in ('phys', 'avail_phys', 'page', 'avail_page', 'virt', 'avail_virt', 'ext')]


def wait_for_commit():
    """Pools die or stall when other jobs have taken the machine's commit."""
    status = MemoryStatus(length=ctypes.sizeof(MemoryStatus))
    while ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) and status.avail_page < MIN_COMMIT:
        print(f'waiting for commit: {status.avail_page / 2 ** 30:.1f} GB free', flush=True)
        time.sleep(300)


def lives_of(text):
    return [(a, int(n)) for a, n in (step.split(':') for step in text.split(','))]


def schedule_for(arm, tag, steps):
    """Matched spends full's live + proof scans on living: every step scaled,
    rounded cumulatively so the total is within one life."""
    if arm != 'matched':
        return steps
    r = json.loads((ROOT / 'seeds' / f'full_{tag}' / 'state.json').read_text())['resource']
    scale = (r['live_scans'] + r['proof_scans']) / r['live_scans']
    out, lived, done = [], 0, 0
    for area, lives in steps:
        lived += lives
        n = round(lived * scale) - done
        done += n
        out.append((area, n))
    return out


def count_harmful(seed, name):
    """Each kept change scored on a set no proof used: the state just before
    it against the state just after, with the experience it was tested under."""
    snaps = seed.path / 'versions'
    lived = {e['version_after']: e['experience_len'] for e in seed.state['ledger'] if e['op'] == 'prove' and e.get('kept')}
    rows = []
    for k in seed.state['kept']:
        area = make_area(seed.state['areas'][k['area']]['spec'], seed.state['seed'])
        fresh = area.held_out(HARM_PER_POOL, salt=999)
        totals = []
        for v in (k['version'] - 1, k['version']):
            snap = json.loads((snaps / f'{v}.json').read_text())
            st = seed.candidate()
            st.update(language=snap['language'], areas=snap['areas'], inventions=snap['inventions'],
                      experience=st['experience'][:lived[k['version']]])
            totals.append(seed.score(seed.run(fresh, BUDGET, area.name, state=st), fresh, BUDGET)['total'])
        rows.append({'version': k['version'], 'area': k['area'], 'change': k['change'], 'before': totals[0],
                     'after': totals[1], 'harmful': totals[1] < totals[0]})
        print('harm', rows[-1], flush=True)
    write_json(ROOT / f'analysis/harmful-{name}.json',
               {'name': name, 'per_pool': HARM_PER_POOL, 'kept': len(rows), 'harmful': sum(r['harmful'] for r in rows), 'rows': rows})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arm', choices=ARMS)
    ap.add_argument('tag')
    ap.add_argument('seed', type=int)
    ap.add_argument('--schedule', default=SCHEDULE)
    ap.add_argument('--worlds', type=int, default=96)
    ap.add_argument('--held-out', type=int, default=48)
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    use_arm(args.arm)
    name = f'{args.arm}_{args.tag}'
    seed = ARMS[args.arm](ROOT / 'seeds' / name, language=MechanismArea(args.seed).seed_language + SEED_LANGUAGE, name=name, seed=args.seed)
    if args.arm != 'full':     # a full seed's state stays byte-for-byte what seed_run.py writes
        seed.state['arm'] = args.arm
        seed.save()
    cands = candidates()
    target = Counter()
    areas = []
    for area_name, lives in schedule_for(args.arm, args.tag, lives_of(args.schedule)):
        area = make_area(area_name, args.seed)
        target[area_name] += lives
        if area_name not in areas:
            areas.append(area_name)
        while seed.lives(area_name) < target[area_name]:
            wait_for_commit()
            t = time.time()
            life, worlds, records = seed.live(area, args.worlds, BUDGET)
            print(f'{area_name} life {life}: solved {seed.state["ledger"][-1]["total"]}', flush=True)
            seed_run.phase(seed, area, worlds, records, cands, BUDGET, args.held_out)
            r = seed.state['resource']
            print(f'  version {seed.state["version"]}, language {len(seed.state["language"])}, live {r["live_scans"] / 1e6:.1f}M '
                  f'proof {r["proof_scans"] / 1e6:.1f}M; {time.time() - t:.0f} s', flush=True)
    sys.argv = ['seed_check', '--name', name, '--seed', str(args.seed), '--areas', ','.join(areas)]
    seed_check.main()
    status = 0
    if args.arm in REPLAYABLE:
        sys.argv = ['audit_seed', '--name', name]
        status = audit_seed.main()
    else:
        print(f'audit: no replayable proofs, {args.arm} does not use the interval rule', flush=True)
    if args.arm in HARM_COUNTED:
        count_harmful(seed, name)
    return status


if __name__ == '__main__':
    sys.exit(main())
