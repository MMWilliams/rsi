"""The mask arithmetic the mechanism experiments rely on must agree with the
host interpreter, or every solve count in them is a count of something else."""
from __future__ import annotations

import random

import numpy as np
import pytest

from rsi.mechanism_space import (ALPHABET, ALPHABET_BASE, DENSITY, FULL, build_catalog,
                                 consistent, correct, densities, drawable_index,
                                 make_task, make_worlds, mask_of, pack, render_program,
                                 vector_test, world_members)
from rsi.mechanism_worlds import interleave, ranks_of
from rsi.semantic_invention import _char_predicate, evaluate_program


@pytest.fixture(scope='module')
def catalog():
    return build_catalog()


@pytest.fixture(scope='module')
def packed(catalog):
    return pack(catalog)


def test_catalog_is_a_function_of_the_atoms(catalog):
    again = build_catalog()
    assert again.size == catalog.size
    assert again.digest() == catalog.digest()


def test_masks_are_distinct_and_proper(catalog):
    assert len(set(catalog.masks)) == catalog.size
    assert all(0 < mask < FULL for mask in catalog.masks)


def test_mask_matches_the_interpreter(catalog):
    rng = random.Random(11)
    for index in rng.sample(range(catalog.size), 40):
        predicate = {'kind': 'ord_expr', 'expr': catalog.expr(index)}
        rebuilt = 0
        for bit, char in enumerate(ALPHABET):
            if _char_predicate(char, predicate):
                rebuilt |= 1 << bit
        assert rebuilt == catalog.masks[index]
        assert mask_of(catalog.expr(index)) == catalog.masks[index]


def test_task_examples_follow_the_mechanism(catalog):
    density = densities(pack(catalog))
    rng = random.Random(3)
    drawable = [index for index in range(catalog.size)
                if DENSITY[0] <= density[index] <= DENSITY[1]]
    for index in rng.sample(drawable, 12):
        task = make_task(catalog, index, rng)
        mask = catalog.masks[index]
        for text, target in task['visible'] + task['hidden']:
            assert text.startswith(target) and 0 < len(target) < len(text)
            assert all(mask >> (ord(char) - ALPHABET_BASE) & 1 for char in target)
            assert not mask >> (ord(text[len(target)]) - ALPHABET_BASE) & 1
        assert consistent(mask, task) and correct(mask, task)


def test_correctness_agrees_with_the_interpreter(catalog, packed):
    """The claim the whole benchmark rests on: a candidate passes the mask test
    for the hidden examples exactly when the interpreter runs its program on
    them successfully."""
    density = densities(packed)
    rng = random.Random(5)
    drawable = [index for index in range(catalog.size)
                if DENSITY[0] <= density[index] <= DENSITY[1]]
    checked = 0
    for index in rng.sample(drawable, 6):
        task = make_task(catalog, index, rng)
        candidates = np.flatnonzero(vector_test(packed, task['visible_pos'],
                                                task['visible_neg']))
        assert index in candidates
        for candidate in list(candidates[:8]) + rng.sample(range(catalog.size), 8):
            program = render_program(catalog.expr(int(candidate)))
            assert bool(evaluate_program(program, task['hidden'])) == \
                correct(catalog.masks[int(candidate)], task)
            checked += 1
    assert checked >= 50


def test_vector_test_matches_the_scalar_tests(catalog, packed):
    rng = random.Random(7)
    density = densities(packed)
    drawable = [index for index in range(catalog.size)
                if DENSITY[0] <= density[index] <= DENSITY[1]]
    task = make_task(catalog, rng.choice(drawable), rng)
    flags = vector_test(packed, task['visible_pos'], task['visible_neg'])
    for index in rng.sample(range(catalog.size), 400):
        assert bool(flags[index]) == consistent(catalog.masks[index], task)


def test_world_members_use_only_the_world_keys(catalog):
    density = densities(pack(catalog))
    worlds = make_worlds(catalog, density, 3, 14, seed=99, minimum=120)
    by_key = drawable_index(catalog, density)
    for world in worlds:
        assert len(world) >= 120
        for index in world.members:
            assert set(catalog.keys(index)) <= set(world.keys)
            assert DENSITY[0] <= density[index] <= DENSITY[1]
        assert world_members(catalog, by_key, world.keys) == world.members


def test_uniform_worlds_are_not_family_coherent(catalog):
    density = densities(pack(catalog))
    coherent = make_worlds(catalog, density, 4, 14, seed=21, minimum=120,
                           coherence='family')
    spread = make_worlds(catalog, density, 4, 14, seed=21, minimum=120,
                         coherence='uniform')
    assert all(len({key.split(':')[0] for key in world.keys}) <= 3 for world in coherent)
    assert max(len({key.split(':')[0] for key in world.keys}) for world in spread) > 3


def test_interleave_spends_the_reserved_share():
    first = np.arange(100)
    second = np.arange(99, -1, -1)
    merged = interleave(first, second, .25)
    assert sorted(merged.tolist()) == list(range(100))
    head = set(merged[:20].tolist())
    assert len(head & set(range(15))) >= 12
    assert len(head & set(range(95, 100))) >= 3
    assert np.array_equal(interleave(first, second, 0.), first)
    assert np.array_equal(interleave(first, second, 1.), second)


def test_ranks_invert_an_order():
    order = np.array([3, 1, 0, 2])
    assert ranks_of(order).tolist() == [2, 1, 3, 0]


@pytest.fixture(scope='module')
def harness():
    from rsi.mechanism_worlds import Harness
    return Harness()


def test_key_scores_are_row_scores(harness):
    rng = np.random.default_rng(13)
    score = rng.normal(size=len(harness.key_names))
    rows = harness.row_scores(score)
    assert np.array_equal(harness.order_from_key_scores(score),
                          harness.order_from_row_scores(rows))
    for index in rng.integers(0, harness.catalog.size, 50):
        keys = harness.catalog.keys(int(index))
        expected = sum(score[harness.key_index[key]] for key in keys)
        assert abs(rows[int(index)] - expected) < 1e-9


def test_pair_scores_read_the_matrix(harness):
    keys = len(harness.key_names)
    matrix = np.random.default_rng(17).normal(size=(keys, keys))
    values = harness.pair_scores(matrix)
    for index in np.random.default_rng(19).integers(0, harness.catalog.size, 50):
        names = harness.catalog.keys(int(index))
        left = harness.key_index[names[0]]
        right = harness.key_index[names[1]] if len(names) > 1 else left
        assert values[int(index)] == matrix[left, right]


def test_a_flat_score_is_the_tiebreak(harness):
    keys = len(harness.key_names)
    harness.set_tiebreak(5)
    order = harness.order_from_key_scores(np.zeros(keys))
    assert np.array_equal(np.argsort(harness.tiebreak, kind='stable'), order)
