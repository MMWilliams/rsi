"""Replay a seed's kept changes from its version snapshots and its ledger.

For every kept change with a snapshot of the state before and after it, the
auditor rebuilds the area from its spec, redraws the held-out set from the
ledger's salt, runs both states with the experience the seed had at the time,
and checks the totals and the interval against what the ledger recorded. A
mismatch is a reproducibility failure; the audit never changes the seed.
Snapshots are written by `rsi.seed.Seed.prove` from version 27 on.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings

import numpy as np

from rsi.common import ROOT, write_json
from rsi.seed import STREAM, Seed, make_area


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='s1')
    ap.add_argument('--versions', default='', help='comma-separated kept versions to replay; default all with snapshots')
    args = ap.parse_args()
    warnings.filterwarnings('ignore')
    seed = Seed(ROOT / 'seeds' / args.name)
    snaps = seed.path / 'versions'
    have = {int(p.stem) for p in snaps.glob('*.json')} if snaps.exists() else set()
    wanted = [int(v) for v in args.versions.split(',') if v] or sorted(v for v in have if v - 1 in have)
    proofs = {e['version_after']: e for e in seed.state['ledger'] if e['op'] == 'prove' and e.get('kept')
              and 'version_after' in e}
    report = {'name': args.name, 'replayed': [], 'passed': True}
    for v in wanted:
        if v not in proofs or v not in have or v - 1 not in have:
            report['replayed'].append({'version': v, 'skipped': 'no snapshot or no proof entry'})
            continue
        entry = proofs[v]
        before = json.loads((snaps / f'{v - 1}.json').read_text())
        after = json.loads((snaps / f'{v}.json').read_text())
        area = make_area(seed.state['areas'][entry['area']]['spec'], seed.state['seed'])
        per_pool = entry['carried']['size'] // len(area.pools)
        held = area.held_out(per_pool, salt=entry['salt'])
        budget = entry['carried']['budget']

        def state_at(snap):
            st = seed.candidate()
            st['language'] = snap['language']
            st['areas'] = snap['areas']
            st['inventions'] = snap['inventions']
            st['experience'] = st['experience'][:snap['experience_len']]
            return st

        carried = seed.run(held, budget, area.name, state=state_at(before))
        candidate = seed.run(held, budget, area.name, state=state_at(after))
        c_hits = [r['hits'] for r in carried]
        n_hits = [r['hits'] for r in candidate]
        diff = np.array(n_hits, dtype=float) - np.array(c_hits, dtype=float)
        draws = np.random.default_rng(entry['salt']).integers(len(diff), size=(4000, len(diff)))
        means = diff[draws].mean(axis=1)
        interval = [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]
        ok = (sum(c_hits) == entry['carried']['total'] and sum(n_hits) == entry['candidate']['total']
              and np.allclose(interval, entry['candidate']['interval'], atol=1e-9))
        report['passed'] &= ok
        report['replayed'].append({'version': v, 'area': entry['area'], 'change': entry['change'],
                                   'carried': [sum(c_hits), entry['carried']['total']],
                                   'candidate': [sum(n_hits), entry['candidate']['total']],
                                   'interval': [interval, entry['candidate']['interval']], 'ok': bool(ok)})
        print(v, entry['change'], 'ok' if ok else 'MISMATCH', flush=True)
    write_json(ROOT / f'analysis/audit-seed-{args.name}.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'replayed'}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
