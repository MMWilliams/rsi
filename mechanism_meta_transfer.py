"""What experience of other worlds is worth, against the best rule that has none.

Three measurements led here. Experience of a world's own mechanisms lifts the
solve rate at a scan budget of 256 from 0.008 to 0.803, and gains nothing when
the same rule is fed another world's mechanisms. Experience of four hundred
*other* worlds then lifts a world with an unfamiliar combination of atom
families from 0.135 to 0.535 at one solved mechanism, with the no-structure and
label-scrambled controls at baseline. On a world built from a family no
training world contained, the same prior fell below having no prior at all,
because an atom absent from training was assigned zero probability even when
the agent had just watched it solve a task in this very world.

Repairing that (`mechanism-meta-support-20260921.json`) recovered the split,
and recovered too much: part of the recovery was not transfer. The free rule
scored an atom by how *often* it appeared in the solved mechanisms, while the
structure being learned is a set, not a distribution. Flattening that is
available to any arm without any experience at all.

This run states the comparison properly. The free adaptation rules are both
forms, and every claim below is against the better of them at the same budget
and the same number of solved mechanisms:

  free_count  atoms weighted by how often they appear in the k solved mechanisms
  free_set    atoms treated as a set, the stronger of the two and the one every
              transfer claim here is measured against
  meta        the set rule, raised by what other worlds say about which atoms
              travel together, never lowered below what this world has shown
  meta_hedged the same, reserving a quarter of the budget for free_set

  meta_uniform / meta_scrambled   the same estimator fitted on worlds with no
              structure, and with its atom labels permuted

Splits, from the mildest holdout to the one that ends claims: a world whose
family combination was trained on, one whose families were each trained on but
never together, and one containing a family no training world held.
Development evidence on opened draws; nothing is frozen here.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import world_members
from rsi.mechanism_worlds import Harness, affinity, interleave, ranks_of

OUT = ROOT / 'analysis/mechanism-meta-transfer-20260921.json'
SEED = 603101
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
HEDGE = 0.25
BOOT = 20000
FREE = ('free_count', 'free_set')
META = ('meta', 'meta_hedged', 'meta_uniform', 'meta_scrambled')


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    catalog = harness.catalog
    keys = len(harness.key_names)
    rng = random.Random(SEED)

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
    uniform_training = []
    while len(uniform_training) < TRAINING_WORLDS:
        chosen = rng.sample(harness.key_names, KEYS_PER_WORLD)
        members = world_members(catalog, harness.by_key, chosen)
        if len(members) >= MINIMUM_MEMBERS:
            uniform_training.append({'keys': tuple(sorted(chosen)), 'members': members})

    def observed(worlds):
        return [sorted({harness.key_index[key] for key in harness.observed_keys(
            rng.sample(world['members'], min(PRIOR_SOLVED, len(world['members']))))})
            for world in worlds]

    structured = affinity(observed(training), keys)
    matrices = {'meta': structured, 'meta_uniform': affinity(observed(uniform_training), keys)}
    permutation = np.random.default_rng(SEED + 5).permutation(keys)
    matrices['meta_scrambled'] = structured[np.ix_(permutation, permutation)]

    evaluation = {'seen_triple': draw(training_triples, EVAL_WORLDS),
                  'new_triple': draw(held_triples, EVAL_WORLDS),
                  'new_family': draw(held_family_triples, EVAL_WORLDS)}

    static = {'complexity': ranks_of(harness.base.copy()),
              'density': ranks_of(np.lexsort((harness.base, np.abs(harness.density - .5))))}
    arms = list(static) + [f'{name}:{k}' for k in ADAPT for name in FREE + META]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}
    members_seen = {split: [] for split in evaluation}

    for split, worlds in evaluation.items():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            test, pool = members[:TEST_MECHANISMS], members[TEST_MECHANISMS:]
            members_seen[split].append(len(members))
            ranks = dict(static)
            for k in ADAPT:
                counts = harness.key_counts(pool[:k])
                present = np.flatnonzero(counts)
                direct = (counts > 0).astype(float)
                set_order = harness.order_from_key_scores(np.log(direct + FLOOR))
                ranks[f'free_count:{k}'] = ranks_of(
                    harness.order_from_key_scores(np.log1p(counts)))
                ranks[f'free_set:{k}'] = ranks_of(set_order)
                for name, matrix in matrices.items():
                    generalized = matrix[present].mean(axis=0) if len(present) else \
                        np.zeros(keys)
                    merged = np.maximum(direct, generalized) + FLOOR
                    order = harness.order_from_key_scores(np.log(merged))
                    ranks[f'{name}:{k}'] = ranks_of(order)
                    if name == 'meta':
                        ranks[f'meta_hedged:{k}'] = ranks_of(
                            interleave(order, set_order, HEDGE))
            for mechanism in test:
                view = harness.task_view(mechanism, rng)
                if view is None:
                    continue
                for arm in arms:
                    for budget in BUDGETS:
                        outcomes[split][arm][budget].append(
                            harness.solve(view, ranks[arm], budget, catalog.size))

    boot = np.random.default_rng(SEED + 7)
    result = {'scope': 'transfer across worlds against the best experience-free rule',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'prior_solved_per_world': PRIOR_SOLVED,
              'held_out_families': list(HELD_OUT_FAMILIES),
              'held_out_triples': [list(triple) for triple in held_triples],
              'floor': FLOOR, 'hedge_share': HEDGE, 'seed': SEED, 'splits': {}}

    for split in evaluation:
        tasks = len(outcomes[split]['complexity'][BUDGETS[0]])
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
        best_free = {}
        for k in ADAPT:
            for budget in BUDGETS:
                best_free[(k, budget)] = max(
                    FREE, key=lambda name: rate[f'{name}:{k}'][str(budget)])
        block = {'tasks': tasks, 'worlds': len(evaluation[split]),
                 'world_members_mean': float(np.mean(members_seen[split])), 'rate': rate,
                 'best_free': {str(k): {str(budget): best_free[(k, budget)]
                                        for budget in BUDGETS} for k in ADAPT}}
        for name in ('meta', 'meta_hedged'):
            block[f'{name}_minus_best_free'] = {
                str(k): {str(budget): paired(f'{name}:{k}',
                                             f'{best_free[(k, budget)]}:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        block['meta_minus_uniform'] = {
            str(k): {str(budget): paired(f'meta:{k}', f'meta_uniform:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        block['meta_minus_scrambled'] = {
            str(k): {str(budget): paired(f'meta:{k}', f'meta_scrambled:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        # How many solved mechanisms the free rule needs to reach what the
        # prior reaches from one, which is the sample cost experience removes.
        equivalence = {}
        for budget in BUDGETS:
            row = {}
            for k in ADAPT:
                target = rate[f'meta:{k}'][str(budget)]
                matched = None
                for candidate in ADAPT:
                    if max(rate[f'{name}:{candidate}'][str(budget)] for name in FREE) >= target:
                        matched = candidate
                        break
                row[str(k)] = matched
            equivalence[str(budget)] = row
        block['free_solved_mechanisms_to_match_meta'] = equivalence
        result['splits'][split] = block

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for split in ('seen_triple', 'new_triple', 'new_family'):
        block = result['splits'][split]
        print('\n== {}: {} tasks, {} worlds, {:.0f} members'.format(
            split, block['tasks'], block['worlds'], block['world_members_mean']))
        print('arm'.ljust(20) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(20) + ''.join('{:9.3f}'.format(block['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        for name in ('meta', 'meta_hedged'):
            print('{} minus best free rule:'.format(name))
            for k in ADAPT:
                row = block[f'{name}_minus_best_free'][str(k)]
                print('  k={:<3d}'.format(k) + ''.join(
                    '{:+9.0f}'.format(row[str(b)]['sum']) for b in BUDGETS))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
