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


def _affinity(observed_sets, keys):
    """Positive PMI of co-occurrence among the atoms any world contained."""
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
    return seen, affinity


def _cluster(seen, affinity, groups, keys, seed):
    from sklearn.cluster import SpectralClustering
    labels = np.full(keys, -1)
    labels[seen] = SpectralClustering(groups, affinity='precomputed', random_state=seed,
                                      assign_labels='cluster_qr').fit_predict(affinity)
    return labels


def log_likelihood(observed_sets, labels, per_world=3, slip=.05):
    """Log probability of worlds under 'pick `per_world` groups uniformly, then
    atoms uniformly from their union', each atom slipping to any seen atom with
    probability `slip`. Atoms the grouping has never seen count as slips."""
    groups = int(labels.max()) + 1
    sizes = np.bincount(labels[labels >= 0], minlength=groups)
    seen = int((labels >= 0).sum())
    total = 0.
    for indices in observed_sets:
        present = np.bincount(labels[list(indices)][labels[list(indices)] >= 0],
                              minlength=groups)
        unseen = len(indices) - present.sum()
        terms = []
        for triple in itertools.combinations(range(groups), per_world):
            union = sizes[list(triple)].sum()
            inside = present[list(triple)].sum()
            outside = present.sum() - inside + unseen
            terms.append(inside * np.log((1 - slip) / union + slip / seen)
                         + outside * np.log(slip / seen))
        terms = np.array(terms)
        total += terms.max() + np.log(np.exp(terms - terms.max()).mean())
    return total


def learn_groups(observed_sets, keys, choices=range(3, 16), seed=0, select='eigengap'):
    """Labels per atom (-1 if never observed) and the chosen group count.

    `select='eigengap'` takes the largest gap in the normalised Laplacian's
    spectrum. `select='likelihood'` clusters the first four fifths of the
    worlds at every count in `choices`, keeps the count under which the last
    fifth is most probable (`log_likelihood`), and reclusters all worlds."""
    from scipy.sparse.csgraph import laplacian

    if select == 'likelihood':
        cut = len(observed_sets) * 4 // 5
        fit_seen, fit_affinity = _affinity(observed_sets[:cut], keys)
        scores = {g: log_likelihood(observed_sets[cut:],
                                    _cluster(fit_seen, fit_affinity, g, keys, seed))
                  for g in choices}
        groups = max(scores, key=scores.get)
    seen, affinity = _affinity(observed_sets, keys)
    if select == 'eigengap':
        eigenvalues = np.sort(np.linalg.eigvalsh(laplacian(affinity, normed=True)))
        gaps = {k: eigenvalues[k] - eigenvalues[k - 1] for k in choices}
        groups = max(gaps, key=gaps.get)
    return _cluster(seen, affinity, groups, keys, seed), groups


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
