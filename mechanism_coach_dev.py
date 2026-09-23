"""A coach trained by reinforcement learning on lifetimes, scored on worlds it
never lived in.

`rsi/growth_coach.py` defines the coach: an external component whose
parameters set the free choices of the earned loop. Here it is trained by
evolution-strategies policy search (antithetic Gaussian perturbations, common
random numbers, centred-rank fitness shaping) on the return of whole lifetimes:
tasks solved over a stream of 100, at six budgets. Training is continual: each
generation lives through worlds never lived in before, so the coach's
experience is a stream and its checkpoints give a curve of held-out value
against lifetimes of experience. It starts as the champion (cold-start pair
prior, half the budget hedged), so any change is what training bought.

The hedge share is trainable, and a coach trained only where the prior is in
support would learn to drop it: nothing in its experience would say the prior
can be wrong. So a quarter of its lifetimes are *practice at unfamiliarity*
built from familiar material alone: a world containing one training family,
lived with a prior fitted on the training worlds that do not contain that
family. The two families no training world contains appear only in evaluation.
Fitness is ranked separately on in-support and practice lifetimes and averaged,
so neither can be traded away unseen.

Held-out worlds, never lived in by the coach and never used by any prior:

  seen_triple  family combinations the training worlds used, fresh key sets
  new_triple   family combinations no training world used
  new_family   a family no training world contained

Arms scored on them, all at the same six budgets:

  champion       the starting point
  coach@g        the trained coach after g generations
  random_search  best of randomly perturbed champions, chosen on the same
                 number of training lifetimes as the coach consumed: is the
                 policy-search update doing anything beyond best-of-N?
  per_budget     six coaches, one per budget, trained on the same lifetimes
                 split by budget: the capacity arm
  no_practice    the same training with the practice lifetimes replaced by
                 in-support ones: what practice at unfamiliarity buys
  blind, warm, revealed   the loop with no prior, the unhedged prior, and the
                 informed ceiling

Development evidence; nothing frozen. Any claim goes through a predeclared
protocol on fresh seeds.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.growth_coach import (BLIND, CHAMPION, UNHEDGED, Coach, Pool, Prior, Simulator,
                              draw_worlds, observed_sets, triples)
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-coach-dev-20260923.json'
SEED = 621101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 32
STREAM = 100
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
NEW_TRIPLE_SHARE = .2
BUDGETS = (128, 256, 512, 1024, 2048, 4096)
WORKERS = 12
SEARCHED = ('unknown', 'pair', 'count', 'depth1', 'affinity', 'soft', 'pick', 'hedge',
            'hedge_slope', 'tilt')
SIGMA = {'unknown': .2, 'pair': .2, 'count': .25, 'depth1': 1., 'affinity': .25,
         'soft': .2, 'pick': .25, 'hedge': .15, 'hedge_slope': .08, 'tilt': .2}
PAIRS = 8
SUPPORTED_PER_GENERATION = 6
PRACTICE_PER_GENERATION = 2
GENERATIONS = 40
LEARNING_RATE = 1.
CHECKPOINTS = (0, 5, 10, 20, 40)
RANDOM_CANDIDATES = 160
BOOT = 20000


def centred_ranks(values):
    ranks = np.empty(len(values))
    ranks[np.argsort(values, kind='stable')] = np.arange(len(values))
    return ranks / (len(values) - 1) - .5


def shaped(totals, kinds):
    """Centred ranks per budget and per kind of lifetime, averaged: each
    budget and each kind carries equal weight whatever its scale."""
    columns = [centred_ranks(totals[kind][:, b]) for kind in kinds
               for b in range(totals[kind].shape[1])]
    return np.mean(columns, axis=0)


class Trainer:
    """Evolution strategies over the searched coach fields.

    `budget_sets` lists which budgets each coach is scored on; one set with
    every budget trains a single shared coach, six singleton sets train the
    per-budget capacity arm on the same lifetimes.
    """

    def __init__(self, budget_sets, seed):
        self.budget_sets = budget_sets
        self.index = [list(Coach.__dataclass_fields__).index(name) for name in SEARCHED]
        self.sigma = np.array([SIGMA[name] for name in SEARCHED])
        self.means = [CHAMPION.vector() for _ in budget_sets]
        self.rng = np.random.default_rng(seed)

    def coach(self, slot, noise=None):
        vector = self.means[slot].copy()
        if noise is not None:
            vector[self.index] += self.sigma * noise
        return Coach.from_vector(vector).clipped()

    def generation(self, pool, lifetimes):
        """One update from `lifetimes`, a list of (views, prior name, kind)."""
        plans = []
        for slot, budgets in enumerate(self.budget_sets):
            noise = self.rng.standard_normal((PAIRS, len(self.index)))
            coaches = [self.coach(slot, sign * row) for row in noise for sign in (1, -1)]
            plans.append((slot, budgets, noise, coaches))
        jobs = [(coach, views, 'earned', prior, budgets)
                for _slot, budgets, _noise, coaches in plans
                for coach in coaches for views, prior, _kind in lifetimes]
        results = iter(pool.map(jobs))
        kinds = sorted({kind for _views, _prior, kind in lifetimes})
        for slot, budgets, noise, coaches in plans:
            totals = {kind: np.zeros((len(coaches), len(budgets))) for kind in kinds}
            for number in range(len(coaches)):
                for _views, _prior, kind in lifetimes:
                    totals[kind][number] += [hits.sum() for hits in next(results)]
            fitness = shaped(totals, kinds)
            gradient = ((fitness[0::2] - fitness[1::2])[:, None] * noise).mean(axis=0)
            self.means[slot][self.index] += LEARNING_RATE * self.sigma * gradient
            self.means[slot] = self.coach(slot).vector()


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    simulator = Simulator(harness)
    rng = random.Random(SEED)
    seen = [family for family in harness.by_family if family not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    rng.shuffle(seen_pool)
    cut = max(1, round(NEW_TRIPLE_SHARE * len(seen_pool)))
    new_triples, train_triples = seen_pool[:cut], seen_pool[cut:]
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {name: draw_worlds(harness, pool_, EVAL_WORLDS, rng, KEYS_PER_WORLD,
                                MINIMUM_MEMBERS, STREAM)
              for name, pool_ in (('seen_triple', train_triples), ('new_triple', new_triples),
                                  ('new_family', held_pool))}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, train_triples, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    observed = observed_sets(harness, training, reserved, PRIOR_SOLVED, rng)
    priors = {'main': Prior(harness, observed)}
    practice_families = sorted({family for triple in train_triples for family in triple})
    for family in practice_families:
        kept = [sets for world, sets in zip(training, observed) if family not in world['triple']]
        priors[f'without:{family}'] = Prior(harness, kept)
    views = {f'{group}:{number:02d}': simulator.views(world['stream'], rng)
             for group, worlds in groups.items() for number, world in enumerate(worlds)}
    names = {group: [key for key in views if key.startswith(group + ':')] for group in groups}

    def fresh_views(triple_pool, count, stream_rng):
        out = []
        for world in draw_worlds(harness, triple_pool, count, stream_rng, KEYS_PER_WORLD,
                                 MINIMUM_MEMBERS, STREAM + 40):
            stream = [index for index in world['stream'] if index not in reserved][:STREAM]
            out.append((simulator.views(stream, stream_rng), world['triple']))
        return out

    def lifetimes(stream_rng, practice=True):
        supported = SUPPORTED_PER_GENERATION + (0 if practice else PRACTICE_PER_GENERATION)
        out = [(v, 'main', 'supported')
               for v, _t in fresh_views(train_triples, supported, stream_rng)]
        if practice:
            for _ in range(PRACTICE_PER_GENERATION):
                family = practice_families[stream_rng.randrange(len(practice_families))]
                with_family = [t for t in train_triples if family in t]
                (v, _t), = fresh_views(with_family, 1, stream_rng)
                out.append((v, f'without:{family}', 'practice'))
        return out

    pool = Pool(WORKERS, SEED + 77, priors, views, BUDGETS)
    print('setup', round(time.perf_counter() - wall), 's; triples: train',
          len(train_triples), 'new', len(new_triples), 'held', len(held_pool), flush=True)

    shared = Trainer([BUDGETS], SEED + 21)
    per_budget = Trainer([(budget,) for budget in BUDGETS], SEED + 22)
    no_practice = Trainer([BUDGETS], SEED + 21)
    stream_rng = random.Random(SEED + 31)
    plain_rng = random.Random(SEED + 32)
    checkpoints = {0: CHAMPION}
    consumed = 0
    for generation in range(1, GENERATIONS + 1):
        batch = lifetimes(stream_rng)
        shared.generation(pool, batch)
        per_budget.generation(pool, batch)
        no_practice.generation(pool, lifetimes(plain_rng, practice=False))
        consumed += 2 * PAIRS * len(batch) * len(BUDGETS)
        if generation in CHECKPOINTS:
            checkpoints[generation] = shared.coach(0)
        print('generation {:2d} ({:.0f}s): {}'.format(
            generation, time.perf_counter() - wall,
            {k: round(v, 2) for k, v in shared.coach(0).as_dict().items()}), flush=True)

    # Random search on the same number of lifetimes, drawn the same way: every
    # candidate is scored on the same lifetimes and the best shaped one kept.
    search_rng = random.Random(SEED + 41)
    per_candidate = consumed // (RANDOM_CANDIDATES * len(BUDGETS))
    batch = []
    while len(batch) < per_candidate:
        batch.extend(lifetimes(search_rng))
    batch = batch[:per_candidate]
    noise = np.random.default_rng(SEED + 42).standard_normal(
        (RANDOM_CANDIDATES - 1, len(SEARCHED)))
    base = Trainer([BUDGETS], SEED + 43)
    candidates = [CHAMPION] + [base.coach(0, 2. * row) for row in noise]
    results = iter(pool.map([(coach, views, 'earned', prior)
                             for coach in candidates for views, prior, _kind in batch]))
    kinds = sorted({kind for _v, _p, kind in batch})
    totals = {kind: np.zeros((len(candidates), len(BUDGETS))) for kind in kinds}
    for number in range(len(candidates)):
        for _views, _prior, kind in batch:
            totals[kind][number] += [hits.sum() for hits in next(results)]
    random_best = candidates[int(np.argmax(shaped(totals, kinds)))]
    print('random search:', per_candidate, 'lifetimes per candidate, chose',
          {k: round(v, 2) for k, v in random_best.as_dict().items()}, flush=True)

    arms = {'static': (BLIND, 'static'), 'blind': (BLIND, 'earned'),
            'warm': (UNHEDGED, 'earned'), 'champion': (CHAMPION, 'earned'),
            'revealed': (BLIND, 'revealed'), 'random_search': (random_best, 'earned'),
            'no_practice': (no_practice.coach(0), 'earned')}
    arms.update({f'coach@{g}': (coach, 'earned') for g, coach in checkpoints.items() if g})
    table = {}
    for group in groups:
        results = pool.map([(coach, world, arm, 'main')
                            for coach, arm in arms.values() for world in names[group]])
        table[group] = {}
        for number, name in enumerate(arms):
            chunk = results[number * len(names[group]):(number + 1) * len(names[group])]
            table[group][name] = np.array([[hits for hits in per_world] for per_world in chunk])
        chunk = pool.map([(per_budget.coach(slot), world, 'earned', 'main', (budget,))
                          for world in names[group] for slot, budget in enumerate(BUDGETS)])
        table[group]['per_budget'] = np.array(
            [[chunk[w * len(BUDGETS) + b][0] for b in range(len(BUDGETS))]
             for w in range(len(names[group]))])
    pool.close()

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, EVAL_WORLDS, (BOOT, EVAL_WORLDS))
    final = f'coach@{GENERATIONS}'
    result = {'scope': 'a coach trained by policy search on lifetimes, held-out worlds',
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'seed': SEED, 'budgets': list(BUDGETS), 'stream': STREAM,
              'training_worlds_for_prior': TRAINING_WORLDS, 'generations': GENERATIONS,
              'coach_training_lifetimes': consumed,
              'held_out_families': list(HELD_OUT_FAMILIES),
              'new_triples': [list(t) for t in new_triples],
              'checkpoints': {str(g): coach.as_dict() for g, coach in checkpoints.items()},
              'per_budget': {str(b): per_budget.coach(s).as_dict()
                             for s, b in enumerate(BUDGETS)},
              'no_practice': no_practice.coach(0).as_dict(),
              'random_search': random_best.as_dict(), 'groups': {}}
    for group, arms_ in table.items():
        totals = {name: values.sum(axis=2) for name, values in arms_.items()}
        block = {'solved_mean_by_budget': {name: values.mean(axis=0).tolist()
                                           for name, values in totals.items()},
                 'per_world': {name: values.tolist() for name, values in totals.items()},
                 'first_vs_last_twenty': {name: [values[:, :, :20].mean(axis=(0, 2)).tolist(),
                                                 values[:, :, -20:].mean(axis=(0, 2)).tolist()]
                                          for name, values in arms_.items()},
                 'contrasts': {}}
        for left, right in ([(f'coach@{g}', 'champion') for g in CHECKPOINTS if g]
                            + [(final, 'random_search'), (final, 'per_budget'),
                               (final, 'no_practice'), (final, 'warm'),
                               ('random_search', 'champion'), ('per_budget', 'champion')]):
            difference = totals[left] - totals[right]
            sums = difference[draws].sum(axis=1)
            block['contrasts'][f'{left} - {right}'] = {
                'sum': difference.sum(axis=0).tolist(),
                'low': np.percentile(sums, 2.5, axis=0).tolist(),
                'high': np.percentile(sums, 97.5, axis=0).tolist()}
        result['groups'][group] = block
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds_parent': time.process_time() - cpu,
                      'peak_rss_mb_parent': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for group, block in result['groups'].items():
        print(f'\n== {group}: mean tasks solved of {STREAM}, by budget')
        print('arm'.ljust(16) + ''.join(str(b).rjust(8) for b in BUDGETS))
        for name, values in block['solved_mean_by_budget'].items():
            print(name.ljust(16) + ''.join('{:8.1f}'.format(v) for v in values))
        for name, entry in block['contrasts'].items():
            print('  {:30s}'.format(name) + ''.join(
                '{:+5.0f} [{:.0f},{:.0f}]'.format(s, lo, hi).rjust(17)
                for s, lo, hi in zip(entry['sum'], entry['low'], entry['high'])))
    print('cost: {:.0f}s wall'.format(result['cost']['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
