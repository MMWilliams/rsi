"""Second independent replication of the heterogeneous environment and improver.

Section 8 of `TECHNICAL-DESIGN-EXPERIMENTATION-2026-09-20.md` requires two
independent frozen replications with disjoint seeds before improver growth is
reported as reliable. Replication one is
`runs/heterogeneous-ast-environment-20260920/`.

This reuses replication one's generator, action set, selection rule and gates
without modification, changing only the seeds and the share prior's draw. No
threshold, rule or control is altered, so this is a replication and not a second
design.
"""
from __future__ import annotations

import json
import sys

import heterogeneous_ast_environment as env
import contextual_improver_transfer as improver
from rsi.common import ROOT, write_json


DEST = ROOT / 'runs/heterogeneous-ast-environment-rep2-20260920'
PANELS = {'beta_dev': (tuple(range(909100, 909112)), 'beta', 909001),
          'beta_transfer': (tuple(range(909200, 909212)), 'beta', 909002),
          'balanced_control': (tuple(range(909300, 909312)), 'balanced', 909003)}


def install():
    """Point both modules at this replication's directory and seeds."""
    env.DEST = DEST
    env.PANELS = PANELS
    improver.DEST = DEST
    improver.OUT = DEST / 'improver_results.json'


def run_improver():
    phase_e = json.loads((DEST / 'results.json').read_text())
    if not phase_e['p2b_satisfied']:
        raise RuntimeError('replication two did not satisfy P2b; '
                           'the improver protocol is void here')
    dev = improver.bank_table('beta_dev')
    result = {
        'scope': 'replication two of the frozen contextual improver transfer',
        'replicates': 'runs/heterogeneous-ast-environment-20260920',
        'protocol_sha256': improver.sha(improver.PROTOCOL),
        'runner_sha256': improver.sha(ROOT / 'heterogeneous_replication_two.py'),
        'phase_e_fixed_regret': {k: v['fixed_regret']
                                 for k, v in phase_e['panels'].items()},
        'development_panel': {
            'seeds': [b['seed'] for b in dev],
            'public_shares': [round(b['public_share'], 3) for b in dev],
            'gain': {str(b['seed']): b['gain'] for b in dev}},
        'transfer': improver.analyse(dev, improver.bank_table('beta_transfer'),
                                     'beta_transfer'),
        'stationarity_control': improver.analyse(
            dev, improver.bank_table('balanced_control'), 'balanced_control'),
        'limits': ['Same limits as replication one; seeds are disjoint and no '
                   'rule, threshold or control was changed.']}
    write_json(improver.OUT, result)
    for key in ('transfer', 'stationarity_control'):
        value = result[key]
        print(f'== {value["panel"]}  fixed_regret={value["fixed_regret"]:+d} '
              f'share_corr={value["share_correlation"]:.2f}')
        print('   totals:', json.dumps(value['totals']))
        for gate, detail in value['gates'].items():
            print(f'   {gate}: passed={detail["passed"]}')
            for sub in ('later_minus_initial', 'later_minus_duplicate'):
                if sub in detail:
                    d = detail[sub]
                    print(f'      {sub}: {d["gain"]:+d} '
                          f'{d["positive_banks"]}w/{d["losing_banks"]}l '
                          f'{d["interval"]}')
            if 'gain' in detail:
                print(f'      gain={detail["gain"]:+d} '
                      f'{detail["positive_banks"]}w/{detail["losing_banks"]}l '
                      f'{detail["interval"]}')


if __name__ == '__main__':
    install()
    {'prepare': env.prepare, 'score': env.score, 'improver': run_improver}[
        sys.argv[1]]()
