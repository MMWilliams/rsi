"""Precondition screen for acquisition policy as a recursive transmissible state.

Recursive growth through partition-scheme transmission failed because the scheme
was worth +1 to +13, below the +20 bar. Before building any machinery around a
different transmissible state, this screens the most plausible one: **which
history banks are worth acquiring**, a decision the child cannot make from the
answers it does not yet have.

On the audited replication-one confirmation banks, a child with a budget of K
history banks builds its full construction system and is scored on the transfer
panel. Compared:

  - `random`: expected score over random K-subsets. The zero-knowledge default.
  - `first`: the first K banks in arrival order.
  - public heuristics a researcher would try for free: most-reachable banks,
    most bin-diverse banks, largest mean pool. These are part of the adversarial
    default, since a parent must beat them to have transmitted anything.
  - `value_topk`: an upper reference that ranks banks by their leave-one-out
    marginal value on the transfer panel, which uses final labels and is not
    deployable.

Default regret is `value_topk` minus the best free rule. Reported per K. If it
does not clear +20, acquisition is rejected as a recursive state without any
improver being built for it. Development on frozen, audited banks.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
import construction_improver_development as dev
import construction_improver_confirmation as conf
import complexity_partition_environment as env


OUT = ROOT / 'analysis/acquisition-regret-screen-20260921.json'
BUDGETS = (4, 8)
RANDOM_DRAWS = 8
SEED = 918001
THRESHOLD = 20


def system_score(history, transfer):
    specialists = dev.build_system(history)
    order = sorted(specialists)
    actions = order + ['e0']
    router = dev.fit_router(history, specialists, actions, order)
    return dev.deploy(transfer, specialists, router, actions, order)


def bank_public_stats(bank):
    """Statistics a child could compute before paying for any label."""
    return {'mean_log_pool': float(np.mean([t['stats']['log_pool'] for t in bank])),
            'mean_margin': float(np.mean([t['stats']['margin'] for t in bank])),
            'mean_spread': float(np.mean([t['stats']['spread'] for t in bank])),
            'mean_head': float(np.mean([t['stats']['head'] for t in bank]))}


def bank_label_stats(bank):
    """Statistics that need labels; these define the upper references only."""
    bins = defaultdict(int)
    for task in bank:
        bins[env.bin_of(task['labels'])] += 1
    reachable = sum(1 for t in bank if any(t['labels']))
    return {'reachable': reachable,
            'bin_diversity': len([k for k in bins if k != 'unreachable'])}


def main():
    if OUT.exists():
        raise RuntimeError('screen exists')
    pool = conf.load_banks('history_a') + conf.load_banks('history_b')
    transfer = conf.load_banks('transfer')
    rng = np.random.default_rng(SEED)
    n = len(pool)
    print('pool banks', n, 'transfer banks', len(transfer), flush=True)

    # Leave-one-out marginal value of each bank, on the transfer panel.
    full = np.asarray(system_score(pool, transfer), float)
    marginal = []
    for index in range(n):
        without = pool[:index] + pool[index + 1:]
        score = np.asarray(system_score(without, transfer), float)
        marginal.append(float(full.sum() - score.sum()))
        print('loo bank {:2d} marginal={:+.1f}'.format(index, marginal[-1]),
              flush=True)
    value_order = sorted(range(n), key=lambda i: -marginal[i])

    public = [bank_public_stats(b) for b in pool]
    labelled = [bank_label_stats(b) for b in pool]
    heuristics = {
        'largest_pool': sorted(range(n), key=lambda i: -public[i]['mean_log_pool']),
        'lowest_margin': sorted(range(n), key=lambda i: public[i]['mean_margin']),
        'widest_spread': sorted(range(n), key=lambda i: -public[i]['mean_spread']),
        'most_reachable_LABELLED': sorted(range(n),
                                          key=lambda i: -labelled[i]['reachable']),
        'most_diverse_LABELLED': sorted(range(n),
                                        key=lambda i: -labelled[i]['bin_diversity'])}

    result = {'scope': 'precondition screen for acquisition policy as a '
                       'recursive transmissible state, on audited frozen banks',
              'pool_banks': n, 'threshold': THRESHOLD,
              'loo_marginal_value': marginal, 'by_budget': {}}

    for k in BUDGETS:
        arms = {}
        draws = []
        for _ in range(RANDOM_DRAWS):
            subset = [pool[i] for i in rng.choice(n, k, replace=False)]
            draws.append(np.asarray(system_score(subset, transfer), float))
        arms['random'] = np.mean(draws, axis=0)
        arms['first'] = np.asarray(system_score(pool[:k], transfer), float)
        for name, order in heuristics.items():
            arms[name] = np.asarray(
                system_score([pool[i] for i in order[:k]], transfer), float)
        arms['value_topk_UNAVAILABLE'] = np.asarray(
            system_score([pool[i] for i in value_order[:k]], transfer), float)

        free = {name: arm for name, arm in arms.items()
                if 'UNAVAILABLE' not in name and 'LABELLED' not in name}
        best_free = max(free, key=lambda name: free[name].sum())
        upper = arms['value_topk_UNAVAILABLE']
        regret = float(upper.sum() - free[best_free].sum())
        diffs = [int(round(a - b)) for a, b in zip(upper, free[best_free])]
        result['by_budget'][str(k)] = {
            'totals': {name: float(arm.sum()) for name, arm in arms.items()},
            'best_free_rule': best_free,
            'default_regret': regret,
            'regret_interval': interval(diffs),
            'p2c_passed': bool(regret > THRESHOLD)}
        print('budget K={}'.format(k), flush=True)
        for name, arm in sorted(arms.items(), key=lambda kv: -kv[1].sum()):
            print('   {:28s} {:7.1f}'.format(name, arm.sum()), flush=True)
        print('   best free = {}  regret = {:+.1f} {}  P2c={}'.format(
            best_free, regret, interval(diffs),
            result['by_budget'][str(k)]['p2c_passed']), flush=True)

    result['verdict'] = {k: v['p2c_passed'] for k, v in result['by_budget'].items()}
    result['limits'] = [
        'Leave-one-out marginal value uses transfer labels and is an upper '
        'reference, not a deployable policy, and top-K by marginal value is '
        'not the true best subset.',
        'Heuristics marked LABELLED need history labels and are shown for '
        'diagnosis; they are excluded from the free-rule set.',
        'Random is averaged over eight draws; the interval is bank-paired '
        'against the single best free rule.',
        'One replication pool and one transfer panel.']
    write_json(OUT, result)
    print('verdict:', result['verdict'])


if __name__ == '__main__':
    main()
