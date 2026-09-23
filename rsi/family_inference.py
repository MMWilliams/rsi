"""A family-level world model for the earned loop.

`mechanism-oracle-structure-probe-20260923.json`: an agent told its world's
three families solves 35.4 of 100 tasks at budget 256 against the champion's
18.2, and 50.4 against 25.6 at 512. The pair prior and its conditional
(affinity) never reach that because they reason about atoms two at a time.
This keeps a posterior over the triple of families the world is drawn from.

Every atom the agent has evidence for is an observation of its family, which a
correct pick guarantees is in the triple and a wrong pick does not: the
likelihood of an observed family under a triple is `slip + (1 - slip)` if the
triple contains it and `slip` otherwise. The prior over triples is their
frequency among the training worlds, smoothed so that no viable triple is ruled
out. A row's family term is the sum over its atoms of `weight * log(FLOOR +
P(atom's family in the world))`, added to the coach's atom terms, so the
posterior only reorders rows and never overrules the evidence terms.

Family labels are syntax: every catalog row is a program whose operator the
solver reads. The model learns nothing from them except which families travel
together, and that from training worlds.
"""
from __future__ import annotations

import itertools

import numpy as np

from .growth_coach import FLOOR, Simulator


class FamilySimulator(Simulator):
    def __init__(self, harness, training_triples, weight, slip, smoothing=1.):
        super().__init__(harness)
        self.weight = weight
        self.slip = slip
        families = sorted(harness.by_family)
        self.family_of = np.array([families.index(key.split(':')[0])
                                   for key in harness.key_names])
        counts = {}
        for triple in training_triples:
            counts[tuple(sorted(triple))] = counts.get(tuple(sorted(triple)), 0) + 1
        self.triples = [tuple(families.index(f) for f in triple)
                        for triple in itertools.combinations(families, 3)]
        prior = np.array([counts.get(tuple(families[i] for i in t), 0) + smoothing
                          for t in self.triples], dtype=float)
        self.log_prior = np.log(prior / prior.sum())
        self.contains = np.zeros((len(self.triples), len(families)))
        for row, triple in enumerate(self.triples):
            self.contains[row, list(triple)] = 1.

    def family_marginals(self, evidence):
        """P(family in the world's triple | families of evidenced atoms)."""
        observed = np.bincount(self.family_of[evidence > 0], minlength=self.contains.shape[1])
        likelihood = np.log(self.slip + (1 - self.slip) * self.contains) @ observed
        posterior = self.log_prior + likelihood
        posterior = np.exp(posterior - posterior.max())
        posterior /= posterior.sum()
        return posterior @ self.contains

    def atom_terms(self, coach, evidence, prior):
        lifted, plain = super().atom_terms(coach, evidence, prior)
        if not self.weight:
            return lifted, plain
        family = self.weight * np.log(FLOOR + self.family_marginals(evidence))[self.family_of]
        lifted = lifted.copy()
        lifted[:self.keys] += family
        return lifted, plain
