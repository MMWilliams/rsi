"""Deploy the trained coach only where validation says it helps.

Three development runs with the hedge share fixed or guarded show the trained
coach improving every budget from 1024 up and, in one run of two, losing
significantly at a tight budget under a shift (`mechanism-coach-fixed-hedge-dev`:
-96 at 128 on untrained combinations; `mechanism-coach-practice-dev`: the
family-practice coach passes every cell at generation 40 and loses up to 190 at
generation 20). The loss moves between seeds and checkpoints, so no lever can be
blamed for it.

The standard answer is high-confidence policy improvement: after training,
compare the coach with the champion on validation lifetimes drawn the way
training draws them, never from evaluation worlds, and deploy the coach at a
budget only if it wins there; otherwise the agent runs the champion at that
budget. The validation kinds are the three the claim is scored on, built from
training material alone: in-support worlds, worlds of a training family lived
with a prior fitted without that family, and worlds of a training combination
lived with a prior fitted without that combination.

Two rules. v1, fixed before the first run of this script: deploy at a budget
iff the pooled paired bootstrap interval over all validation worlds is entirely
above zero and the point estimate is positive in each of the three kinds. v2,
the high-confidence form, added after v1's first run showed its only fallback
came from the pooled interval touching zero while the combination kind was
positive at a budget where held-out untrained combinations lost: deploy iff
the interval is entirely above zero **in each kind separately**. 32 validation
worlds per kind; both rules are reported.

Applied retrospectively to the two fixed-hedge coaches whose held-out totals
already exist; their evaluation worlds are not touched here, and the deployed
policy's held-out totals are read from those runs (coach at deployed budgets,
champion elsewhere). Development evidence.
"""
from __future__ import annotations

import json
import random
import sys
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import (CHAMPION, Coach, Pool, Prior, Simulator, draw_worlds,
                              observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-validation-gate-v2-20260923.json'
RUNS = {'fixed_hedge': ('analysis/mechanism-coach-fixed-hedge-dev-20260923.json', 625101,
                        lambda d: d['checkpoints']['40'], 'coach@40'),
        'practice_family_only': ('analysis/mechanism-coach-practice-dev-20260923.json', 626101,
                                 lambda d: d['checkpoints']['family_only']['40'],
                                 'family_only@40')}
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 32
VALIDATION_WORLDS = 32
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
KINDS = ('supported', 'family', 'combination')
BOOT = 20000


def interval(difference, seed):
    draws = np.random.default_rng(seed).integers(0, len(difference), (BOOT, len(difference)))
    sums = difference[draws].sum(axis=1)
    return np.percentile(sums, 2.5, axis=0), np.percentile(sums, 97.5, axis=0)


def validate(name, dev_path, seed, coach):
    """Rebuild a dev run's training material and score coach and champion on
    fresh validation lifetimes of each kind."""
    harness = Harness()
    harness.set_tiebreak(seed + 77)
    simulator = Simulator(harness)
    rng = random.Random(seed)
    seen = [family for family in harness.by_family if family not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    rng.shuffle(seen_pool)
    cut = max(1, round(NEW_TRIPLE_SHARE * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {g: draw_worlds(harness, pool_, EVAL_WORLDS, rng, KEYS_PER_WORLD,
                             MINIMUM_MEMBERS, STREAM)
              for g, pool_ in (('seen_triple', train_triples), ('new_triple', new_triples),
                               ('new_family', held_pool))}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, train_triples, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    observed = observed_sets(harness, training, reserved, PRIOR_SOLVED, rng)
    priors = {'main': Prior(harness, observed)}
    families = sorted({family for triple in train_triples for family in triple})
    for family in families:
        priors[f'without:{family}'] = Prior(
            harness, [s for w, s in zip(training, observed) if family not in w['triple']])
    for triple in train_triples:
        priors[f'without:{"+".join(sorted(triple))}'] = Prior(
            harness, [s for w, s in zip(training, observed) if w['triple'] != tuple(sorted(triple))])

    # A stream no dev run drew from.
    stream_rng = random.Random(seed + 51)

    def fresh(triple_pool):
        world, = draw_worlds(harness, triple_pool, 1, stream_rng, KEYS_PER_WORLD,
                             MINIMUM_MEMBERS, STREAM + 40)
        stream = [index for index in world['stream'] if index not in reserved][:STREAM]
        return simulator.views(stream, stream_rng)

    lives = {kind: [] for kind in KINDS}
    for _ in range(VALIDATION_WORLDS):
        lives['supported'].append((fresh(train_triples), 'main'))
        family = families[stream_rng.randrange(len(families))]
        lives['family'].append((fresh([t for t in train_triples if family in t]),
                                f'without:{family}'))
        triple = train_triples[stream_rng.randrange(len(train_triples))]
        lives['combination'].append((fresh([triple]), f'without:{"+".join(sorted(triple))}'))

    pool = Pool(12, seed + 77, priors, {}, BUDGETS)
    differences = {}
    for kind in KINDS:
        results = pool.map([(arm, views, 'earned', prior) for arm in (coach, CHAMPION)
                            for views, prior in lives[kind]])
        totals = np.array([[h.sum() for h in r] for r in results], dtype=float)
        differences[kind] = totals[:VALIDATION_WORLDS] - totals[VALIDATION_WORLDS:]
    pool.close()
    pooled = np.concatenate([differences[k] for k in KINDS])
    low, high = interval(pooled, seed + 52)
    by_kind = {k: differences[k].sum(axis=0) for k in KINDS}
    kind_low = {k: interval(differences[k], seed + 53 + i)[0] for i, k in enumerate(KINDS)}
    v1 = [bool(low[b] > 0 and all(by_kind[k][b] > 0 for k in KINDS))
          for b in range(len(BUDGETS))]
    v2 = [bool(all(kind_low[k][b] > 0 for k in KINDS)) for b in range(len(BUDGETS))]
    return {'pooled': {'sum': pooled.sum(axis=0).tolist(), 'low': low.tolist(),
                       'high': high.tolist()},
            'by_kind': {k: v.tolist() for k, v in by_kind.items()},
            'by_kind_low': {k: v.tolist() for k, v in kind_low.items()},
            'deploy': {'v1': v1, 'v2': v2}}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    result = {'scope': 'high-confidence deployment of the trained coach, retrospective',
              'rule': 'deploy at a budget iff pooled validation interval > 0 and every kind > 0',
              'validation_worlds_per_kind': VALIDATION_WORLDS, 'budgets': list(BUDGETS),
              'runs': {}}
    for name, (path, seed, pick, arm) in RUNS.items():
        dev = json.loads((ROOT / path).read_text())
        coach = Coach(**pick(dev))
        gate = validate(name, path, seed, coach)
        deployed = {rule: {} for rule in ('v1', 'v2')}
        for rule in deployed:
            for split, block in dev['groups'].items():
                coach_totals = np.array(block['per_world'][arm])
                champion_totals = np.array(block['per_world']['champion'])
                policy = np.where(np.array(gate['deploy'][rule])[None, :], coach_totals,
                                  champion_totals)
                low, high = interval(policy - champion_totals, seed + 3)
                deployed[rule][split] = {'sum': (policy - champion_totals).sum(axis=0).tolist(),
                                         'low': low.tolist(), 'high': high.tolist()}
        result['runs'][name] = {'seed': seed, 'coach': coach.as_dict(), 'validation': gate,
                                'deployed_minus_champion': deployed}
        print(f'\n== {name} (seed {seed}): deploy v1 {dict(zip(BUDGETS, gate["deploy"]["v1"]))}'
              f' v2 {dict(zip(BUDGETS, gate["deploy"]["v2"]))}')
        print('  validation pooled ' + ''.join(
            '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17) for s, lo, hi in
            zip(gate['pooled']['sum'], gate['pooled']['low'], gate['pooled']['high'])))
        for kind, sums in gate['by_kind'].items():
            print('  {:18s}'.format(kind) + ''.join(
                '{:+5.0f} (low {:+.0f})'.format(s, lo).rjust(17)
                for s, lo in zip(sums, gate['by_kind_low'][kind])))
        for rule, splits in deployed.items():
            for split, entry in splits.items():
                print('  {} held-out {:9s}'.format(rule, split) + ''.join(
                    '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                    for s, lo, hi in zip(entry['sum'], entry['low'], entry['high'])))
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
