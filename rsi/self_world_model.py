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
from types import SimpleNamespace

import numpy as np

from .learned_groups import _affinity, _cluster

EPS = 1e-6
R_MIN = .10


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
        self.weight = np.ones(len(labels))   # per-atom prevalence within its group
        self.pi = np.full(len(self.triples), 1. / len(self.triples))  # how often each group set occurs
        self._membership()

    def _membership(self):
        """q[T, k]: probability atom k is in a world that uses group set T;
        within the union, proportional to the atom's prevalence weight."""
        g, labels = self.groups, self.labels
        grouped = labels >= 0
        mass = np.bincount(labels[grouped], weights=self.weight[grouped], minlength=g)
        uses = np.zeros((len(self.triples), g), dtype=bool)
        uses[np.arange(len(self.triples))[:, None], self.triples] = True
        union = (uses * mass).sum(axis=1)
        inside = np.zeros((len(self.triples), len(labels)), dtype=bool)
        inside[:, grouped] = uses[:, labels[grouped]]
        q_in = self.keys_per_world * self.weight[None, :] / np.maximum(union, EPS)[:, None]
        self.uses = uses
        self.q = np.where(inside, np.minimum(q_in, 1. - EPS), self.q_out)

    def sample_worlds(self, count, rng, triple_index=None):
        """Imagined worlds' atom sets: a group set by its learned frequency (or
        the one given), then atoms without replacement in proportion to
        prevalence, as the model believes worlds are made."""
        out = []
        grouped = np.flatnonzero(self.labels >= 0)
        while len(out) < count:
            index = rng.choice(len(self.triples), p=self.pi) if triple_index is None else triple_index
            triple = self.triples[index]
            pool = grouped[np.isin(self.labels[grouped], triple)]
            p = self.weight[pool] / self.weight[pool].sum()
            size = min(self.keys_per_world, len(pool))
            keys = rng.choice(pool, size, replace=False, p=p)
            # a world uses every group it picked
            if set(self.labels[keys].tolist()) == set(triple.tolist()):
                out.append(sorted(keys.tolist()))
        return out

    def _earn_probability(self):
        return np.clip(self.r * self.q + self.f * (1 - self.q), EPS, 1 - EPS)

    def world_posterior(self, earned):
        """Posterior over group sets per world (rows) and the log likelihood of
        each world, from a binary worlds-by-atoms matrix of earned sets."""
        p = self._earn_probability()[:, self.seen]
        e = earned[:, self.seen]
        loglik = e @ np.log(p).T + (1 - e) @ np.log(1 - p).T + np.log(self.pi)[None, :]
        top = loglik.max(axis=1, keepdims=True)
        weights = np.exp(loglik - top)
        total = weights.sum(axis=1, keepdims=True)
        return weights / total, (top + np.log(total)).ravel()

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
        q_out=.01, fixed_r=None, init=None):
    """Joint EM fit; returns the model and its training log likelihood trace.

    `fixed_r` holds the discovery rates (from self-simulation) instead of
    estimating them; only then is per-atom prevalence identifiable, so only
    then is it fitted. `init` starts from another model's groups."""
    earned = _matrix(earned_sets, keys)
    seen_atoms, affinity = _affinity(earned_sets, keys)
    seen = np.zeros(keys, dtype=bool)
    seen[seen_atoms] = True
    if init is not None:
        labels = np.where(seen, init.labels, -1)
    else:
        labels = _cluster(seen_atoms, affinity, groups, keys, seed)
    rate = earned.mean(axis=0)
    r0 = fixed_r if fixed_r is not None else np.clip(rate * 4, .05, .95)
    model = SelfWorldModel(labels, np.clip(r0, EPS, 1 - EPS), np.full(keys, .01),
                           per_world, keys_per_world, q_out, seen)
    trace = []
    for _ in range(iterations):
        post, ll = model.world_posterior(earned)
        trace.append(float(ll.sum()))
        # which group sets occur, and how often: mixture weights, lightly smoothed
        model.pi = (post.sum(axis=0) + 1.) / (len(post) + len(model.pi))
        q = post @ model.q
        r, f = model.r, model.f
        joint_in = np.where(earned > 0, r * q, (1 - r) * q)
        joint_out = np.where(earned > 0, f * (1 - q), (1 - f) * (1 - q))
        member = joint_in / np.maximum(joint_in + joint_out, EPS)
        f = ((1 - member) * earned).sum(0) / np.maximum((1 - member).sum(0), EPS)
        model.f = np.clip(f, EPS, .5)
        use = post @ model.uses                          # P(world uses group g)
        if fixed_r is None:
            r = (member * earned).sum(0) / np.maximum(member.sum(0), EPS)
            model.r = np.clip(r, EPS, 1 - EPS)
        else:
            # prevalence: expected membership per world exposed to the atom's group
            grouped = model.labels >= 0
            exposure = np.ones(keys)
            exposure[grouped] = use[:, model.labels[grouped]].sum(0)
            w = member.sum(0) / np.maximum(exposure, EPS)
            for g in range(model.groups):
                inside = model.labels == g
                if inside.any() and w[inside].mean() > 0:
                    w[inside] = w[inside] / w[inside].mean()
            model.weight = np.clip(np.where(grouped, w, 1.), .05, 20.)
            model._membership()
        score, none = _atom_scores(model, earned, post)
        new = np.where(seen & (score.max(axis=0) > none), score.argmax(axis=0), -1)
        # The self model's verdict binds the world model: an atom the agent
        # would almost never find if it were in a world is not in any world;
        # it is seen only through imports.
        new[model.r < R_MIN] = -1
        changed = int((new != model.labels).sum())
        if changed:
            # keep every group non-empty so the triple space is stable
            counts = np.bincount(new[new >= 0], minlength=model.groups)
            if (counts > 0).all():
                model.labels = new
                model._membership()
        if not changed and len(trace) > 2 and abs(trace[-1] - trace[-2]) < 1e-3 * abs(trace[-1]):
            break
    trace.append(model.log_likelihood(earned))
    return model, trace


def _atom_scores(model, earned, post):
    """Expected log likelihood of each atom's earned column if it belonged to
    each group, holding the world posteriors fixed, and if it belonged to no
    world at all (earned only through the agent's own wrong picks, so every
    earn is an import). Membership in world w for an atom of group g is the
    posterior expectation over w's group sets of keys_per_world / union size."""
    keys = len(model.labels)
    use = post @ model.uses                                              # P(world uses g)
    mass = np.bincount(model.labels[model.labels >= 0],
                       weights=model.weight[model.labels >= 0], minlength=model.groups)
    union = (model.uses * mass).sum(axis=1)
    share = model.keys_per_world / np.maximum(union, EPS)                # per group set
    inside = post @ (model.uses * share[:, None])                        # [W, G]
    score = np.empty((model.groups, keys))
    for g in range(model.groups):
        q = np.minimum(inside[:, [g]] * model.weight[None, :], 1 - EPS) \
            + (1 - use[:, [g]]) * model.q_out
        p = np.clip(model.r * q + model.f * (1 - q), EPS, 1 - EPS)
        score[g] = (earned * np.log(p) + (1 - earned) * np.log(1 - p)).sum(axis=0)
    f_alone = np.clip(earned.mean(axis=0), EPS, 1 - EPS)
    none = (earned * np.log(f_alone) + (1 - earned) * np.log(1 - f_alone)).sum(axis=0)
    return score, none


def _misfit_init(model, earned, share=.05):
    """Free the smallest group for the atoms the model explains worst. A family
    the spectral start never isolated (rotmod: 8 atoms, found a third of the
    time) shows up as atoms that fit no group much better than no world;
    reassignment alone cannot create a group for them."""
    post, _ = model.world_posterior(earned)
    score, none = _atom_scores(model, earned, post)
    labels = model.labels.copy()
    grouped = np.flatnonzero(labels >= 0)
    smallest = int(np.bincount(labels[grouped], minlength=model.groups).argmin())
    moved = grouped[labels[grouped] == smallest]
    second = score.copy()
    second[smallest] = -np.inf
    labels[moved] = second[:, moved].argmax(axis=0)
    margin = score.max(axis=0) - none
    worst = grouped[np.argsort(margin[grouped])[:max(6, int(share * len(grouped)))]]
    labels[worst] = smallest
    return SimpleNamespace(labels=labels)


def fit_restarts(earned_sets, keys, groups, restarts=8, shake=.3, **kwargs):
    """Best of several EM runs by training likelihood: the spectral start,
    starts with a share of atoms moved to random groups, then a start that
    frees the smallest group for the atoms the best fit explains worst."""
    best = None
    for start in range(restarts + 1):
        init = None
        if start == restarts:
            init = _misfit_init(best[0], _matrix(earned_sets, keys))
        elif start:
            rng = np.random.default_rng(start)
            labels = best[0].labels.copy()
            move = (labels >= 0) & (rng.random(len(labels)) < shake)
            labels[move] = rng.integers(groups, size=move.sum())
            init = SimpleNamespace(labels=labels)
        model, trace = fit(earned_sets, keys, groups, init=init, seed=start, **kwargs)
        if best is None or trace[-1] > best[1][-1]:
            best = (model, trace)
    return best


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
