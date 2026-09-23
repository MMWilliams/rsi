"""Do near-misses say which atoms a world is built from?

Two coach screens (`mechanism-coach-screen-20260922.json`,
`mechanism-coach-screen2-20260923.json`) found no headroom at tight budgets for
any lever acting on the earned loop's evidence, because at those budgets the
window almost never holds a consistent candidate and no evidence arrives. A
scan tests every row in the window against the visible examples anyway, and
most rows fail. Some fail narrowly: they fit every positive character and
admit a negative one, or exclude every negative and miss a positive. Those
results are free by-products of the scan.

This probe asks whether they carry signal, before anything is built on them.
For the champion's first window (no evidence yet) at four budgets, over the
first 20 tasks of each world, it compares how often the atoms of each outcome
class are atoms of the world, and how well the world's atoms are recovered by
ranking atoms on accumulated near-miss counts after 5 and 20 tasks.

A class is worth a coach lever if its atoms are enriched over the window's
atoms as a whole. Development evidence.
"""
from __future__ import annotations

import random
import sys
import time

import numpy as np

from rsi.common import ROOT, write_json
from rsi.growth_coach import CHAMPION, Prior, Simulator, draw_worlds, observed_sets, triples
from rsi.mechanism_space import make_task
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-near-miss-probe-20260923.json'
SEED = 622101
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
WORLDS = {'seen': 32, 'new_family': 16}
TASKS = 20
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 130
HELD_OUT_FAMILIES = ('popcount', 'xormod')
BUDGETS = (128, 256, 512, 1024)
CLASSES = ('consistent', 'covers_only', 'avoids_only', 'neither')


def words(mask):
    return np.array([(mask >> (64 * w)) & 0xFFFFFFFFFFFFFFFF for w in range(4)],
                    dtype=np.uint64)


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    wall = time.perf_counter()
    harness = Harness()
    harness.set_tiebreak(SEED + 77)
    simulator = Simulator(harness)
    rng = random.Random(SEED)
    seen = [family for family in harness.by_family if family not in HELD_OUT_FAMILIES]
    seen_pool = triples(harness, seen, rng, KEYS_PER_WORLD, MINIMUM_MEMBERS)
    held_pool = [triple for triple in triples(harness, harness.by_family, rng, KEYS_PER_WORLD,
                                              MINIMUM_MEMBERS)
                 if set(triple) & set(HELD_OUT_FAMILIES)]
    groups = {'seen': draw_worlds(harness, seen_pool, WORLDS['seen'], rng, KEYS_PER_WORLD,
                                  MINIMUM_MEMBERS, TASKS),
              'new_family': draw_worlds(harness, held_pool, WORLDS['new_family'], rng,
                                        KEYS_PER_WORLD, MINIMUM_MEMBERS, TASKS)}
    reserved = {index for worlds in groups.values() for world in worlds
                for index in world['stream']}
    training = draw_worlds(harness, seen_pool, TRAINING_WORLDS, rng, KEYS_PER_WORLD,
                           MINIMUM_MEMBERS, 0)
    prior = Prior(harness, observed_sets(harness, training, reserved, PRIOR_SOLVED, rng))

    keys = len(harness.key_names)
    zero = np.zeros(keys + 1)
    constants = simulator.constants(CHAMPION, prior)
    share = CHAMPION.share(1024)
    scores = simulator.orderings((zero, zero), constants, share)
    windows = {budget: np.flatnonzero(simulator.window(scores, budget, share))
               for budget in BUDGETS}
    packed = harness.packed

    result = {'scope': 'signal in near-miss outcomes of the first window', 'seed': SEED,
              'catalog': {'rows': harness.catalog.size, 'digest': harness.catalog.digest()},
              'tasks_per_world': TASKS, 'groups': {}}
    for group, worlds in groups.items():
        block = {}
        for budget in BUDGETS:
            rows = windows[budget]
            left, right = simulator.left[rows], simulator.right[rows]
            window_atoms = np.bincount(left, minlength=keys + 1)[:keys] + \
                np.bincount(right, minlength=keys + 1)[:keys]
            occurrences = {name: [0, 0] for name in CLASSES + ('window',)}
            recall = {5: [], 20: []}
            base_recall = []
            for world in worlds:
                members = np.zeros(keys, dtype=bool)
                members[[harness.key_index[key] for key in world['keys']]] = True
                near = np.zeros(keys)
                for step, mechanism in enumerate(world['stream'][:TASKS]):
                    task = make_task(harness.catalog, mechanism, rng)
                    pos, neg = words(task['visible_pos']), words(task['visible_neg'])
                    covers = ((packed[rows] & pos) == pos).all(axis=1)
                    avoids = ((packed[rows] & neg) == 0).all(axis=1)
                    kinds = {'consistent': covers & avoids, 'covers_only': covers & ~avoids,
                             'avoids_only': avoids & ~covers, 'neither': ~covers & ~avoids,
                             'window': np.ones(len(rows), dtype=bool)}
                    for name, chosen in kinds.items():
                        atoms = np.concatenate([left[chosen], right[chosen]])
                        atoms = atoms[atoms < keys]
                        occurrences[name][0] += int(members[atoms].sum())
                        occurrences[name][1] += len(atoms)
                    for chosen in (kinds['covers_only'], kinds['avoids_only']):
                        count = chosen.sum()
                        if count:
                            atoms = np.concatenate([left[chosen], right[chosen]])
                            np.add.at(near, atoms[atoms < keys], 1. / count)
                    if step + 1 in recall:
                        # Atoms never in the window cannot be ranked by it;
                        # rank the ones that were, and score recall of the
                        # world's atoms among the top 14.
                        top = np.argsort(-(near + 1e-9 * window_atoms))[:KEYS_PER_WORLD]
                        recall[step + 1].append(float(members[top].mean()))
                base_recall.append(float(members[np.argsort(-window_atoms)[:KEYS_PER_WORLD]]
                                         .mean()))
            block[str(budget)] = {
                'window_rows': int(len(rows)),
                'share_of_atoms_in_world': {name: (hit / total if total else None)
                                            for name, (hit, total) in occurrences.items()},
                'atom_occurrences': {name: total for name, (_hit, total) in occurrences.items()},
                'top14_precision_near_miss': {str(k): float(np.mean(v))
                                              for k, v in recall.items()},
                'top14_precision_window_frequency': float(np.mean(base_recall))}
        result['groups'][group] = block
    result['wall_seconds'] = time.perf_counter() - wall
    write_json(OUT, result)

    for group, block in result['groups'].items():
        print(f'\n== {group}: share of atom occurrences that are world atoms')
        print('budget'.ljust(8) + ''.join(n.rjust(13) for n in CLASSES + ('window',))
              + '  top14@5 top14@20 top14 by frequency')
        for budget, entry in block.items():
            shares = entry['share_of_atoms_in_world']
            print(budget.ljust(8) + ''.join(
                ('{:13.3f}'.format(shares[n]) if shares[n] is not None else ' ' * 13)
                for n in CLASSES + ('window',))
                + '  {:.3f}   {:.3f}    {:.3f}'.format(
                    entry['top14_precision_near_miss']['5'],
                    entry['top14_precision_near_miss']['20'],
                    entry['top14_precision_window_frequency']))
            print(' ' * 8 + ''.join('{:13d}'.format(entry['atom_occurrences'][n])
                                    for n in CLASSES + ('window',)))
    print('\n{:.0f}s'.format(result['wall_seconds']))


if __name__ == '__main__':
    sys.exit(main())
