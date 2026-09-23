"""Can a prior reach a mechanism family that no training world contained?

Measured against the strongest experience-free rule, an acquired prior over
atom *identities* transfers to a world whose family combination is new
(+55 tasks of 640 at one solved mechanism and a budget of 256, controls at
baseline) and does not transfer to a world containing a family no training
world held: positive at tight budgets, negative at loose ones
(`mechanism-meta-transfer-20260921.json`). That is the same boundary the
verifier claim hit when it was finally asked for a mechanism holdout, and the
reason is structural. An identity affinity has no entry for an atom it has
never seen, so nothing it learned can be about one.

The repair tested here is to state the prior over something defined for atoms
that were never seen. Each atom is described by the magnitude spectrum of its
truth mask, Fourier and Walsh, which exists for every predicate in the catalog
and is invariant to which residue of a modulus an atom selects, so atoms of one
family look alike without anything naming the family.

Whether that is *growth* depends on a comparison the identity arm never had to
face, and it is included from the start:

  free_set        atoms of the k solved mechanisms, treated as a set
  free_spectral   atoms resembling the k solved ones, with no training worlds
                  used at all: a free procedure, and the one that decides
                  whether experience is doing any work here
  meta_identity   affinity over atom identities, estimated from 400 worlds
  meta_spectral   resemblance calibrated on those worlds
  meta_spectral_scrambled   the descriptors permuted across atoms

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
from rsi.mechanism_space import ALPHABET_SIZE, world_members
from rsi.mechanism_worlds import Harness, affinity, ranks_of

OUT = ROOT / 'analysis/mechanism-family-transfer-20260921.json'
SEED = 604101
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
ARMS = ('free_set', 'free_spectral', 'meta_identity', 'meta_spectral',
        'meta_spectral_scrambled')


def fwht(rows):
    rows = rows.astype(np.float64).copy()
    width = rows.shape[-1]
    step = 1
    while step < width:
        for start in range(0, width, step * 2):
            left = rows[:, start:start + step].copy()
            right = rows[:, start + step:start + 2 * step].copy()
            rows[:, start:start + step] = left + right
            rows[:, start + step:start + 2 * step] = left - right
        step *= 2
    return rows


def descriptors(harness):
    """One unit vector per atom, from the magnitude spectrum of its mask.

    Magnitudes, not coefficients: the Fourier magnitude of a mask is unchanged
    by rotating the alphabet, so the residues of one modulus map to the same
    description without any of them having been seen. That is the property the
    identity affinity lacks.
    """
    from rsi.mechanism_space import mask_of
    rows = np.zeros((len(harness.key_names), ALPHABET_SIZE))
    lookup = {atom[0]: atom[2] for atom in harness.catalog.atoms}
    for index, key in enumerate(harness.key_names):
        mask = mask_of(lookup[key])
        bits = np.array([(mask >> bit) & 1 for bit in range(ALPHABET_SIZE)], float)
        rows[index] = bits * 2 - 1
    fourier = np.abs(np.fft.rfft(rows, axis=1))
    walsh = np.abs(fwht(rows))
    block = np.concatenate([fourier / np.linalg.norm(fourier, axis=1, keepdims=True),
                            walsh / np.linalg.norm(walsh, axis=1, keepdims=True)], axis=1)
    return block / np.linalg.norm(block, axis=1, keepdims=True)


def similarity_scores(similarity, observed):
    if not len(observed):
        return np.zeros(similarity.shape[0])
    return similarity[:, observed].max(axis=1)


def calibrate(similarity, observed_sets, rng, samples=60):
    """P(atom is in a world | it resembles the atoms already solved there).

    Fitted on the training worlds only, by showing the estimator the same view
    an arm gets: a few solved atoms, and the question of what else is present.
    """
    features, labels = [], []
    size = similarity.shape[0]
    for indices in observed_sets:
        indices = list(indices)
        if len(indices) < 2:
            continue
        for k in ADAPT:
            seen = rng.sample(indices, min(k, len(indices)))
            scores = similarity_scores(similarity, seen)
            positives = [index for index in indices if index not in seen]
            negatives = rng.sample(range(size), samples)
            for index in positives + negatives:
                features.append([scores[index], np.log(len(seen) + 1.)])
                labels.append(int(index in indices))
    model = LogisticRegression(max_iter=1000)
    model.fit(np.array(features), np.array(labels))
    return model


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
    similarity = np.clip(block @ block.T, 0., 1.)
    permutation = np.random.default_rng(SEED + 3).permutation(keys)
    scrambled = similarity[np.ix_(permutation, permutation)]

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
    spectral_model = calibrate(similarity, observed_sets, rng)
    scrambled_model = calibrate(scrambled, observed_sets, rng)

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
                raw = similarity_scores(similarity, present)
                scrambled_raw = similarity_scores(scrambled, present)
                page = np.full(len(raw), np.log(len(present) + 1.))
                probability = spectral_model.predict_proba(
                    np.column_stack([raw, page]))[:, 1]
                scrambled_probability = scrambled_model.predict_proba(
                    np.column_stack([scrambled_raw, page]))[:, 1]
                generalized = identity[present].max(axis=0) if present else np.zeros(keys)
                scores = {
                    'free_set': direct,
                    'free_spectral': np.maximum(direct, raw),
                    'meta_identity': np.maximum(direct, generalized),
                    'meta_spectral': np.maximum(direct, probability),
                    'meta_spectral_scrambled': np.maximum(direct, scrambled_probability),
                }
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
    result = {'scope': 'transfer to an unfamiliar family through a behavioural description',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'held_out_families': list(HELD_OUT_FAMILIES),
              'held_out_triples': [list(triple) for triple in held_triples],
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
        block_out = {'tasks': tasks, 'worlds': len(evaluation[split]), 'rate': rate}
        for name in ('meta_spectral', 'meta_identity', 'free_spectral'):
            block_out[f'{name}_minus_free_set'] = {
                str(k): {str(budget): paired(f'{name}:{k}', f'free_set:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        block_out['meta_spectral_minus_free_spectral'] = {
            str(k): {str(budget): paired(f'meta_spectral:{k}', f'free_spectral:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        block_out['meta_spectral_minus_scrambled'] = {
            str(k): {str(budget): paired(f'meta_spectral:{k}',
                                         f'meta_spectral_scrambled:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        result['splits'][split] = block_out

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for split in ('seen_triple', 'new_triple', 'new_family'):
        out = result['splits'][split]
        print('\n== {}: {} tasks, {} worlds'.format(split, out['tasks'], out['worlds']))
        print('arm'.ljust(28) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(28) + ''.join('{:9.3f}'.format(out['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        for name in ('free_spectral', 'meta_identity', 'meta_spectral'):
            print('{} minus free_set:'.format(name))
            for k in ADAPT:
                row = out[f'{name}_minus_free_set'][str(k)]
                print('  k={:<3d}'.format(k) + ''.join(
                    '{:+9.0f}'.format(row[str(b)]['sum']) for b in BUDGETS))
        print('meta_spectral minus free_spectral:')
        for k in ADAPT:
            row = out['meta_spectral_minus_free_spectral'][str(k)]
            print('  k={:<3d}'.format(k) + ''.join(
                '{:+9.0f}'.format(row[str(b)]['sum']) for b in BUDGETS))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
