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
    have = {int(p.stem) for p in snaps.glob('*.json') if p.stem.isdigit()} if snaps.exists() else set()
    wanted = [int(v) for v in args.versions.split(',') if v] or sorted(v for v in have if v - 1 in have)
    proofs, lived = {}, 0
    for e in seed.state['ledger']:
        if e['op'] == 'live':
            lived += e['worlds']
        elif e['op'] == 'prove' and e.get('kept') and 'version_after' in e:
            # both states of a proof share the experience the seed had when it ran
            proofs[e['version_after']] = dict(e, experience_len=e.get('experience_len', lived))
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
            st['experience'] = st['experience'][:entry['experience_len']]
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
        extension = None
        if 'extension' in entry:      # judged on the union of the proof set and one extension set
            ext_entry = entry['extension']
            ext = area.held_out(ext_entry['carried']['size'] // len(area.pools), salt=ext_entry['salt'])
            e_carried = [r['hits'] for r in seed.run(ext, budget, area.name, state=state_at(before))]
            e_candidate = [r['hits'] for r in seed.run(ext, budget, area.name, state=state_at(after))]
            diff_all = np.concatenate([diff, np.array(e_candidate, dtype=float) - np.array(e_carried, dtype=float)])
            draws = np.random.default_rng(entry['salt']).integers(len(diff_all), size=(4000, len(diff_all)))
            means = diff_all[draws].mean(axis=1)
            interval_all = [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]
            ok = (ok and sum(e_carried) == ext_entry['carried']['total']
                  and sum(e_candidate) == ext_entry['candidate']['total']
                  and np.allclose(interval_all, ext_entry['candidate']['interval'], atol=1e-9))
            extension = {'carried': [sum(e_carried), ext_entry['carried']['total']],
                         'candidate': [sum(e_candidate), ext_entry['candidate']['total']],
                         'interval': [interval_all, ext_entry['candidate']['interval']]}
        report['passed'] &= ok
        report['replayed'].append({'version': v, 'area': entry['area'], 'change': entry['change'],
                                   'carried': [sum(c_hits), entry['carried']['total']],
                                   'candidate': [sum(n_hits), entry['candidate']['total']],
                                   'interval': [interval, entry['candidate']['interval']], 'ok': bool(ok),
                                   **({'extension': extension} if extension else {})})
        print(v, entry['change'], 'ok' if ok else 'MISMATCH', flush=True)
    # every recorded fallback policy follows from the ledger before it, and every
    # meta-proof replays: both branches' final states on the meta set
    policy_ok, meta_ok, metas = True, True, []
    for i, e in enumerate(seed.state['ledger']):
        if e['op'] == 'revise':
            p = seed.fallback_policy(e['form'], upto=i, patience=e['patience'], probation=e['probation'])
            same = p['active'] == e['active'] and p['retired'] == e['retired']
            policy_ok &= same
            if not same:
                print('revise at ledger entry', i, 'MISMATCH', flush=True)
        elif e['op'] == 'meta' and not e.get('noop'):
            area = make_area(seed.state['areas'][e['area']]['spec'], seed.state['seed'])
            held = area.held_out(e['meta']['worlds'] // len(area.pools), salt=e['meta']['salt'])
            winner = json.loads((snaps / f'{e["winner_version"]}.json').read_text())
            loser = json.loads((snaps / e['loser_snapshot']).read_text())
            a, b = (loser, winner) if e['adopted'] else (winner, loser)

            had = e.get('experience_len', loser['experience_len'])   # version snapshots are rewritten by later lives

            def state_of(snap):
                st = seed.candidate()
                st['language'] = snap['language']
                st['areas'] = snap['areas']
                st['inventions'] = snap['inventions']
                if 'experience_tail' in snap:     # a losing branch's own lives after the branch point
                    st['experience'] = st['experience'][:snap['experience_from']] + snap['experience_tail']
                else:
                    st['experience'] = st['experience'][:had]
                return st

            budget = e['budget']
            ha = [r['hits'] for r in seed.run(held, budget, area.name, state=state_of(a))]
            hb = [r['hits'] for r in seed.run(held, budget, area.name, state=state_of(b))]
            diff = np.array(hb, dtype=float) - np.array(ha, dtype=float)
            draws = np.random.default_rng(e['meta']['salt']).integers(len(diff), size=(4000, len(diff)))
            means = diff[draws].mean(axis=1)
            interval = [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]
            ok = (sum(ha) == e['meta']['a'] and sum(hb) == e['meta']['b']
                  and np.allclose(interval, e['meta']['interval'], atol=1e-9))
            if 'pooled' in e:         # the verdict pooled earlier tests of the same mutation
                pooled = seed.pooled(e['form'], e['mutation'], diff, e['cost']['a']['proof_scans'],
                                     e['cost']['b']['proof_scans'], e['meta']['salt'], upto=i)
                ok = (ok and pooled is not None and pooled['tests'] == e['pooled']['tests']
                      and np.allclose(pooled['interval'], e['pooled']['interval'], atol=1e-9)
                      and pooled['cost'] == e['pooled']['cost'])
            meta_ok &= ok
            metas.append({'ledger': i, 'mutation': e['mutation'], 'adopted': e['adopted'],
                          'a': [sum(ha), e['meta']['a']], 'b': [sum(hb), e['meta']['b']], 'ok': bool(ok)})
            print('meta', e['mutation'], 'adopted' if e['adopted'] else 'declined', 'ok' if ok else 'MISMATCH', flush=True)
    report['policy_ok'] = policy_ok
    report['meta_ok'] = meta_ok
    report['meta'] = metas
    report['passed'] &= policy_ok and meta_ok
    write_json(ROOT / f'analysis/audit-seed-{args.name}.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'replayed'}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
