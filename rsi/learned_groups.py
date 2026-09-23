"""Groups of atoms learned from which atoms appear together in worlds.

The confirmed family agent (`rsi/family_inference.py`) reads each atom's family
from the program text. Worlds are unions of a few groups of atoms, so atoms of
one group appear together more often than chance, and the grouping can instead
be learned from training worlds alone: build a co-occurrence graph weighted by
positive pointwise mutual information and cut it by spectral clustering, with
the number of groups chosen by the largest gap in the normalised Laplacian's
spectrum. Atoms no training world contained get no group (-1); the agent treats
them as one extra group it knows nothing about.

`LearnedFamilySimulator` is the family agent with these groups in place of the
syntactic families; everything else about it is unchanged.
"""
from __future__ import annotations

import itertools

import numpy as np

from .family_inference import FamilySimulator


def learn_groups(observed_sets, keys, choices=range(3, 16), seed=0):
    """Labels per atom (-1 if never observed) and the chosen group count."""
    from scipy.sparse.csgraph import laplacian
    from sklearn.cluster import SpectralClustering

    worlds = len(observed_sets)
    counts = np.zeros((keys, keys))
    for indices in observed_sets:
        indices = list(indices)
        counts[np.ix_(indices, indices)] += 1.
    appear = np.diag(counts).copy()
    seen = np.flatnonzero(appear > 0)
    joint = counts[np.ix_(seen, seen)] / worlds
    marginal = appear[seen] / worlds
    with np.errstate(divide='ignore'):
        pmi = np.log(joint / np.outer(marginal, marginal))
    affinity = np.where(np.isfinite(pmi), np.maximum(pmi, 0.), 0.)
    np.fill_diagonal(affinity, 0.)
    eigenvalues = np.sort(np.linalg.eigvalsh(laplacian(affinity, normed=True)))
    gaps = {k: eigenvalues[k] - eigenvalues[k - 1] for k in choices}
    groups = max(gaps, key=gaps.get)
    labels = np.full(keys, -1)
    labels[seen] = SpectralClustering(groups, affinity='precomputed', random_state=seed,
                                      assign_labels='cluster_qr').fit_predict(affinity)
    return labels, groups


class LearnedFamilySimulator(FamilySimulator):
    """The family agent over learned groups; unseen atoms form one extra group."""

    def __init__(self, harness, labels, weight, slip, per_world=3):
        super().__init__(harness, [], weight, slip)
        labels = np.asarray(labels)
        groups = int(labels.max()) + 1
        self.family_of = np.where(labels >= 0, labels, groups)
        count = groups + 1
        self.triples = list(itertools.combinations(range(count), per_world))
        self.log_prior = np.log(np.full(len(self.triples), 1. / len(self.triples)))
        self.contains = np.zeros((len(self.triples), count))
        for row, triple in enumerate(self.triples):
            self.contains[row, list(triple)] = 1.
