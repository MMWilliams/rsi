"""Why the acquired prior collapsed on an unfamiliar family, and whether it has
to.

`mechanism-meta-growth-20260921.json` found both halves of the same result.
Experience of four hundred worlds made a world with an unseen combination of
families far quicker to learn: at one solved mechanism and a scan budget of
1024, 0.535 against 0.135 for the same rule without that experience, with the
no-structure and scrambled controls at baseline. On a world built from a family
no training world contained, the same arm fell to 0.077 while the experience
free rule reached 0.056 at k=1 and 0.706 at k=16. Held out one level further,
the acquired prior was worse than having none.

The cause is visible in the estimator rather than in the environment. The
affinity of an atom never seen in training is zero in every row and column, and
the arm scores a catalog entry by its atoms' affinities, so an atom the agent
has *directly observed solving a task in this very world* is assigned zero
probability. Prior experience was allowed to overrule present evidence.

Two repairs are tested, and they are different kinds of claim:

  direct   the posterior over atoms is the maximum of what this world has shown
           and what other worlds suggest, over a uniform floor. Evidence from
           the world at hand can no longer be overruled.
  hedge    a fixed share of the scan budget is spent on the experience-free
           adaptation order regardless of what the prior believes, which bounds
           the loss on any world at the cost of that share.

The question for each is whether it keeps the gain where the prior was right
and removes the loss where it was wrong. Development evidence on opened draws;
nothing is frozen here.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_worlds import Harness, affinity, interleave, ranks_of

OUT = ROOT / 'analysis/mechanism-meta-support-20260921.json'
SEED = 602601
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
EVAL_WORLDS = 12
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
        from rsi.mechanism_space import world_members
        members = world_members(catalog, harness.by_key, chosen)
        if len(members) >= MINIMUM_MEMBERS:
            uniform_training.append({'keys': tuple(sorted(chosen)), 'members': members})

    def observed(worlds):
        out = []
        for world in worlds:
            solved = rng.sample(world['members'], min(PRIOR_SOLVED, len(world['members'])))
            out.append(sorted({harness.key_index[key]
                               for key in harness.observed_keys(solved)}))
        return out

    matrices = {'meta': affinity(observed(training), keys),
                'meta_uniform': affinity(observed(uniform_training), keys)}
    permutation = np.random.default_rng(SEED + 5).permutation(keys)
    matrices['meta_scrambled'] = matrices['meta'][np.ix_(permutation, permutation)]

    evaluation = {'seen_triple': draw(training_triples, EVAL_WORLDS),
                  'new_triple': draw(held_triples, EVAL_WORLDS),
                  'new_family': draw(held_family_triples, EVAL_WORLDS)}

    free_static = {'complexity': ranks_of(harness.base.copy()),
                   'density': ranks_of(np.lexsort((harness.base,
                                                   np.abs(harness.density - .5))))}
    adaptive = ['free', 'meta', 'meta_direct', 'meta_hedged', 'meta_uniform',
                'meta_direct_uniform', 'meta_scrambled']
    arms = list(free_static) + [f'{name}:{k}' for k in ADAPT for name in adaptive]
    outcomes = {split: {arm: {budget: [] for budget in BUDGETS} for arm in arms}
                for split in evaluation}
    members_seen = {split: [] for split in evaluation}

    for split, worlds in evaluation.items():
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            test, pool = members[:TEST_MECHANISMS], members[TEST_MECHANISMS:]
            members_seen[split].append(len(members))
            ranks = dict(free_static)
            for k in ADAPT:
                counts = harness.key_counts(pool[:k])
                present = np.flatnonzero(counts)
                free_order = harness.order_from_key_scores(np.log1p(counts))
                ranks[f'free:{k}'] = ranks_of(free_order)
                direct = (counts > 0).astype(float)
                for name, matrix in matrices.items():
                    generalized = matrix[present].mean(axis=0) if len(present) else \
                        np.zeros(keys)
                    ranks[f'{name}:{k}'] = ranks_of(
                        harness.order_from_key_scores(np.log(generalized + 1e-9)))
                    if name in ('meta', 'meta_uniform'):
                        merged = np.maximum(direct, generalized) + FLOOR
                        order = harness.order_from_key_scores(np.log(merged))
                        label = 'meta_direct' if name == 'meta' else 'meta_direct_uniform'
                        ranks[f'{label}:{k}'] = ranks_of(order)
                        if name == 'meta':
                            ranks[f'meta_hedged:{k}'] = ranks_of(
                                interleave(order, free_order, HEDGE))
            for mechanism in test:
                view = harness.task_view(mechanism, rng)
                if view is None:
                    continue
                for arm in arms:
                    for budget in BUDGETS:
                        outcomes[split][arm][budget].append(
                            harness.solve(view, ranks[arm], budget, catalog.size))

    boot = np.random.default_rng(SEED + 7)
    result = {'scope': 'repairing an acquired prior that overruled present evidence',
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
            return {'sum': float(difference.sum()),
                    'interval': [float(np.percentile(sums, 2.5)),
                                 float(np.percentile(sums, 97.5))]}

        rate = {arm: {str(budget): float(np.mean(outcomes[split][arm][budget]))
                      for budget in BUDGETS} for arm in arms}
        block = {'tasks': tasks, 'worlds': len(evaluation[split]),
                 'world_members_mean': float(np.mean(members_seen[split])), 'rate': rate}
        for name in ('meta', 'meta_direct', 'meta_hedged'):
            block[f'{name}_minus_free'] = {
                str(k): {str(budget): paired(f'{name}:{k}', f'free:{k}', budget)
                         for budget in BUDGETS} for k in ADAPT}
        block['meta_direct_minus_uniform'] = {
            str(k): {str(budget): paired(f'meta_direct:{k}', f'meta_direct_uniform:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        block['meta_direct_minus_scrambled'] = {
            str(k): {str(budget): paired(f'meta_direct:{k}', f'meta_scrambled:{k}', budget)
                     for budget in BUDGETS} for k in ADAPT}
        result['splits'][split] = block

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for split in ('seen_triple', 'new_triple', 'new_family'):
        block = result['splits'][split]
        print('\n== {}: {} tasks, {} worlds, {:.0f} members'.format(
            split, block['tasks'], block['worlds'], block['world_members_mean']))
        print('arm'.ljust(22) + ''.join(str(budget).rjust(9) for budget in BUDGETS))
        for arm in arms:
            print(arm.ljust(22) + ''.join('{:9.3f}'.format(block['rate'][arm][str(budget)])
                                          for budget in BUDGETS))
        for name in ('meta', 'meta_direct', 'meta_hedged'):
            print('{} minus free:'.format(name))
            for k in ADAPT:
                row = block[f'{name}_minus_free'][str(k)]
                print('  k={:<3d}'.format(k) + ''.join('{:+9.0f}'.format(row[str(b)]['sum'])
                                                       for b in BUDGETS))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
