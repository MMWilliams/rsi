"""A world model and a model of the agent's own discovery, fitted jointly.

The agent sees a world only through the atoms of the picks it submitted. Those
earned sets are not samples of the world: they are the world filtered by the
agent's own search, which finds some atoms far more often than others
(recall 0.74-0.84 for mod atoms, 0.21-0.31 for rotmod and gcd on seed 643101).
Treating them as samples teaches the agent its blind spots as facts about the
world. Here both are latent and fitted together, without labels:

world model   each world picks `per_world` of G atom groups; each atom of their
              union is in the world with probability q_in (= keys per world
              over the union's size), any other atom with probability q_out.
self model    an atom in the world is earned with probability r[k] (the agent's
              discovery rate for that atom); an atom not in the world is earned
              with probability f[k] (it was imported by a wrong pick).

So P(atom k earned | world uses groups T) = r[k] q_kT + f[k] (1 - q_kT), atoms
independent given T. EM: the E-step is the posterior over each world's group
set; the M-step updates r and f from expected membership and reassigns each
atom to the group under which its earned pattern across worlds is most
probable. Initialised from spectral clustering on positive PMI.
"""
from __future__ import annotations

import itertools

import numpy as np

from .learned_groups import _affinity, _cluster

EPS = 1e-6


class SelfWorldModel:
    def __init__(self, labels, r, f, per_world, keys_per_world, q_out, seen):
        self.labels = labels            # group per atom, -1 if never earned
        self.r, self.f = r, f           # discovery and import rates per atom
        self.per_world = per_world
        self.keys_per_world = keys_per_world
        self.q_out = q_out
        self.seen = seen                # atoms earned in at least one world
        self.groups = int(labels.max()) + 1
        self.triples = np.array(list(itertools.combinations(range(self.groups), per_world)))
        self._membership()

    def _membership(self):
        """q[T, k]: probability atom k is in a world that uses group set T."""
        g, labels = self.groups, self.labels
        sizes = np.bincount(labels[labels >= 0], minlength=g)
        uses = np.zeros((len(self.triples), g), dtype=bool)
        uses[np.arange(len(self.triples))[:, None], self.triples] = True
        union = (uses * sizes).sum(axis=1)
        q_in = np.minimum(self.keys_per_world / np.maximum(union, 1), 1. - EPS)
        inside = np.zeros((len(self.triples), len(labels)), dtype=bool)
        grouped = labels >= 0
        inside[:, grouped] = uses[:, labels[grouped]]
        self.uses = uses
        self.q = np.where(inside, q_in[:, None], self.q_out)

    def _earn_probability(self):
        return np.clip(self.r * self.q + self.f * (1 - self.q), EPS, 1 - EPS)

    def world_posterior(self, earned):
        """Posterior over group sets per world (rows) and the log likelihood of
        each world, from a binary worlds-by-atoms matrix of earned sets."""
        p = self._earn_probability()[:, self.seen]
        e = earned[:, self.seen]
        loglik = e @ np.log(p).T + (1 - e) @ np.log(1 - p).T
        top = loglik.max(axis=1, keepdims=True)
        weights = np.exp(loglik - top)
        total = weights.sum(axis=1, keepdims=True)
        return weights / total, (top + np.log(total / len(self.triples))).ravel()

    def membership(self, earned):
        """P(atom k is in world w | its earned set): the world model's belief
        about each world's true atoms, correcting for what the agent misses."""
        post, _ = self.world_posterior(earned)
        q = post @ self.q                     # prior membership, averaged over T
        r, f = self.r, self.f
        hit = r * q / np.maximum(r * q + f * (1 - q), EPS)
        miss = (1 - r) * q / np.maximum((1 - r) * q + (1 - f) * (1 - q), EPS)
        return np.where(earned > 0, hit, miss)

    def log_likelihood(self, earned):
        return float(self.world_posterior(earned)[1].sum())


def _matrix(sets, keys):
    m = np.zeros((len(sets), keys))
    for w, s in enumerate(sets):
        m[w, list(s)] = 1.
    return m


def fit(earned_sets, keys, groups, per_world=3, keys_per_world=14, iterations=30, seed=0,
        q_out=.01):
    """Joint EM fit; returns the model and its training log likelihood trace."""
    earned = _matrix(earned_sets, keys)
    seen_atoms, affinity = _affinity(earned_sets, keys)
    labels = _cluster(seen_atoms, affinity, groups, keys, seed)
    seen = np.zeros(keys, dtype=bool)
    seen[seen_atoms] = True
    rate = earned.mean(axis=0)
    model = SelfWorldModel(labels, np.clip(rate * 4, .05, .95), np.full(keys, .01),
                           per_world, keys_per_world, q_out, seen)
    trace = []
    for _ in range(iterations):
        post, ll = model.world_posterior(earned)
        trace.append(float(ll.sum()))
        q = post @ model.q
        r, f = model.r, model.f
        joint_in = np.where(earned > 0, r * q, (1 - r) * q)
        joint_out = np.where(earned > 0, f * (1 - q), (1 - f) * (1 - q))
        member = joint_in / np.maximum(joint_in + joint_out, EPS)
        r = (member * earned).sum(0) / np.maximum(member.sum(0), EPS)
        f = ((1 - member) * earned).sum(0) / np.maximum((1 - member).sum(0), EPS)
        model.r = np.clip(r, EPS, 1 - EPS)
        model.f = np.clip(f, EPS, .5)
        # Reassign atoms: expected log likelihood of each atom's earned column
        # if it belonged to each group, holding the world posteriors fixed.
        use = post @ model.uses                          # P(world uses group g)
        q_in = np.median(model.q[model.q > model.q_out]) if (model.q > model.q_out).any() else .1
        p_in = model.r * q_in + model.f * (1 - q_in)
        p_out = model.r * model.q_out + model.f * (1 - model.q_out)
        l1_in, l0_in = np.log(np.clip(p_in, EPS, 1)), np.log(np.clip(1 - p_in, EPS, 1))
        l1_out, l0_out = np.log(np.clip(p_out, EPS, 1)), np.log(np.clip(1 - p_out, EPS, 1))
        a_in = use.T @ earned * l1_in + use.T @ (1 - earned) * l0_in        # [G, K]
        a_out = (1 - use).T @ earned * l1_out + (1 - use).T @ (1 - earned) * l0_out
        score = a_in + a_out
        new = np.where(seen, score.argmax(axis=0), -1)
        changed = int((new != model.labels).sum())
        if changed:
            # keep every group non-empty so the triple space is stable
            counts = np.bincount(new[new >= 0], minlength=model.groups)
            if (counts > 0).all():
                model.labels = new
                model._membership()
        if not changed and len(trace) > 2 and abs(trace[-1] - trace[-2]) < 1e-3 * abs(trace[-1]):
            break
    return model, trace


def select(earned_sets, keys, choices=range(3, 13), per_world=3, **kwargs):
    """Group count by held-out likelihood: fit on the first four fifths of the
    worlds, score the last fifth, refit on all at the best count."""
    cut = len(earned_sets) * 4 // 5
    held = _matrix(earned_sets[cut:], keys)
    scores = {}
    for g in choices:
        if g <= per_world:
            continue
        model, _ = fit(earned_sets[:cut], keys, g, per_world, **kwargs)
        scores[g] = model.log_likelihood(held)
    best = max(scores, key=scores.get)
    model, trace = fit(earned_sets, keys, best, per_world, **kwargs)
    return model, best, scores, trace
