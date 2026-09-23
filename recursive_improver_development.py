"""Recursive growth: does a later parent produce a BETTER CHILD IMPROVER?

Improver growth is established: more verified history builds a better system.
Recursive growth is a different and stronger claim, and it is the one the
measurement contract has always listed as unmet. It asks whether a later parent
improves the *improvement process* it hands on, not the artifact it builds.

The design keeps the child's data fixed so only the inherited process varies:

  - Each parent holds history A of its own size and selects a **partition
    scheme** from a catalog by leave-one-bank-out cross-validation on A. That
    scheme is its entire transmissible state; no model, no router, no labels.
  - Every child receives one scheme, an **identical fresh history B** that no
    parent saw, and builds its own partition, specialists and router on B.
  - Children are scored on an untouched transfer panel T.

So C(late) and C(early) differ only in the scheme they inherited. A gain is
attributable to the parent having learned a better way to build, which is the
recursive claim.

Controls: the researcher default scheme, which needs no parent at all and is the
zero-knowledge baseline; and a scrambled scheme drawn at random from the catalog.

Development evidence on opened cached panels.
"""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import SOURCE, TARGET
import construction_improver_development as dev


OUT = ROOT / 'analysis/recursive-improver-development-20260921.json'
SCHEMES = {
    'flat': (),
    'coarse': (3,),
    'default': (3, 15),
    'fine': (2, 6, 20),
    'finest': (1, 3, 8, 25),
}
DEFAULT_SCHEME = 'default'
EARLY_BANKS = 4
LATE_BANKS = 32
CHILD_BANKS = 12
CV_FOLDS = 3
THRESHOLD = 6
SEED = 915001


def bin_of(labels, edges):
    """Complexity bin under one scheme. `edges` are first-correct-rank cuts."""
    for rank, y in enumerate(labels):
        if y:
            for index, edge in enumerate(edges):
                if rank < edge:
                    return f'b{index}'
            return f'b{len(edges)}'
    return 'unreachable'


def build_with(history, edges):
    """Same construction as the improver, under a given partition scheme."""
    tasks = [t for bank in history for t in bank]
    groups = {}
    for task in tasks:
        groups.setdefault(bin_of(task['labels'], edges), []).append(task)
    specialists = {}
    for name, group in groups.items():
        if name == 'unreachable' or len(group) < 8:
            continue
        x = np.concatenate([t['x'] for t in group])
        y = np.concatenate([np.asarray(t['labels'], np.int8) for t in group])
        if 0 < y.sum() < len(y):
            specialists[name] = model_for(15).fit(x, y)
    px = np.concatenate([t['x'] for t in tasks])
    py = np.concatenate([np.asarray(t['labels'], np.int8) for t in tasks])
    specialists['pooled'] = model_for(15).fit(px, py)
    return specialists


def system_on(history, edges):
    specialists = build_with(history, edges)
    order = sorted(specialists)
    actions = order + ['e0']
    router = dev.fit_router(history, specialists, actions, order)
    return specialists, router, actions, order


def score_on(transfer, history, edges):
    specialists, router, actions, order = system_on(history, edges)
    return dev.deploy(transfer, specialists, router, actions, order)


def parent_selects(history):
    """Leave-a-block-out CV over the catalog, on the parent's history only."""
    size = max(1, len(history) // CV_FOLDS)
    folds = [history[i:i + size] for i in range(0, len(history), size)][:CV_FOLDS]
    scores = {}
    for name, edges in SCHEMES.items():
        total = 0
        for held in folds:
            rest = [b for b in history if b not in held]
            if not rest or not held:
                continue
            total += sum(score_on(held, rest, edges))
        scores[name] = total
    best = max(scores, key=lambda k: (scores[k], k == DEFAULT_SCHEME, k))
    return best, scores


def compare(left, right):
    diffs = [int(round(a - b)) for a, b in zip(left, right)]
    return {'gain': sum(diffs), 'positive_banks': sum(d > 0 for d in diffs),
            'losing_banks': sum(d < 0 for d in diffs),
            'interval': interval(diffs)}


def main():
    if OUT.exists():
        raise RuntimeError('development exists')
    panels = dev.load_banks()
    transfer_name = TARGET[2]
    transfer = panels[transfer_name]
    pool = [bank for name, banks in panels.items()
            if name != transfer_name for bank in banks]

    # Parents see the front of the pool; the child's history is disjoint and at
    # the back, so no parent has seen a single one of the child's banks.
    child_history = pool[-CHILD_BANKS:]
    parent_pool = pool[:-CHILD_BANKS]
    early_history = parent_pool[:EARLY_BANKS]
    late_history = parent_pool[:LATE_BANKS]
    assert not any(b in child_history for b in late_history)

    early_scheme, early_scores = parent_selects(early_history)
    late_scheme, late_scores = parent_selects(late_history)
    rng = np.random.default_rng(SEED)
    scrambled_scheme = sorted(SCHEMES)[int(rng.integers(len(SCHEMES)))]
    print('early parent ({} banks) selects {} from {}'.format(
        EARLY_BANKS, early_scheme, early_scores), flush=True)
    print('late  parent ({} banks) selects {} from {}'.format(
        LATE_BANKS, late_scheme, late_scores), flush=True)

    children = {}
    for label, scheme in (('early', early_scheme), ('late', late_scheme),
                          ('default', DEFAULT_SCHEME),
                          ('scrambled', scrambled_scheme)):
        children[label] = {'scheme': scheme,
                           'per_bank': score_on(transfer, child_history,
                                                SCHEMES[scheme])}
        print('child[{:9s}] scheme={:7s} total={}'.format(
            label, scheme, sum(children[label]['per_bank'])), flush=True)

    g3 = compare(children['late']['per_bank'], children['early']['per_bank'])
    vs_default = compare(children['late']['per_bank'],
                         children['default']['per_bank'])
    vs_scrambled = compare(children['late']['per_bank'],
                           children['scrambled']['per_bank'])

    result = {
        'scope': 'opened development; recursive child-improver growth',
        'transfer_panel': transfer_name,
        'schemes': {k: list(v) for k, v in SCHEMES.items()},
        'early_banks': EARLY_BANKS, 'late_banks': LATE_BANKS,
        'child_history_banks': CHILD_BANKS,
        'parent_selection': {'early': {'scheme': early_scheme,
                                       'cv_scores': early_scores},
                             'late': {'scheme': late_scheme,
                                      'cv_scores': late_scores}},
        'children': {k: {'scheme': v['scheme'], 'total': sum(v['per_bank']),
                         'per_bank': v['per_bank']}
                     for k, v in children.items()},
        'gates': {
            'G3_recursive_growth': {
                **g3,
                'passed': bool(g3['gain'] >= THRESHOLD
                               and g3['losing_banks'] <= 4
                               and g3['interval'][0] > 0)},
            'G3b_beats_default_scheme': {
                **vs_default,
                'passed': bool(vs_default['gain'] > 0
                               and vs_default['interval'][0] > 0)}},
        'late_minus_scrambled': vs_scrambled,
        'limits': [
            'Opened cached panels; development evidence only.',
            'If both parents select the same scheme the children are identical '
            'by construction and G3 is vacuous; that outcome is reported, not '
            'hidden.',
            'The scheme catalog is researcher written; the parent chooses '
            'within it rather than inventing new schemes.',
            'One child history and one transfer panel, so this is a single '
            'draw, not a replication.']}
    write_json(OUT, result)
    print('G3 recursive growth      : {:+d} {}w/{}l {} passed={}'.format(
        g3['gain'], g3['positive_banks'], g3['losing_banks'], g3['interval'],
        result['gates']['G3_recursive_growth']['passed']))
    print('G3b vs default scheme    : {:+d} {} passed={}'.format(
        vs_default['gain'], vs_default['interval'],
        result['gates']['G3b_beats_default_scheme']['passed']))
    print('late vs scrambled scheme : {:+d} {}'.format(
        vs_scrambled['gain'], vs_scrambled['interval']))
    if early_scheme == late_scheme:
        print('NOTE: both parents chose the same scheme; G3 is vacuous here.')


if __name__ == '__main__':
    main()
