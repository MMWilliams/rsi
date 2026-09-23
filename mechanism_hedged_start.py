"""A cold-start prior that is never worse than not having one.

The unconditional cross-world prior is worth +314 and +621 tasks to the earned
loop on families the training worlds contained, and on a family they did not it
is worse than the same prior with its atom labels permuted, -147 [-240, -60]
at budget 1024 (`mechanism-cold-start-20260921.json`). Every acquired prior in
this line of work has failed in exactly that place and no other, so the fix is
worth building once rather than rediscovering.

Two repairs, and they differ in what they need to be true:

  hedge    reserve a fixed share of the scan budget for the order the agent
           would use with no prior at all. It needs nothing to be detectable:
           the loss is bounded by the reserved share whatever the prior
           believes, and the gain is scaled by the rest.
  detect   switch the prior off once the agent's own solved atoms say it is out
           of support. The statistic is the fraction of them that appear in no
           training world, which is an unbiased estimate of the share of this
           world the prior cannot rank at all, and the threshold is the share
           the hedge would otherwise have reserved. It needs the agent to have
           solved something, so it cannot protect the first few tasks, and it
           recovers the whole gain where it is in support rather than a
           fraction of it.

Both are run against the unhedged prior and against the earned loop with no
prior, on worlds whose families the training worlds held and on worlds whose
families they did not. Development evidence; nothing frozen.
"""
from __future__ import annotations

import itertools
import random
import time

import numpy as np
import psutil

from rsi.common import ROOT, write_json
from rsi.mechanism_space import make_task, vector_test
from rsi.mechanism_worlds import Harness, interleave, ranks_of

OUT = ROOT / 'analysis/mechanism-hedged-start-20260921.json'
SEED = 611101
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
UNSEEN_LIMIT = .25
BOOT = 20000
ARMS = ('blind', 'warm', 'warm_hedge25', 'warm_hedge50', 'warm_detect', 'revealed')
CHECKPOINTS = (20, 50, 100)
SHARES = {'warm_hedge25': .25, 'warm_hedge50': .5}


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
    held_triples = [triple for triple in itertools.combinations(families, FAMILIES_PER_WORLD)
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

    groups = {}
    for name, triples in (('seen_families', training_triples), ('new_family', held_triples)):
        worlds = draw(triples, WORLDS)
        for world in worlds:
            members = list(world['members'])
            rng.shuffle(members)
            world['stream'] = members[:STREAM]
        groups[name] = worlds
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}

    training = draw(training_triples, TRAINING_WORLDS)
    observed_sets = []
    for world in training:
        allowed = [index for index in world['members'] if index not in reserved]
        solved = rng.sample(allowed, min(PRIOR_SOLVED, len(allowed)))
        observed_sets.append(sorted({harness.key_index[key]
                                     for key in harness.observed_keys(solved)}))
    pair = cooccurrence(observed_sets, keys)
    appearance = np.diag(pair).copy()
    prior_rows = np.log(harness.pair_scores(pair) + FLOOR)

    neutral = np.zeros(catalog.size)
    curves = {group: {budget: {arm: np.zeros((WORLDS, STREAM)) for arm in ARMS}
                      for budget in BUDGETS} for group in groups}
    fallbacks = {group: {budget: 0 for budget in BUDGETS} for group in groups}

    def order_for(arm, known_rows, in_support):
        """The scan order an arm uses given its current evidence."""
        if arm in ('blind', 'revealed'):
            return harness.order_from_row_scores(known_rows)
        if arm == 'warm_detect' and not in_support:
            return harness.order_from_row_scores(known_rows)
        prior_order = harness.order_from_row_scores(known_rows + prior_rows)
        share = SHARES.get(arm)
        if share is None:
            return prior_order
        return interleave(prior_order, harness.order_from_row_scores(known_rows), share)

    for group, worlds in groups.items():
        for world_number, world in enumerate(worlds):
            views = []
            for mechanism in world['stream']:
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
                    known_rows = neutral
                    in_support = True
                    position = ranks_of(order_for(arm, known_rows, in_support))
                    for step, view in enumerate(views):
                        ranked = position[view['consistent']]
                        pick = -1
                        for candidate in view['select']:
                            if ranked[candidate] < budget:
                                pick = candidate
                                break
                        hit = 0 if pick < 0 else int(view['good'][pick])
                        curves[group][budget][arm][world_number, step] = hit
                        if arm == 'revealed':
                            learned = view['mechanism']
                        elif pick >= 0:
                            learned = int(view['consistent'][pick])
                        else:
                            continue
                        fresh = {harness.key_index[key]
                                 for key in catalog.keys(learned)} - known
                        if not fresh:
                            continue
                        known |= fresh
                        score = np.zeros(keys)
                        score[sorted(known)] = 1.
                        known_rows = harness.row_scores(np.log(score + FLOOR))
                        was = in_support
                        unseen = float((appearance[sorted(known)] == 0).mean())
                        in_support = unseen <= UNSEEN_LIMIT
                        if arm == 'warm_detect' and was and not in_support:
                            fallbacks[group][budget] += 1
                        position = ranks_of(order_for(arm, known_rows, in_support))

    boot = np.random.default_rng(SEED + 3)
    draws = boot.integers(0, WORLDS, (BOOT, WORLDS))
    result = {'scope': 'bounding the loss of a cold-start prior outside its support',
              'catalog': {'rows': catalog.size, 'digest': catalog.digest()},
              'training_worlds': len(training), 'held_out_families': list(HELD_OUT_FAMILIES),
              'unseen_limit': UNSEEN_LIMIT, 'worlds': WORLDS, 'stream': STREAM,
              'seed': SEED, 'groups': {}}

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
                         for point in CHECKPOINTS} for arm in ARMS},
                     'detector_fallbacks': fallbacks[group][budget]}
            for arm in ARMS:
                if arm in ('blind', 'revealed'):
                    continue
                difference = totals[arm] - totals['blind']
                sums = difference[draws].sum(axis=1)
                entry.setdefault('minus_blind', {})[arm] = {
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
            print('\n== {} budget {} ({} detector fallbacks)'.format(
                group, budget, entry['detector_fallbacks']))
            print('arm'.ljust(16) + 'solved'.rjust(9) + 'first20'.rjust(10)
                  + 'last20'.rjust(9) + 'minus blind'.rjust(24))
            for arm in ARMS:
                first, last = entry['first_twenty_vs_last_twenty'][arm]
                tail = ''
                if arm in entry.get('minus_blind', {}):
                    row = entry['minus_blind'][arm]
                    tail = '{:+.0f} {}'.format(row['sum'],
                                               [round(x) for x in row['interval']])
                print(arm.ljust(16) + '{:9.1f}{:10.3f}{:9.3f}'.format(
                    entry['solved'][arm], first, last) + tail.rjust(24))
    print('\ncost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
