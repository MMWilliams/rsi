"""Review 002, item 5: every recorded full-set proof of the sealed seeds judged
again, offline, at half and quarter set size and at other cross-area
tolerances. A candidate that was never kept has no later fresh-set effect to
compare with, so the reference is the full-set verdict: how many of its
acceptances a smaller set would lose and how many of its rejections it would
pass, against the share of proof scans saved."""
import json

import numpy as np

from rsi.common import ROOT, write_json

SEEDS = [f'c{i}' for i in range(1, 32) if i != 20]   # c20 was killed before its verdict
ORIGINAL = [f'c{i}' for i in range(1, 24) if i != 20]
FRACTIONS, TOLERANCES, BOOT = (1, 2, 4), (0., .02, .05, .1), 4000


def accepted(diff, salt):
    draws = np.random.default_rng(salt).integers(len(diff), size=(BOOT, len(diff)))
    return float(np.percentile(diff[draws].mean(axis=1), 2.5)) > 0


def main():
    proofs = []
    for name in SEEDS:
        state = json.loads((ROOT / 'seeds' / name / 'state.json').read_text())
        for e in state['ledger']:
            if e['op'] != 'prove':
                continue
            full = 'worlds' in e['candidate'] and e['candidate']['worlds'] == e['carried'].get('size')
            proofs.append(dict(e, seed_name=name, full_set=full))
    judged = [e for e in proofs if e['full_set'] and 'extension' not in e]
    size = {}
    for f in FRACTIONS:
        table = {'accept_kept': 0, 'accept_lost': 0, 'reject_passed': 0, 'reject_held': 0}
        for e in judged:
            diff = np.array(e['candidate']['hits'], float) - np.array(e['carried']['hits'], float)
            small = accepted(diff[::f], e['salt'])
            table[('accept_kept' if small else 'accept_lost') if accepted(diff, e['salt']) else ('reject_passed' if small else 'reject_held')] += 1
        size[f'1/{f}'] = table
    tolerance = {}
    for t in TOLERANCES:
        with_checks = [e for e in proofs if e.get('elsewhere')]
        tolerance[str(t)] = {'with_cross_area_check': len(with_checks), 'would_pass': sum(
            all(v['candidate'] >= v['carried'] * (1 - t) for v in e['elsewhere'].values()) for e in with_checks)}
    original = [e for e in proofs if e['seed_name'] in ORIGINAL]
    rejected = [e for e in original if e['full_set'] and not e['kept']]
    out = {'seeds': len(SEEDS), 'proofs': len(proofs), 'full_set_without_extension': len(judged), 'set_size': size, 'cross_area_tolerance': tolerance,
           'plan_reference_c1_c23': {'proofs': len(original), 'full_set_rejections': len(rejected),
                                     'of_which_positive': sum(e['candidate']['total'] > e['carried']['total'] for e in rejected)}}
    write_json(ROOT / 'analysis/review002-rejudged.json', out)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
