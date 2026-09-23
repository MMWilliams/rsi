"""A better way to turn worlds into a prior, and what it costs on the holdouts.

The prior confirmed in G2 scores an atom by its strongest pairwise affinity to
an atom already solved. Pairwise is a crude reading of what the training worlds
say: they are *sets*, and the evidence from a new world is also a set, so the
question "which training worlds look like this one" is answerable directly and
the pairwise summary throws most of it away.

This arm asks it directly. Each training world is kept as its observed atom
set; a new world's solved atoms weight those worlds by how many they contain,
with an exponential penalty per atom missed; the posterior over atoms is the
weighted average of the worlds' own indicators, mixed with a uniform floor so
that a world resembling nothing in training degrades to the free rule instead
of to nonsense. That last clause is rule 6 of
`MECHANISM-GROWTH-RESULTS-2026-09-21.md` built into the estimator rather than
bolted on, and it is what the identity affinity could not do.

  free_set        the strongest experience-free rule
  affinity        the confirmed prior, strongest pairwise affinity
  retrieval       weighted average over training worlds
  retrieval_flat  the same with every world weighted equally, which is the
                  control separating "retrieving the right worlds" from
                  "knowing the base rate of atoms"
  retrieval_scrambled   training worlds with their atom labels permuted

Development evidence; nothing frozen.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test
from rsi.mechanism_worlds import Harness, affinity, ranks_of

OUT = ROOT / 'analysis/mechanism-world-retrieval-20260921.json'
SEED = 608101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 16
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
HELD_OUT_FAMILIES = ('popcount', 'xormod')
HELD_OUT_TRIPLES = 6
MINIMUM_MEMBERS = 120
ADAPT = (1, 2, 4, 8, 16)
BUDGETS = (256, 1024, 4096, 16384, None)
FLOOR = 1e-4
MISS_PENALTY = .2
UNIFORM_MASS = .05
BOOT = 20000
ARMS = ('free_set', 'affinity', 'retrieval', 'retrieval_flat', 'retrieval_scrambled')


def retrieval_posterior(indicators, observed, flat=False):
    """Weighted average of training worlds' atom sets, given a world's solved atoms.

    `MISS_PENALTY` per observed atom a training world lacks, so worlds that
    contain everything seen so far dominate; `UNIFORM_MASS` of the posterior is
    spread over every atom, so a world resembling none of them still leaves
    every hypothesis reachable.
    """
    keys = indicators.shape[1]
    uniform = np.full(keys, 1. / keys)
    if not len(observed):
        return uniform
    if flat:
        weights = np.ones(len(indicators))
    else:
        misses = len(observed) - indicators[:, observed].sum(axis=1)
        weights = MISS_PENALTY ** misses
    total = weights.sum()
    if total <= 0:
        return uniform
    posterior = (weights[:, None] * indicators).sum(axis=0) / total
    return (1. - UNIFORM_MASS) * posterior + UNIFORM_MASS * uniform


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    catalog = harness.catalog
    keys = len(harness.key_names)
    rng = random.Random(SEED)
    harness.set_tiebreak(SEED + 77)

    seen_families = [family for family in sorted(harness.by_family)
                     if family not in HELD_OUT_FAMILIES]
    viable = [triple for triple in itertools.combinations(seen_families, FAMILIES_PER_WORLD)
              if harness.sample_world(triple, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)]
    held_triples = sorted(rng.sample(viable, HELD_OUT_TRIPLES))
    training_triples = [triple for triple in viable if triple not in held_triples]
    held_family_triples = [triple for triple in
                           itertools.combinations(sorted(harness.by_family),
                                                  FAMILIES_PER_WORLD)
                           if set(triple) & set(HELD_OUT_FAMILIES)]

    def draw(triples, count):
        out = []
        while len(out) < count:
            world = harness.sample_world(triples[rng.randrange(len(triples))], rng,
                                         KEYS_PER_WORLD, MINIMUM_MEMBERS)
            if world is not None:
                out.append(world)
        return out

    evaluation = {'seen_triple': draw(training_triples, EVAL_WORLDS),
                  'new_triple': draw(held_triples, EVAL_WORLDS),
                  'new_family': draw(held_family_triples, EVAL_WORLDS)}
    for worlds in evaluation.values():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            world['test'] = members[:TEST_MECHANISMS]
            world['pool'] = members[TEST_MECHANISMS:]
    reserved = {index for worlds in evaluation.values() for world in worlds
                for index in world['test']}

    training = draw(training_triples, TRAINING_WORLDS)
    observed_sets = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
        observed_sets.append(sorted({harness.key_index[key]
                                     for key in harness.observed_keys(solved)}))
    pairwise = affinity(observed_sets, keys)
    indicators = np.zeros((len(observed_sets), keys))
    for row, indices in enumerate(observed_sets):
        indicators[row, indices] = 1.
    permutation = np.random.default_rng(SEED + 5).permutation(keys)
    scrambled = indicators[:, permutation]

    arms = [f'{name}:{k}' for k in ADAPT for name in ARMS]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}

    for split, worlds in evaluation.items():
        for world in worlds:
            ranks = {}
            for k in ADAPT:
                counts = harness.key_counts(world['pool'][:k])
                present = list(np.flatnonzero(counts))
                direct = (counts > 0).astype(float)
                scores = {
                    'free_set': direct,
                    'affinity': np.maximum(
                        direct, pairwise[present].max(axis=0) if present else 0.),
                    'retrieval': np.maximum(
                        direct, retrieval_posterior(indicators, present)),
                    'retrieval_flat': np.maximum(
                        direct, retrieval_posterior(indicators, present, flat=True)),
                    'retrieval_scrambled': np.maximum(
                        direct, retrieval_posterior(scrambled, present)),
                }
                for name, score in scores.items():
                    ranks[f'{name}:{k}'] = ranks_of(
                        harness.order_from_key_scores(np.log(score + FLOOR)))
            for mechanism in world['test']:
                task = make_task(catalog, mechanism, rng)
                consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                        task['visible_neg']))
                if len(consistent) == 0:
                    continue
                good = vector_test(harness.packed, task['hidden_pos'],
                                   task['hidden_neg'])[consistent]
                select = np.lexsort((harness.complexity[consistent],
                                     harness.sizes[consistent]))
                for arm in arms:
                    ranked = ranks[arm][consistent]
                    for budget in BUDGETS:
                        limit = catalog.size if budget is None else budget
                        hit = 0
                        for candidate in select:
                            if ranked[candidate] < limit:
                                hit = int(good[candidate])
                                break
                        outcomes[split][arm][budget].append(hit)

    boot = np.random.default_rng(SEED + 9)
    result = {'scope': 'world retrieval against pairwise affinity',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'miss_penalty': MISS_PENALTY,
              'uniform_mass': UNIFORM_MASS, 'seed': SEED, 'splits': {}}

    for split in evaluation:
        tasks = len(outcomes[split][arms[0]][BUDGETS[0]])
        draws = boot.integers(0, tasks, (BOOT, tasks))

        def paired(a, b, budget):
            difference = np.asarray(outcomes[split][a][budget], float) - \
                np.asarray(outcomes[split][b][budget], float)
            sums = difference[draws].sum(axis=1)
            return {'sum': float(difference.sum()), 'tasks': tasks,
                    'interval': [float(np.percentile(sums, 2.5)),
                                 float(np.percentile(sums, 97.5))]}

        rate = {arm: {str(budget): float(np.mean(outcomes[split][arm][budget]))
                      for budget in BUDGETS} for arm in arms}
        entry = {'tasks': tasks, 'rate': rate}
        for left, right in (('retrieval', 'free_set'), ('retrieval', 'affinity'),
                            ('retrieval', 'retrieval_flat'),
                            ('retrieval', 'retrieval_scrambled'),
                            ('affinity', 'free_set')):
            entry[f'{left}_minus_{right}'] = {
                str(k): {str(budget): paired(f'{left}:{k}', f'{right}:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        result['splits'][split] = entry

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for split in ('seen_triple', 'new_triple', 'new_family'):
        entry = result['splits'][split]
        print('\n== {}: {} tasks'.format(split, entry['tasks']))
        print('arm'.ljust(24) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(24) + ''.join('{:9.3f}'.format(entry['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        for key in ('retrieval_minus_free_set', 'retrieval_minus_affinity',
                    'retrieval_minus_retrieval_flat'):
            print(key + ':')
            for k in ADAPT:
                row = entry[key][str(k)]
                print('  k={:<3d}'.format(k) + ''.join(
                    '{:+6.0f}{:<13s}'.format(row[str(b)]['sum'],
                                             str([round(x) for x in row[str(b)]['interval']]))
                    for b in ('256', '1024', '4096', '16384')))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
