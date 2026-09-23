"""An unbounded supply of task mechanisms, drawn from structured worlds.

Every transfer result in this repository was measured on fresh seeds of six
hand-written generators, so "unfamiliar" could only ever mean a new instance.
The mechanism-holdout check then showed that the one surviving claim was
familiarity with those six. A learning-ability claim needs mechanisms that are
drawn, not chosen, and a held-out mechanism has to be a random variable.

This module supplies that. A mechanism is a character predicate written in the
DSL's own ordinal expression language (`rsi.semantic_invention._char_predicate`
with `kind="ord_expr"`), so the host interpreter, not this module, decides what
a predicate means. Predicates are enumerated once into a catalog of
behaviourally distinct masks over a 256 character alphabet, and a *world* is a
latent structure over that catalog that a task's mechanism is drawn from.

Four properties make the resulting benchmark say something the old one could
not:

* **The truth is in the hypothesis space.** Mechanisms are drawn from the same
  catalog a solver enumerates, so an unsolved task is a failure of inductive
  bias or of budget, never of coverage. There is no max-over-noisy-labels
  standing in for an oracle.
* **Unfamiliarity is graded.** A fresh string is a new instance, a fresh
  catalog entry is a new mechanism, a fresh key set is a new world. The three
  splits are different questions and are never merged.
* **The structure is hidden from every arm.** A world is defined by the atom
  keys its mechanisms may use; nothing in a task reveals them, so an arm that
  exploits the structure had to acquire it from experience.
* **Resources are countable.** A solver scans candidates in some order and
  stops when its budget runs out; the budget is the number of entries scanned.
  "One larger budget" is therefore always available as a default.

Task form. The alphabet is `chr(0x800 + i)`, Samaritan letters: every character
has Unicode category Lo, so the interpreter's built-in letter/digit transition
carries no signal and the predicate has to be invented. An example is a string
of 2-5 characters satisfying the mechanism followed by 2-5 characters that do
not; the answer is the first block.

A hypothesis is a predicate `X` read as *the answer is the longest prefix of
characters satisfying X*. It reproduces an example exactly when every character
of the first block satisfies `X` and the first character of the second block
does not, which is two integer tests against masks. `render_program` emits

    Concat(Slice({"kind":"start"}, {"kind":"run","predicate":X,"ordinal":1,
                                    "side":"end"}))

whose interpreter reading is "up to the end of the *first* run of X", and the
two agree in one direction only: a hypothesis that passes the mask tests always
passes the interpreter, while the interpreter additionally accepts programs
whose first run begins after position zero. Grading is by the prefix reading,
which is therefore sound and slightly conservative; the audit of the
confirmation measures the gap at 0.14% of picks (105 of 75,063). The true
mechanism always satisfies the prefix reading, so no task is made unsolvable by
it.
"""
from __future__ import annotations

import hashlib
import json
import random

from .semantic_invention import _char_predicate, render_span

ALPHABET_BASE = 0x800
ALPHABET_SIZE = 256
FULL = (1 << ALPHABET_SIZE) - 1
ALPHABET = [chr(ALPHABET_BASE + index) for index in range(ALPHABET_SIZE)]

VISIBLE = 8
HIDDEN = 16
BLOCK = (2, 5)

# Density bounds a drawn mechanism must satisfy, so that both blocks of an
# example can always be filled. Candidates are not filtered by density: a
# solver may consider a predicate no mechanism would ever be.
DENSITY = (0.2, 0.8)

ORD = {"op": "ord"}
COMPOUND_OPS = ("bool_and", "bool_or", "bool_xor")


def _eq(left, right):
    return {"op": "eq", "left": left, "right": right}


def _mod(arg, modulus):
    return {"op": "mod", "arg": arg, "modulus": modulus}


def atom_expressions():
    """The catalog's depth-one predicates as (key, family, expression).

    The key names the atom's parameters and is the unit a world is built from;
    the family is the coarser grouping a mechanism holdout can withhold.
    """
    out = []
    for modulus in range(2, 17):
        for residue in range(modulus):
            out.append((f'mod:{modulus}:{residue}', 'mod', _eq(_mod(ORD, modulus), residue)))
    for position in range(8):
        bit = {"op": "bit", "arg": ORD, "position": position}
        out.append((f'bit:{position}:0', 'bit', _eq(bit, 0)))
        out.append((f'bit:{position}:1', 'bit', _eq(bit, 1)))
    for cut in range(16, 256, 16):
        out.append((f'threshold:{cut}', 'threshold',
                    {"op": "ge", "left": ORD, "right": ALPHABET_BASE + cut}))
    for mask in (0xFF, 0x0F, 0xF0, 0x33, 0x55, 0xAA, 0x3C):
        masked = {"op": "mask", "arg": ORD, "mask": mask}
        for value in range(9):
            out.append((f'popcount:{mask:02x}:{value}', 'popcount',
                        _eq({"op": "popcount", "arg": masked}, value)))
        for value in (0, 1):
            out.append((f'parity:{mask:02x}:{value}', 'parity',
                        _eq({"op": "parity", "arg": masked}, value)))
    for divisor in (2, 3, 4, 5, 7):
        quotient = {"op": "div", "left": ORD, "divisor": divisor}
        for modulus in (2, 3, 5):
            for residue in range(modulus):
                out.append((f'divmod:{divisor}:{modulus}:{residue}', 'divmod',
                            _eq(_mod(quotient, modulus), residue)))
    for right in (6, 10, 14, 15, 21, 35):
        out.append((f'gcd:{right}', 'gcd',
                    {"op": "gt", "left": {"op": "gcd", "left": ORD, "right": right},
                     "right": 1}))
    for key in (0x55, 0xAA, 0x3C):
        flipped = {"op": "xor", "left": ORD, "right": key}
        for modulus in (3, 5, 7):
            for residue in range(modulus):
                out.append((f'xormod:{key:02x}:{modulus}:{residue}', 'xormod',
                            _eq(_mod(flipped, modulus), residue)))
    for shift in (1, 3, 5):
        rotated = {"op": "rotl", "arg": ORD, "width": 8, "shift": shift}
        for modulus in (3, 5):
            for residue in range(modulus):
                out.append((f'rotmod:{shift}:{modulus}:{residue}', 'rotmod',
                            _eq(_mod(rotated, modulus), residue)))
    return out


def mask_of(expr):
    """Truth mask over the alphabet, evaluated by the host interpreter."""
    predicate = {"kind": "ord_expr", "expr": expr}
    mask = 0
    for index, char in enumerate(ALPHABET):
        if _char_predicate(char, predicate):
            mask |= 1 << index
    return mask


class Catalog:
    """Every behaviourally distinct predicate the space contains.

    A row is stored as a code, not as an expression tree: `(op, left, right,
    negated)` with atom indices, where `op` is -1 for a bare atom. The
    expression is rebuilt on demand, which keeps a quarter of a million rows
    inside a few tens of megabytes.
    """

    def __init__(self, atoms, codes, masks):
        self.atoms = atoms
        self.codes = codes
        self.masks = masks
        self.size = len(codes)

    def expr(self, index):
        op, left, right, negated = self.codes[index]
        if op < 0:
            expr = self.atoms[left][2]
        else:
            expr = {"op": COMPOUND_OPS[op], "left": self.atoms[left][2],
                    "right": self.atoms[right][2]}
        return {"op": "not", "arg": expr} if negated else expr

    def keys(self, index):
        op, left, right, _ = self.codes[index]
        return (self.atoms[left][0],) if op < 0 else (self.atoms[left][0], self.atoms[right][0])

    def families(self, index):
        op, left, right, _ = self.codes[index]
        return (self.atoms[left][1],) if op < 0 else \
            tuple(sorted((self.atoms[left][1], self.atoms[right][1])))

    def depth(self, index):
        return 1 if self.codes[index][0] < 0 else 2

    def complexity(self, index):
        op, left, right, negated = self.codes[index]
        base = _tree_size(self.atoms[left][2])
        if op >= 0:
            base += _tree_size(self.atoms[right][2]) + 1
        return base + (1 if negated else 0)

    def digest(self):
        sha = hashlib.sha256()
        sha.update(json.dumps([list(atom[:2]) for atom in self.atoms],
                              separators=(",", ":")).encode())
        for code, mask in zip(self.codes, self.masks):
            sha.update(json.dumps([code, mask], separators=(",", ":")).encode())
        return sha.hexdigest()


def _tree_size(expr):
    if not isinstance(expr, dict):
        return 1
    return 1 + sum(_tree_size(value) for value in expr.values() if isinstance(value, dict))


def build_catalog():
    """Atoms, every cross-family pair under three boolean operators, and every
    complement, reduced to one representative per distinct mask.

    The representative kept is the one whose code sorts first, so the catalog
    is a function of the atom list alone and carries no arm's preferences.
    """
    atoms = atom_expressions()
    atom_masks = [mask_of(expr) for _key, _family, expr in atoms]
    best = {}

    def offer(mask, code):
        if mask == 0 or mask == FULL:
            return
        current = best.get(mask)
        if current is None or code < current:
            best[mask] = code

    for index, mask in enumerate(atom_masks):
        offer(mask, (-1, index, -1, False))
        offer((~mask) & FULL, (-1, index, -1, True))
    count = len(atoms)
    for left in range(count):
        family = atoms[left][1]
        mask_left = atom_masks[left]
        for right in range(left + 1, count):
            if atoms[right][1] == family:
                continue
            mask_right = atom_masks[right]
            for op, mask in enumerate((mask_left & mask_right, mask_left | mask_right,
                                       mask_left ^ mask_right)):
                offer(mask, (op, left, right, False))
                offer((~mask) & FULL, (op, left, right, True))

    ordered = sorted(best.items(), key=lambda item: (item[1], item[0]))
    masks = [mask for mask, _code in ordered]
    codes = [code for _mask, code in ordered]
    return Catalog(atoms, codes, masks)


WORDS = ALPHABET_SIZE // 64


def _words(mask):
    return [(mask >> (64 * word)) & 0xFFFFFFFFFFFFFFFF for word in range(WORDS)]


def pack(catalog):
    """Catalog masks as a (rows, 4) uint64 array, for whole-catalog tests."""
    import numpy as np
    return np.array([_words(mask) for mask in catalog.masks], dtype=np.uint64)


def vector_test(packed, pos, neg):
    """Which catalog rows reproduce a `(pos, neg)` constraint pair."""
    import numpy as np
    pos_words = np.array(_words(pos), dtype=np.uint64)
    neg_words = np.array(_words(neg), dtype=np.uint64)
    keeps = ((packed & pos_words) == pos_words).all(axis=1)
    avoids = ((packed & neg_words) == np.uint64(0)).all(axis=1)
    return keeps & avoids


def densities(packed):
    import numpy as np
    bits = np.unpackbits(packed.view(np.uint8).reshape(packed.shape[0], -1), axis=1)
    return bits.sum(axis=1) / ALPHABET_SIZE


def make_task(catalog, index, rng, visible=VISIBLE, hidden=HIDDEN):
    """One task: examples split by a mechanism, plus its constraint masks.

    `pos`/`neg` are what a candidate must satisfy to reproduce the examples:
    every character of a first block, and the first character of each second
    block. They are recorded separately for the visible and hidden halves so
    that consistency and correctness are the same two integer tests.
    """
    mask = catalog.masks[index]
    positive = [bit for bit in range(ALPHABET_SIZE) if mask >> bit & 1]
    negative = [bit for bit in range(ALPHABET_SIZE) if not mask >> bit & 1]
    examples, spans = [], []
    for _ in range(visible + hidden):
        left = [rng.choice(positive) for _ in range(rng.randint(*BLOCK))]
        right = [rng.choice(negative) for _ in range(rng.randint(*BLOCK))]
        examples.append(["".join(ALPHABET[bit] for bit in left + right),
                         "".join(ALPHABET[bit] for bit in left)])
        spans.append((left, right))

    def constraints(part):
        pos = neg = 0
        for left, right in part:
            for bit in left:
                pos |= 1 << bit
            neg |= 1 << right[0]
        return pos, neg

    visible_pos, visible_neg = constraints(spans[:visible])
    hidden_pos, hidden_neg = constraints(spans[visible:])
    return {"mechanism": index, "visible": examples[:visible], "hidden": examples[visible:],
            "visible_pos": visible_pos, "visible_neg": visible_neg,
            "hidden_pos": hidden_pos, "hidden_neg": hidden_neg}


def consistent(mask, task):
    return (mask & task["visible_pos"]) == task["visible_pos"] and not mask & task["visible_neg"]


def correct(mask, task):
    return (mask & task["hidden_pos"]) == task["hidden_pos"] and not mask & task["hidden_neg"]


def render_program(expr):
    """The interpreter-checkable program a candidate predicate stands for."""
    right = {"kind": "run", "predicate": {"kind": "ord_expr", "expr": expr},
             "ordinal": 1, "side": "end"}
    return "Concat(" + render_span({"kind": "start"}, right) + ")"


class World:
    """A latent structure a task's mechanism is drawn from.

    A world admits the catalog rows built only from its key set. Nothing in a
    task says which keys those are, and no arm is given the world object: an
    arm that does better inside a world had to infer the structure from solved
    tasks, which is the whole question.
    """

    def __init__(self, name, keys, members):
        self.name = name
        self.keys = tuple(sorted(keys))
        self.members = members

    def __len__(self):
        return len(self.members)


def drawable_index(catalog, density):
    """Catalog rows a mechanism may be drawn from, grouped by the atom keys
    they are built from."""
    by_key = {}
    for index in range(catalog.size):
        if not DENSITY[0] <= density[index] <= DENSITY[1]:
            continue
        for key in catalog.keys(index):
            by_key.setdefault(key, []).append(index)
    return by_key


def world_members(catalog, by_key, keys):
    """Every drawable row built only from `keys`."""
    allowed = set(keys)
    members, seen = [], set()
    for key in keys:
        for index in by_key.get(key, ()):
            if index in seen:
                continue
            seen.add(index)
            if set(catalog.keys(index)) <= allowed:
                members.append(index)
    return sorted(members)


def make_worlds(catalog, density, count, keys_per_world, seed, minimum=200,
                coherence='family', families_per_world=3):
    """Sample worlds by drawing key sets and collecting the rows they admit.

    A world's members are restricted to drawable densities, so every member can
    generate tasks. Worlds with too few members are rejected rather than
    padded, so world size never silently becomes the variable under study.

    `coherence` decides whether worlds share structure with each other. Under
    'family' a world's keys are drawn from a few atom families, so a fact about
    worlds in general is available to be learned; under 'uniform' the keys are
    drawn from the whole pool and no such fact exists. The second setting is
    the control for any claim that experience across worlds transfers.
    """
    by_key = drawable_index(catalog, density)
    key_names = sorted(by_key)
    by_family = {}
    for key in key_names:
        by_family.setdefault(key.split(':')[0], []).append(key)
    family_names = sorted(by_family)
    rng = random.Random(seed)
    worlds, attempts = [], 0
    while len(worlds) < count and attempts < count * 200:
        attempts += 1
        if coherence == 'family':
            families = rng.sample(family_names, families_per_world)
            pool = [key for family in families for key in by_family[family]]
            if len(pool) < keys_per_world:
                continue
            chosen = rng.sample(pool, keys_per_world)
        elif coherence == 'uniform':
            chosen = rng.sample(key_names, keys_per_world)
        else:
            raise ValueError(coherence)
        members = world_members(catalog, by_key, chosen)
        if len(members) < minimum:
            continue
        worlds.append(World(f'world{len(worlds):02d}', chosen, sorted(members)))
    if len(worlds) < count:
        raise RuntimeError(f'only {len(worlds)} of {count} worlds met the size floor')
    return worlds
