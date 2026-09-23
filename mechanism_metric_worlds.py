"""Worlds with a latent structure that an unseen atom can be measured against.

Four attempts to reach a world built from a family no training world contained
have now failed, and the fifth, `mechanism-atom-clustering-20260921.json`,
explains the other four. In the worlds used so far a family is the *name of an
arithmetic operation*: `mod:2:0` and `mod:16:7` share a label and share nothing
observable, while `threshold` is recovered perfectly and `xormod` scatters over
three clusters. Unsupervised clustering of atom behaviour recovers the family
labelling at adjusted Rand 0.144. So the family holdout asked for generalization
across a boundary that nothing computable on an atom can see, and no
representation defined on behaviour could ever have crossed it. That is a fact
about how those worlds were built, not about transfer.

This builds worlds whose latent structure *is* behavioural, so the question
becomes answerable either way. A fixed weight vector over descriptor
dimensions, sparse and random, is drawn once and shown to nobody. A world is a
centre atom and the fourteen atoms nearest it under that weighting. Every atom
in the catalog has a descriptor, including atoms no training world contained,
so a prior stated over the weighting applies to them.

  free_set       the solved atoms, treated as a set
  free_cosine    unweighted descriptor proximity to them, the free procedure
                 that needs no training worlds and is the rule to beat
  meta_metric    a diagonal metric fitted to co-membership on training worlds
  meta_scrambled the same fitted metric with its dimensions permuted
  oracle_metric  the true weighting. Not deployable; it is the headroom, and
                 reading it is the P2 screen this run carries inside it

Splits: worlds centred on atoms of the seven families the training worlds were
centred on, and worlds centred on the two they were not. Development evidence;
nothing frozen.
"""
from __future__ import annotations

import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import DENSITY, make_task, vector_test, world_members
from rsi.mechanism_worlds import Harness, ranks_of
from mechanism_atom_clustering import descriptors
from mechanism_metric_transfer import fit_metric

OUT = ROOT / 'analysis/mechanism-metric-worlds-20260921.json'
SEED = 614101
WEIGHT_SEED = 777001
ACTIVE_DIMENSIONS = 40
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 16
TEST_MECHANISMS = 40
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 110
HELD_OUT_FAMILIES = ('popcount', 'xormod')
ADAPT = (1, 2, 4, 8)
BUDGETS = (256, 1024, 4096, 16384, None)
FLOOR = 1e-4
BOOT = 20000
ARMS = ('free_set', 'free_cosine', 'meta_metric', 'meta_scrambled', 'oracle_metric')


def weighted_distance(latent, weights, centre):
    difference = latent - latent[centre]
    return ((difference ** 2) * weights).sum(axis=1)


def proximity(latent, weights, observed):
    """Highest weighted closeness to any solved atom, as a score in (0, 1]."""
    if not len(observed):
        return np.zeros(latent.shape[0])
    best = None
    for index in observed:
        distance = weighted_distance(latent, weights, index)
        best = distance if best is None else np.minimum(best, distance)
    return np.exp(-best / max(float(np.median(best)), 1e-9))


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

    latent = descriptors(harness)
    dimensions = latent.shape[1]
    weight_rng = np.random.default_rng(WEIGHT_SEED)
    true_weights = np.zeros(dimensions)
    active = weight_rng.choice(dimensions, ACTIVE_DIMENSIONS, replace=False)
    true_weights[active] = weight_rng.uniform(.5, 4., ACTIVE_DIMENSIONS)
    flat_weights = np.ones(dimensions)

    families = np.array([key.split(':')[0] for key in harness.key_names])
    seen_centres = [index for index in range(keys)
                    if families[index] not in HELD_OUT_FAMILIES]
    held_centres = [index for index in range(keys)
                    if families[index] in HELD_OUT_FAMILIES]

    def world_from(centre):
        distance = weighted_distance(latent, true_weights, centre)
        chosen = [harness.key_names[index]
                  for index in np.argsort(distance)[:KEYS_PER_WORLD]]
        members = world_members(catalog, harness.by_key, chosen)
        members = [index for index in members
                   if DENSITY[0] <= harness.density[index] <= DENSITY[1]]
        if len(members) < MINIMUM_MEMBERS:
            return None
        return {'centre': centre, 'keys': chosen, 'members': members}

    def draw(centres, count):
        out, attempts = [], 0
        while len(out) < count and attempts < count * 60:
            attempts += 1
            world = world_from(centres[rng.randrange(len(centres))])
            if world is not None:
                out.append(world)
        if len(out) < count:
            raise RuntimeError(f'only {len(out)} of {count} worlds met the size floor')
        return out

    evaluation = {'seen_centre': draw(seen_centres, EVAL_WORLDS),
                  'new_family_centre': draw(held_centres, EVAL_WORLDS)}
    for worlds in evaluation.values():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            world['test'] = members[:TEST_MECHANISMS]
            world['pool'] = members[TEST_MECHANISMS:]
    reserved = {index for worlds in evaluation.values() for world in worlds
                for index in world['test']}

    training = draw(seen_centres, TRAINING_WORLDS)
    observed_sets = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
        observed_sets.append(sorted({harness.key_index[key]
                                     for key in harness.observed_keys(solved)}))
    model = fit_metric(latent, observed_sets, rng)
    fitted_weights = np.maximum(model.coef_[0], 0.)
    scrambled_weights = fitted_weights[np.random.default_rng(SEED + 5).permutation(dimensions)]
    weights = {'free_cosine': flat_weights, 'meta_metric': fitted_weights,
               'meta_scrambled': scrambled_weights, 'oracle_metric': true_weights}
    overlap = float(np.corrcoef(fitted_weights, true_weights)[0, 1])

    arms = [f'{name}:{k}' for k in ADAPT for name in ARMS]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}
    members_seen = {split: [] for split in evaluation}

    for split, worlds in evaluation.items():
        for world in worlds:
            members_seen[split].append(len(world['members']))
            ranks = {}
            for k in ADAPT:
                counts = harness.key_counts(world['pool'][:k])
                present = list(np.flatnonzero(counts))
                direct = (counts > 0).astype(float)
                for name in ARMS:
                    if name == 'free_set':
                        score = direct
                    else:
                        score = np.maximum(direct, proximity(latent, weights[name], present))
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
    result = {'scope': 'worlds defined by a hidden metric over atom behaviour',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'descriptor_dimensions': dimensions, 'active_dimensions': ACTIVE_DIMENSIONS,
              'training_worlds': len(training), 'held_out_families': list(HELD_OUT_FAMILIES),
              'fitted_true_weight_correlation': overlap, 'seed': SEED, 'splits': {}}

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
        entry = {'tasks': tasks, 'worlds': len(evaluation[split]),
                 'world_members_mean': float(np.mean(members_seen[split])), 'rate': rate}
        for left, right in (('oracle_metric', 'free_cosine'), ('meta_metric', 'free_cosine'),
                            ('meta_metric', 'free_set'), ('meta_metric', 'meta_scrambled'),
                            ('free_cosine', 'free_set')):
            entry[f'{left}_minus_{right}'] = {
                str(k): {str(budget): paired(f'{left}:{k}', f'{right}:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        result['splits'][split] = entry

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    print('fitted-to-true weight correlation {:.3f}'.format(overlap))
    for split in evaluation:
        entry = result['splits'][split]
        print('\n== {}: {} tasks, {} worlds, {:.0f} members'.format(
            split, entry['tasks'], entry['worlds'], entry['world_members_mean']))
        print('arm'.ljust(22) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(22) + ''.join('{:9.3f}'.format(entry['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        for key in ('oracle_metric_minus_free_cosine', 'meta_metric_minus_free_cosine',
                    'meta_metric_minus_meta_scrambled'):
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
