"""Frozen contextual improver transfer on the heterogeneous environment.

Protocol: EXPERIMENT-contextual-improver-transfer.md

Reads the panels Phase E already froze and scored. Parents differ only in how
many development banks of verified effects they inherit; they share the base,
the three actions, the selection rule and the transfer panel. The rule is the
weakest sensible learner, nearest observed public share, so a later parent's
advantage can only come from holding more of the share-to-action mapping.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from heterogeneous_ast_environment import DEST, ACTIONS, THRESHOLD


PROTOCOL = ROOT / 'EXPERIMENT-contextual-improver-transfer.md'
SCRIPT = ROOT / 'contextual_improver_transfer.py'
OUT = DEST / 'improver_results.json'
PARENTS = ('initial', 'later', 'duplicate', 'scrambled', 'empty')
DEFAULT_ACTION = 'e0'
SCRAMBLE_SEED = 908500


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bank_table(panel):
    """Per-bank public share and realized gain of each action over e0."""
    rows = json.loads((DEST / f'rows_{panel}.json').read_text())['rows']
    totals = defaultdict(lambda: defaultdict(int))
    leaning = defaultdict(list)
    truth = defaultdict(list)
    for row in rows:
        for action in ACTIONS:
            totals[row['seed']][action] += row['labels'][action]
        leaning[row['seed']].append(
            row['confidence']['familiar'] >= row['confidence']['shifted'])
        truth[row['seed']].append(row['domain'] == 'familiar')
    banks = []
    for seed in sorted(totals):
        base = totals[seed]['e0']
        banks.append({'seed': seed,
                      'public_share': float(np.mean(leaning[seed])),
                      'true_share': float(np.mean(truth[seed])),
                      'e0': base,
                      'gain': {a: totals[seed][a] - base for a in ACTIONS}})
    return banks


def inherited(dev):
    """What each parent carries. Records are (public_share, gain-by-action)."""
    first = [dev[0]]
    rng = np.random.default_rng(SCRAMBLE_SEED)
    order = rng.permutation(len(dev))
    scrambled = [{**bank, 'gain': dev[int(other)]['gain']}
                 for bank, other in zip(dev, order)]
    return {'initial': first, 'later': list(dev),
            'duplicate': first * len(dev), 'scrambled': scrambled,
            'empty': []}


def choose(records, public_share):
    """The one selection rule every parent shares."""
    if not records:
        return DEFAULT_ACTION
    nearest = min(records,
                  key=lambda r: (abs(r['public_share'] - public_share),
                                 r['seed']))
    return min(ACTIONS, key=lambda a: (-nearest['gain'][a], a))


def deploy(records, target):
    """Per-bank gain over e0 from this parent's deployments."""
    picks = {}
    gains = []
    for bank in target:
        action = choose(records, bank['public_share'])
        picks[str(bank['seed'])] = action
        gains.append(bank['gain'][action])
    return picks, gains


def constant(target, action):
    return [bank['gain'][action] for bank in target]


def compare(left, right):
    diffs = [a - b for a, b in zip(left, right)]
    return {'left': sum(left), 'right': sum(right), 'gain': sum(diffs),
            'banks': len(diffs),
            'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def growth_gate(result):
    return bool(result['gain'] >= 6 and result['losing_banks'] <= 4
                and result['interval'][0] > 0)


def analyse(dev, target, label):
    records = inherited(dev)
    picks = {}
    gains = {}
    for name in PARENTS:
        picks[name], gains[name] = deploy(records[name], target)
    fixed = {f'always_{a}': constant(target, a) for a in ACTIONS}
    totals = {f'parent_{k}': sum(v) for k, v in gains.items()}
    totals.update({k: sum(v) for k, v in fixed.items()})
    best_constant_name = max(fixed, key=lambda k: sum(fixed[k]))
    hindsight = [max(bank['gain'].values()) for bank in target]
    totals['best_constant'] = sum(fixed[best_constant_name])
    totals['per_bank_hindsight'] = sum(hindsight)

    g1 = compare(gains['later'], fixed[best_constant_name])
    g2 = compare(gains['later'], gains['initial'])
    g2_dup = compare(gains['later'], gains['duplicate'])
    return {
        'panel': label,
        'banks': len(target),
        'public_shares': [round(b['public_share'], 3) for b in target],
        'true_shares': [round(b['true_share'], 3) for b in target],
        'share_correlation': float(np.corrcoef(
            [b['public_share'] for b in target],
            [b['true_share'] for b in target])[0, 1]),
        'e0_total': sum(b['e0'] for b in target),
        'totals': totals,
        'best_constant_action': best_constant_name,
        'chosen_actions': picks,
        'fixed_regret': sum(hindsight) - sum(fixed[best_constant_name]),
        'regret_of_later': sum(hindsight) - sum(gains['later']),
        'gates': {
            'g1_contextual_value': {**g1,
                                    'passed': bool(g1['gain'] > 0
                                                   and g1['interval'][0] > 0)},
            'g2_improver_growth': {
                'later_minus_initial': g2,
                'later_minus_duplicate': g2_dup,
                'passed': bool(growth_gate(g2) and g2_dup['gain'] >= 0)}}}


def main():
    if OUT.exists():
        raise RuntimeError('already scored')
    phase_e = json.loads((DEST / 'results.json').read_text())
    if not phase_e['p2b_satisfied']:
        raise RuntimeError('protocol is void: Phase E did not satisfy P2b')

    dev = bank_table('beta_dev')
    result = {
        'scope': 'frozen contextual improver transfer on generated '
                 'heterogeneous banks',
        'protocol_sha256': sha(PROTOCOL), 'runner_sha256': sha(SCRIPT),
        'phase_e_threshold': THRESHOLD,
        'phase_e_fixed_regret': {k: v['fixed_regret']
                                 for k, v in phase_e['panels'].items()},
        'development_panel': {
            'seeds': [b['seed'] for b in dev],
            'public_shares': [round(b['public_share'], 3) for b in dev],
            'gain': {str(b['seed']): b['gain'] for b in dev}},
        'transfer': analyse(dev, bank_table('beta_transfer'), 'beta_transfer'),
        'stationarity_control': analyse(dev, bank_table('balanced_control'),
                                        'balanced_control'),
        'limits': [
            'One synthetic benchmark and one mechanism axis.',
            'Specialists are the frozen 2026-09-18 models, not retrained here.',
            'The environment was chosen because simulation predicted it would '
            'have measurable fixed regret.',
            'A G2 pass shows better contextual deployment from more verified '
            'history, not recursive self-improvement.']}
    write_json(OUT, result)
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
    main()
