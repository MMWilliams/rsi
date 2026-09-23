"""A learned metric over atom behaviour, and whether it reaches a new family.

An acquired prior over atom identities transfers to an unfamiliar combination
of families and fails on an unfamiliar family, because identity has no entry
for an atom never seen. Describing atoms by the magnitude spectrum of their
mask gives every atom, seen or not, a description; but an untrained cosine over
those descriptions was matched by the same descriptions permuted across atoms
(`mechanism-family-transfer-20260921.json`), so that arm was reading the shape
of a soft prior, not the behaviour of the atoms. The descriptor separates
families unevenly: the gap between within-family and between-family similarity
is +0.396 for thresholds and +0.296 for moduli, but +0.080 for popcounts, which
is one of the two withheld families.

This asks whether experience can supply what the raw cosine did not: a metric.
The training worlds label pairs of atoms by whether they belong to one world,
and a diagonal metric over whitened spectral dimensions is fitted to that. The
metric is a function of description alone, so it applies to atoms no training
world contained, while everything it knows came from worlds that did.

  free_set        the strongest experience-free rule: the solved atoms, as a set
  free_cosine     untrained whitened cosine to the solved atoms
  meta_identity   affinity over atom identities
  meta_metric     the fitted metric
  meta_both       the higher of identity and metric, the system one would deploy
  meta_metric_scrambled   the metric with descriptions permuted across atoms,
                  the control that decides whether the behaviour or the shape
                  of the prior is doing the work

Development evidence on opened draws; nothing is frozen here.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil
from sklearn.linear_model import LogisticRegression

from rsi.common import ROOT, write_json
from rsi.mechanism_worlds import Harness, affinity, ranks_of
from mechanism_family_transfer import descriptors

OUT = ROOT / 'analysis/mechanism-metric-transfer-20260921.json'
SEED = 605101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 16
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
ADAPT = (1, 2, 4, 8, 16)
BUDGETS = (256, 1024, 4096, 16384, 65536, None)
HELD_OUT_FAMILIES = ('popcount', 'xormod')
HELD_OUT_TRIPLES = 6
MINIMUM_MEMBERS = 120
FLOOR = 1e-4
BOOT = 20000
POSITIVE_PAIRS = 24
NEGATIVE_PAIRS = 48
ARMS = ('free_set', 'free_cosine', 'meta_identity', 'meta_metric', 'meta_both',
        'meta_metric_scrambled')


def whiten(block):
    centred = block - block.mean(axis=0, keepdims=True)
    scale = centred.std(axis=0, keepdims=True)
    return centred / np.maximum(scale, 1e-9)


def fit_metric(latent, observed_sets, rng):
    """A diagonal metric on whitened descriptions, fitted to world co-membership.

    The label is the only thing experience supplies: were these two atoms ever
    in one world. The features are products of description dimensions, so the
    fitted object is a similarity an unseen atom can be measured with.
    """
    size = latent.shape[0]
    features, labels = [], []
    for indices in observed_sets:
        indices = list(indices)
        if len(indices) < 2:
            continue
        for _ in range(POSITIVE_PAIRS):
            left, right = rng.sample(indices, 2)
            features.append(latent[left] * latent[right])
            labels.append(1)
        for _ in range(NEGATIVE_PAIRS):
            left = rng.choice(indices)
            right = rng.randrange(size)
            if right in indices:
                continue
            features.append(latent[left] * latent[right])
            labels.append(0)
    model = LogisticRegression(max_iter=3000, C=.25)
    model.fit(np.asarray(features), np.asarray(labels))
    return model


def metric_scores(model, latent, observed):
    """Highest fitted co-membership probability against any solved atom."""
    if not len(observed):
        return np.zeros(latent.shape[0])
    weight = model.coef_[0]
    logits = (latent * weight) @ latent[observed].T + model.intercept_[0]
    return 1. / (1. + np.exp(-logits.max(axis=1)))


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    catalog = harness.catalog
    keys = len(harness.key_names)
    rng = random.Random(SEED)

    block = descriptors(harness)
    latent = whiten(block)
    unit = latent / np.linalg.norm(latent, axis=1, keepdims=True)
    cosine = np.clip(unit @ unit.T, 0., 1.)
    permutation = np.random.default_rng(SEED + 3).permutation(keys)
    latent_scrambled = latent[permutation]

    seen_families = [family for family in sorted(harness.by_family)
                     if family not in HELD_OUT_FAMILIES]
    viable = [triple for triple in itertools.combinations(seen_families, FAMILIES_PER_WORLD)
              if harness.sample_world(triple, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)]
    held_triples = sorted(rng.sample(viable, HELD_OUT_TRIPLES))
    training_triples = [triple for triple in viable if triple not in held_triples]
    held_family_triples = [triple for triple in
                           itertools.combinations(sorted(harness.by_family), FAMILIES_PER_WORLD)
                           if set(triple) & set(HELD_OUT_FAMILIES)]

    def draw(triples, count):
        out = []
        while len(out) < count:
            world = harness.sample_world(triples[rng.randrange(len(triples))], rng,
                                         KEYS_PER_WORLD, MINIMUM_MEMBERS)
            if world is not None:
                out.append(world)
        return out

    training = draw(training_triples, TRAINING_WORLDS)
    observed_sets = [sorted({harness.key_index[key] for key in harness.observed_keys(
        rng.sample(world['members'], min(PRIOR_SOLVED, len(world['members']))))})
        for world in training]
    identity = affinity(observed_sets, keys)
    metric = fit_metric(latent, observed_sets, rng)
    metric_scrambled = fit_metric(latent_scrambled, observed_sets, rng)

    evaluation = {'seen_triple': draw(training_triples, EVAL_WORLDS),
                  'new_triple': draw(held_triples, EVAL_WORLDS),
                  'new_family': draw(held_family_triples, EVAL_WORLDS)}
    arms = [f'{name}:{k}' for k in ADAPT for name in ARMS]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}

    for split, worlds in evaluation.items():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            test, pool = members[:TEST_MECHANISMS], members[TEST_MECHANISMS:]
            ranks = {}
            for k in ADAPT:
                counts = harness.key_counts(pool[:k])
                present = list(np.flatnonzero(counts))
                direct = (counts > 0).astype(float)
                generalized = identity[present].max(axis=0) if present else np.zeros(keys)
                fitted = metric_scores(metric, latent, present)
                scrambled = metric_scores(metric_scrambled, latent_scrambled, present)
                raw = cosine[:, present].max(axis=1) if present else np.zeros(keys)
                scores = {'free_set': direct,
                          'free_cosine': np.maximum(direct, raw),
                          'meta_identity': np.maximum(direct, generalized),
                          'meta_metric': np.maximum(direct, fitted),
                          'meta_both': np.maximum(direct, np.maximum(generalized, fitted)),
                          'meta_metric_scrambled': np.maximum(direct, scrambled)}
                for name, score in scores.items():
                    ranks[f'{name}:{k}'] = ranks_of(
                        harness.order_from_key_scores(np.log(score + FLOOR)))
            for mechanism in test:
                view = harness.task_view(mechanism, rng)
                if view is None:
                    continue
                for arm in arms:
                    for budget in BUDGETS:
                        outcomes[split][arm][budget].append(
                            harness.solve(view, ranks[arm], budget, catalog.size))

    boot = np.random.default_rng(SEED + 11)
    result = {'scope': 'a fitted behavioural metric against an unfamiliar family',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'held_out_families': list(HELD_OUT_FAMILIES),
              'held_out_triples': [list(triple) for triple in held_triples],
              'metric_nonzero_dimensions': int((np.abs(metric.coef_[0]) > 1e-3).sum()),
              'seed': SEED, 'splits': {}}

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
        out = {'tasks': tasks, 'worlds': len(evaluation[split]), 'rate': rate}
        for name in ('meta_metric', 'meta_both', 'meta_identity', 'free_cosine'):
            out[f'{name}_minus_free_set'] = {
                str(k): {str(budget): paired(f'{name}:{k}', f'free_set:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        out['meta_metric_minus_scrambled'] = {
            str(k): {str(budget): paired(f'meta_metric:{k}', f'meta_metric_scrambled:{k}',
                                         budget) for budget in BUDGETS} for k in ADAPT}
        out['meta_metric_minus_free_cosine'] = {
            str(k): {str(budget): paired(f'meta_metric:{k}', f'free_cosine:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        result['splits'][split] = out

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for split in ('seen_triple', 'new_triple', 'new_family'):
        out = result['splits'][split]
        print('\n== {}: {} tasks, {} worlds'.format(split, out['tasks'], out['worlds']))
        print('arm'.ljust(26) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(26) + ''.join('{:9.3f}'.format(out['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        for key in ('meta_metric_minus_free_set', 'meta_metric_minus_scrambled',
                    'meta_both_minus_free_set'):
            print(key + ':')
            for k in ADAPT:
                row = out[key][str(k)]
                print('  k={:<3d}'.format(k) + ''.join(
                    '{:+6.0f}{:<14s}'.format(row[str(b)]['sum'],
                                             str([round(x) for x in row[str(b)]['interval']]))
                    for b in ('256', '1024', '4096', '65536')))
    print('\nmetric dimensions used: {}'.format(result['metric_nonzero_dimensions']))
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
