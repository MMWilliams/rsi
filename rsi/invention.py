"""Atom invention from the ord_expr grammar: the hypothesis-space axis.

The catalog's 313 atoms are a hand-picked subset of the depth-one expressions
the host interpreter accepts. An agent whose language lacks a family cannot
reach that family's mechanisms by scanning further; it can reach them by
constructing atoms from the grammar and keeping the ones that reproduce the
visible examples of tasks it could not solve, alone or joined to an atom it
already knows. Nothing here reads a family label. The truth labels an invented
atom only when the result is scored.

Cost is counted in candidate tests: one test checks one candidate against the
world's unsolved tasks, which is the same order of work as scanning one
catalog row against one task, and is reported as such.
"""
from __future__ import annotations

import numpy as np

from .mechanism_space import ALPHABET_BASE, FULL, ORD, _eq, _mod, _words, mask_of

MASKS = (0xFF, 0x0F, 0xF0, 0x33, 0x55, 0xAA, 0x3C, 0xC3, 0x5A, 0x69, 0x96, 0xA5, 0x0C, 0x30, 0x1E, 0x78)
KEYS = (0x55, 0xAA, 0x3C, 0x0F, 0xF0, 0x69, 0x96, 0xC3)
WORD = np.uint64(0xFFFFFFFFFFFFFFFF)


def transforms():
    """(tag, name, expr): the value a reduction is applied to."""
    out = [('ord', 'ord', ORD)]
    for m in MASKS:
        out.append(('mask', f'mask{m:02x}', {"op": "mask", "arg": ORD, "mask": m}))
    for k in range(1, 8):
        out.append(('shr', f'shr{k}', {"op": "shr", "arg": ORD, "position": k}))
    for s in range(1, 8):
        out.append(('rotl', f'rotl{s}', {"op": "rotl", "arg": ORD, "width": 8, "shift": s}))
    for key in KEYS:
        out.append(('xor', f'xor{key:02x}', {"op": "xor", "left": ORD, "right": key}))
    for d in range(2, 10):
        out.append(('div', f'div{d}', {"op": "div", "left": ORD, "divisor": d}))
    return out


def reductions(tag, arg):
    """(tag, name, expr): equality and order tests on a transformed value."""
    out = []
    for modulus in range(2, 17):
        for residue in range(modulus):
            out.append(('mod', f'mod{modulus}={residue}', _eq(_mod(arg, modulus), residue)))
    for position in range(8):
        for value in (0, 1):
            out.append(('bit', f'bit{position}={value}',
                        _eq({"op": "bit", "arg": arg, "position": position}, value)))
    for value in range(9):
        out.append(('popcount', f'popcount={value}', _eq({"op": "popcount", "arg": arg}, value)))
    for value in (0, 1):
        out.append(('parity', f'parity={value}', _eq({"op": "parity", "arg": arg}, value)))
    if tag == 'ord':
        for cut in range(16, 256, 16):
            out.append(('ge', f'ge{cut}', {"op": "ge", "left": arg, "right": ALPHABET_BASE + cut}))
    for right in (6, 10, 14, 15, 21, 35, 30, 42, 70, 105):
        out.append(('gcd', f'gcd{right}',
                    {"op": "gt", "left": {"op": "gcd", "left": arg, "right": right}, "right": 1}))
    return out


def _size(expr):
    if not isinstance(expr, dict):
        return 1
    return 1 + sum(_size(v) for v in expr.values() if isinstance(v, dict))


def candidates():
    """Every depth-one candidate as (name, (transform tag, reduction tag), expr,
    mask), one per distinct mask up to complement, in breadth-first order:
    smaller expressions first, enumeration order within a size."""
    out, seen = [], set()
    for ttag, tname, texpr in transforms():
        for rtag, rname, rexpr in reductions(ttag, texpr):
            mask = mask_of(rexpr)
            if mask in (0, FULL) or mask in seen or (FULL & ~mask) in seen:
                continue
            seen.add(mask)
            out.append((f'{tname}:{rname}', (ttag, rtag), rexpr, mask))
    out.sort(key=lambda c: _size(c[2]))
    return out


def words(masks):
    return np.array([_words(m) for m in masks], dtype=np.uint64).reshape(-1, 4)


def fits_any(cand, pos, neg, earned):
    """Per task: does the candidate, its complement, or its and/or/xor with one
    earned atom (either complemented) reproduce the task's visible examples?
    `cand` (4,), `pos`/`neg` (T, 4), `earned` (E, 4), all uint64 words."""
    c = cand[None, :]
    hyps = [c, ~c & WORD]
    if len(earned):
        for h in (c & earned, c | earned, c ^ earned):
            hyps.append(h)
            hyps.append(~h & WORD)
    h = np.concatenate(hyps, axis=0)
    ok = ((h[:, None, :] & pos[None]) == pos[None]).all(-1) & ((h[:, None, :] & neg[None]) == 0).all(-1)
    return ok.any(axis=0)


def invent(cands, tasks, earned, known, budget=None):
    """Breadth-first invention for one world. `cands` is the candidate list,
    `tasks` the (pos, neg) constraints of the tasks the agent could not solve,
    `earned` the masks of atoms it earned there, `known` the set of masks (and
    complements) already in its language. A candidate is kept when it fits at
    least one still-uncovered task. Returns (kept candidate indices, tests)."""
    if not tasks:
        return [], 0
    pos, neg = words([t[0] for t in tasks]), words([t[1] for t in tasks])
    earned = words(earned) if len(earned) else np.zeros((0, 4), dtype=np.uint64)
    covered = np.zeros(len(tasks), dtype=bool)
    kept, tests = [], 0
    for index, (_name, _tags, _expr, mask) in enumerate(cands):
        if covered.all() or (budget is not None and tests >= budget):
            break
        if mask in known or (FULL & ~mask) in known:
            continue
        tests += 1
        open_ = np.flatnonzero(~covered)
        fit = fits_any(words([mask])[0], pos[open_], neg[open_], earned)
        if fit.any():
            kept.append(index)
            covered[open_[fit]] = True
    return kept, tests
