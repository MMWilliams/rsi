"""Shared harness for world-level experiments on the mechanism catalog.

The pieces every world experiment needs and none of them should reimplement:
the derived catalog arrays, world sampling from a family triple, the atom
affinity estimator, and the scan-and-select loop that turns an ordering into a
solve count. An arm is a function from a world's solved mechanisms to an
ordering; everything downstream of that is held identical, so ordering is the
only thing any comparison here can be about.
"""
from __future__ import annotations

import random

import numpy as np

from .mechanism_space import (build_catalog, densities, drawable_index, make_task,
                              pack, vector_test, world_members)


class Harness:
    def __init__(self, atoms=None):
        self.catalog = build_catalog(atoms)
        self.packed = pack(self.catalog)
        self.density = densities(self.packed)
        self.sizes = (self.density * 256).astype(np.int32)
        self.complexity = np.array(
            [self.catalog.complexity(index) for index in range(self.catalog.size)],
            dtype=np.int32)
        self.base = np.arange(self.catalog.size, dtype=np.int64)
        self.by_key = drawable_index(self.catalog, self.density)
        self.by_family = {}
        for key in sorted(self.by_key):
            self.by_family.setdefault(key.split(':')[0], []).append(key)
        self.key_names = sorted(self.by_key)
        self.key_index = {key: index for index, key in enumerate(self.key_names)}
        self.left, self.right = self._key_columns()
        self.set_tiebreak(0)

    def _key_columns(self):
        catalog = self.catalog
        left = np.empty(catalog.size, dtype=np.int32)
        right = np.empty(catalog.size, dtype=np.int32)
        for index in range(catalog.size):
            keys = catalog.keys(index)
            left[index] = self.key_index[keys[0]]
            right[index] = self.key_index[keys[1]] if len(keys) > 1 else -1
        return left, right

    def set_tiebreak(self, seed, stable=False):
        """Fix the order rows are scanned in when an arm scores them equally.

        Catalog order is complexity order, and using it to break ties gave the
        free rules a systematic preference among the rows they cannot tell
        apart: their solve rate jumped between budgets for reasons that had
        nothing to do with their scores. One shared random tie-break makes
        every arm's ordering a function of its scores alone.
        """
        if not stable:
            self.tiebreak = np.random.default_rng(seed).permutation(self.catalog.size)
            return
        # A row's tie-break is a hash of what it is, not of where it sits, so
        # rows keep their relative order when atoms are added to or removed
        # from the language; a language change then changes nothing but the
        # rows it adds or removes.
        import hashlib
        catalog = self.catalog
        keys = np.empty(catalog.size, dtype=np.int64)
        for index, (op, left, right, negated) in enumerate(catalog.codes):
            right_key = catalog.atoms[right][0] if op >= 0 else ''
            name = f'{seed}|{op}|{catalog.atoms[left][0]}|{right_key}|{int(negated)}'.encode()
            keys[index] = int.from_bytes(hashlib.blake2b(name, digest_size=8).digest(), 'little') >> 1
        self.tiebreak = keys

    def order_from_key_scores(self, key_score):
        """A catalog ordering induced by a score over atom keys."""
        return self.order_from_row_scores(self.row_scores(key_score))

    def row_scores(self, key_score):
        return key_score[self.left] + np.where(self.right >= 0, key_score[self.right], 0.)

    def order_from_row_scores(self, score):
        """A catalog ordering from a score per row, for priors that are not a
        sum over atoms: whether two atoms belong to one world is a fact about
        the pair and cannot be written as a score on each of them."""
        return np.lexsort((self.tiebreak, -score))

    def pair_scores(self, matrix):
        """Each row's entry in an atom-by-atom matrix, with a depth-one row
        taking its single atom's diagonal."""
        right = np.where(self.right >= 0, self.right, self.left)
        return matrix[self.left, right]

    def observed_keys(self, mechanisms):
        keys = []
        for index in mechanisms:
            keys.extend(self.catalog.keys(index))
        return keys

    def key_counts(self, mechanisms):
        counts = np.zeros(len(self.key_names))
        for key in self.observed_keys(mechanisms):
            counts[self.key_index[key]] += 1
        return counts

    def sample_world(self, triple, rng, keys_per_world, minimum, attempts=40):
        pool = [key for family in triple for key in self.by_family[family]]
        if len(pool) < keys_per_world:
            return None
        for _ in range(attempts):
            keys = rng.sample(pool, keys_per_world)
            if {key.split(':')[0] for key in keys} != set(triple):
                continue
            members = world_members(self.catalog, self.by_key, keys)
            if len(members) >= minimum:
                return {'keys': tuple(sorted(keys)), 'triple': tuple(sorted(triple)),
                        'members': members}
        return None

    def task_view(self, mechanism, rng):
        """One task reduced to what any ordering-based arm needs to be scored."""
        task = make_task(self.catalog, mechanism, rng)
        consistent = np.flatnonzero(vector_test(self.packed, task['visible_pos'],
                                                task['visible_neg']))
        if len(consistent) == 0:
            return None
        good = vector_test(self.packed, task['hidden_pos'], task['hidden_neg'])[consistent]
        order = np.lexsort((self.complexity[consistent], self.sizes[consistent]))
        return {'consistent': consistent, 'good': good, 'select': order}

    @staticmethod
    def solve(view, position, budget, catalog_size):
        """Scan the first `budget` entries of an ordering, then apply the free
        selection rule to whatever was consistent inside the window."""
        limit = catalog_size if budget is None else budget
        ranked = position[view['consistent']]
        for candidate in view['select']:
            if ranked[candidate] < limit:
                return int(view['good'][candidate])
        return 0


def ranks_of(order):
    position = np.empty(len(order), dtype=np.int32)
    position[order] = np.arange(len(order), dtype=np.int32)
    return position


def affinity(observed_sets, key_count, alpha=2.0):
    """P(atom b is in a world | atom a is in it), estimated by counting worlds.

    Nothing here knows what a family is. If atoms of the same family travel
    together the counts say so, and if worlds have no structure they say that
    instead, so an arm reading this matrix inherits whichever is true.
    """
    appear = np.zeros(key_count)
    cooccur = np.zeros((key_count, key_count))
    for indices in observed_sets:
        indices = list(indices)
        appear[indices] += 1
        block = np.zeros(key_count)
        block[indices] = 1.
        cooccur[np.ix_(indices, range(key_count))] += block
    base = appear / max(len(observed_sets), 1)
    return (cooccur + alpha * base[None, :]) / (appear[:, None] + alpha)


def interleave(first, second, share):
    """One ordering that spends `share` of its budget on `second`.

    A row's position is the earliest budget at which either policy would have
    reached it, which is exactly round-robin interleaving at the given ratio.
    A hedged prior can therefore lose only the reserved fraction, however wrong
    it is about a world it has never seen.
    """
    if share <= 0:
        return first
    if share >= 1:
        return second
    left = ranks_of(first).astype(np.float64) / (1. - share)
    right = ranks_of(second).astype(np.float64) / share
    return np.argsort(np.minimum(left, right), kind='stable')
