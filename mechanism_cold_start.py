"""A prior that works before the first solve.

The earned loop is limited by how fast correct atoms arrive, and the
cross-world prior cannot help it: +86 [-40, 222] at budget 1024
(`mechanism-lifelong-20260921.json`). The reason is structural rather than
statistical. That prior conditions on the atoms of mechanisms the agent has
already solved, and an agent that has solved nothing has nothing to condition
on, so for exactly the stretch that decides whether the loop ever starts it is
the no-experience ordering.

What the training worlds also know, and that prior never used, is which pairs
of atoms belong together in *any* world. That is unconditional: it is available
before the agent has seen a single task of the new world, and it cannot be
written as a score on each atom separately, so it needs a row-level ordering.

  static    never updates, no prior
  blind     keeps the atoms of whatever it submitted; the earned-loop champion
  warm      starts from the pair-plausibility ordering, then updates as blind
  warm_flat the same with pair plausibility replaced by each atom's own rate,
            which separates "these two atoms go together" from "this atom is
            common"
  warm_scrambled  pair plausibility with atom labels permuted
  revealed  told the true mechanism each time; the ceiling

Training worlds are drawn from seven atom families. Half the evaluation worlds
use only those, and half contain one of the two families no training world
held, so the prior is scored where it is in distribution and where it is not,
in the same run. Development evidence; nothing frozen.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test
from rsi.mechanism_worlds import Harness, ranks_of

OUT = ROOT / 'analysis/mechanism-cold-start-20260921.json'
SEED = 610101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
WORLDS = 16
STREAM = 100
KEYS_PER_WORLD = 14
FAMILIES_PER_WORLD = 3
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
BUDGETS = (256, 1024)
FLOOR = 1e-4
BOOT = 20000
ARMS = ('static', 'blind', 'warm', 'warm_flat', 'warm_scrambled', 'revealed')
CHECKPOINTS = (20, 50, 100)


def cooccurrence(observed_sets, keys):
    counts = np.zeros((keys, keys))
    for indices in observed_sets:
        indices = list(indices)
        block = np.zeros(keys)
        block[indices] = 1.
        counts[np.ix_(indices, range(keys))] += block
    return counts / max(len(observed_sets), 1)


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

    families = sorted(harness.by_family)
    seen_families = [family for family in families if family not in HELD_OUT_FAMILIES]
    training_triples = [triple for triple in
                        itertools.combinations(seen_families, FAMILIES_PER_WORLD)
                        if harness.sample_world(triple, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)]
    held_triples = [triple for triple in
                    itertools.combinations(families, FAMILIES_PER_WORLD)
                    if set(triple) & set(HELD_OUT_FAMILIES)
                    and harness.sample_world(triple, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)]

    def draw(triples, count):
        out = []
        while len(out) < count:
            world = harness.sample_world(triples[rng.randrange(len(triples))], rng,
                                         KEYS_PER_WORLD, MINIMUM_MEMBERS)
            if world is not None:
                out.append(world)
        return out

    groups = {'seen_families': draw(training_triples, WORLDS),
              'new_family': draw(held_triples, WORLDS)}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['members'][:STREAM]}

    training = draw(training_triples, TRAINING_WORLDS)
    observed_sets = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
        observed_sets.append(sorted({harness.key_index[key]
                                     for key in harness.observed_keys(solved)}))
    pair = cooccurrence(observed_sets, keys)
    rate = np.diag(pair).copy()
    permutation = np.random.default_rng(SEED + 5).permutation(keys)

    warm_rows = np.log(harness.pair_scores(pair) + FLOOR)
    flat_rows = harness.row_scores(np.log(rate + FLOOR))
    scrambled_rows = np.log(harness.pair_scores(pair[np.ix_(permutation, permutation)]) + FLOOR)
    prior_rows = {'warm': warm_rows, 'warm_flat': flat_rows,
                  'warm_scrambled': scrambled_rows}
    static_order = ranks_of(harness.order_from_row_scores(np.zeros(catalog.size)))
    start = {arm: (static_order if arm not in prior_rows else
                   ranks_of(harness.order_from_row_scores(prior_rows[arm])))
             for arm in ARMS}

    curves = {group: {budget: {arm: np.zeros((WORLDS, STREAM)) for arm in ARMS}
                      for budget in BUDGETS} for group in groups}

    for group, worlds in groups.items():
        for world_number, world in enumerate(worlds):
            stream = list(world['members'])
            rng.shuffle(stream)
            views = []
            for mechanism in stream[:STREAM]:
                task = make_task(catalog, mechanism, rng)
                consistent = np.flatnonzero(vector_test(harness.packed, task['visible_pos'],
                                                        task['visible_neg']))
                good = vector_test(harness.packed, task['hidden_pos'],
                                   task['hidden_neg'])[consistent]
                views.append({'mechanism': mechanism, 'consistent': consistent,
                              'good': good,
                              'select': np.lexsort((harness.complexity[consistent],
                                                    harness.sizes[consistent]))})
            for budget in BUDGETS:
                for arm in ARMS:
                    known = set()
                    position = start[arm]
                    base = prior_rows.get(arm)
                    for step, view in enumerate(views):
                        ranked = position[view['consistent']]
                        pick = -1
                        for candidate in view['select']:
                            if ranked[candidate] < budget:
                                pick = candidate
                                break
                        hit = 0 if pick < 0 else int(view['good'][pick])
                        curves[group][budget][arm][world_number, step] = hit
                        learned = None
                        if arm in ('blind', 'warm', 'warm_flat', 'warm_scrambled') \
                                and pick >= 0:
                            learned = int(view['consistent'][pick])
                        elif arm == 'revealed':
                            learned = view['mechanism']
                        if learned is None:
                            continue
                        fresh = {harness.key_index[key]
                                 for key in catalog.keys(learned)} - known
                        if not fresh:
                            continue
                        known |= fresh
                        score = np.zeros(keys)
                        score[sorted(known)] = 1.
                        rows = harness.row_scores(np.log(score + FLOOR))
                        if base is not None:
                            rows = rows + base
                        position = ranks_of(harness.order_from_row_scores(rows))

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, WORLDS, (BOOT, WORLDS))
    result = {'scope': 'an unconditional cross-world prior for the earned loop',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'held_out_families': list(HELD_OUT_FAMILIES),
              'worlds': WORLDS, 'stream': STREAM, 'seed': SEED, 'groups': {}}

    for group in groups:
        block = {}
        for budget in BUDGETS:
            totals = {arm: curves[group][budget][arm].sum(axis=1) for arm in ARMS}
            entry = {'solved': {arm: float(totals[arm].mean()) for arm in ARMS},
                     'first_twenty_vs_last_twenty': {arm: [
                         float(curves[group][budget][arm][:, :20].mean()),
                         float(curves[group][budget][arm][:, -20:].mean())] for arm in ARMS},
                     'cumulative': {arm: {str(point): float(
                         curves[group][budget][arm][:, :point].sum(axis=1).mean())
                         for point in CHECKPOINTS} for arm in ARMS}}
            for left, right in (('warm', 'blind'), ('warm', 'warm_flat'),
                                ('warm', 'warm_scrambled'), ('blind', 'static')):
                difference = totals[left] - totals[right]
                sums = difference[draws].sum(axis=1)
                entry[f'{left}_minus_{right}'] = {
                    'sum': float(difference.sum()),
                    'interval': [float(np.percentile(sums, 2.5)),
                                 float(np.percentile(sums, 97.5))]}
            block[str(budget)] = entry
        result['groups'][group] = block

    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    for group in groups:
        for budget in BUDGETS:
            entry = result['groups'][group][str(budget)]
            print('\n== {} budget {}'.format(group, budget))
            print('arm'.ljust(18) + 'solved'.rjust(9) + 'first20'.rjust(10)
                  + 'last20'.rjust(9) + ''.join('cum@{}'.format(p).rjust(9)
                                                for p in CHECKPOINTS))
            for arm in ARMS:
                first, last = entry['first_twenty_vs_last_twenty'][arm]
                print(arm.ljust(18) + '{:9.1f}{:10.3f}{:9.3f}'.format(
                    entry['solved'][arm], first, last)
                    + ''.join('{:9.1f}'.format(entry['cumulative'][arm][str(p)])
                              for p in CHECKPOINTS))
            for key in ('warm_minus_blind', 'warm_minus_warm_flat',
                        'warm_minus_warm_scrambled'):
                row = entry[key]
                print('  {}: {:+.0f} {}'.format(key, row['sum'],
                                                [round(x) for x in row['interval']]))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
