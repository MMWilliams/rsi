"""Screen: is the metric estimator fitted to the wrong features?

G4 failed on its control clause, and the fitted-to-true weight correlation was
0.117 and 0.329, so whatever the arm was reading it was not much of the
structure it was meant to recover. The likely reason is a specification
mismatch rather than a shortage of data.

A world is the atoms nearest a centre under a weighted squared distance,

    d(a, b) = sum_i w_i (z_a[i] - z_b[i])^2,

and co-membership means small `d`. The estimator fitted logistic regression on
the elementwise product `z_a[i] * z_b[i]`, which is the inner-product form: for
whitened descriptors the product appears inside the squared difference, but so
do `z_a[i]^2` and `z_b[i]^2`, and dropping them is dropping the terms that say
how far apart the two atoms are in that dimension at all.

This screens the two feature forms against each other on weight recovery
alone, with no tasks and no worlds' worth of solving: draw a weighting, build
worlds from it, observe them as an arm would, fit both ways, and compare the
fitted weights to the truth. If the squared-difference form recovers the
weighting and the product form does not, the G4 arm was misspecified and is
worth rebuilding; if neither recovers it, the arm was not the problem.
"""
from __future__ import annotations

import random
import time

import numpy as np
import psutil
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression

from rsi.common import ROOT, write_json
from rsi.mechanism_space import DENSITY, world_members
from rsi.mechanism_worlds import Harness
from mechanism_atom_clustering import descriptors
from mechanism_metric_worlds import weighted_distance

OUT = ROOT / 'analysis/mechanism-metric-form-20260921.json'
SEED = 615101
DRAWS = 5
ACTIVE_DIMENSIONS = 40
TRAINING_WORLDS = 400
PRIOR_SOLVED = 64
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 110
POSITIVE_PAIRS = 24
NEGATIVE_PAIRS = 48
HELD_OUT_FAMILIES = ('popcount', 'xormod')


def fit(latent, observed_sets, rng, form):
    """Fit a diagonal metric, with features in one of the two forms."""
    size = latent.shape[0]
    features, labels = [], []
    for indices in observed_sets:
        indices = list(indices)
        if len(indices) < 2:
            continue
        pairs = [(rng.choice(indices), rng.choice(indices), 1)
                 for _ in range(POSITIVE_PAIRS)]
        pairs += [(rng.choice(indices), rng.randrange(size), 0)
                  for _ in range(NEGATIVE_PAIRS)]
        for left, right, label in pairs:
            if left == right:
                continue
            if label == 0 and right in indices:
                continue
            row = latent[left] * latent[right] if form == 'product' else \
                -(latent[left] - latent[right]) ** 2
            features.append(row)
            labels.append(label)
    model = LogisticRegression(max_iter=3000, C=.25)
    model.fit(np.asarray(features), np.asarray(labels))
    return np.maximum(model.coef_[0], 0.)


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    latent = descriptors(harness)
    dimensions = latent.shape[1]
    families = np.array([key.split(':')[0] for key in harness.key_names])
    centres = [index for index in range(len(families))
               if families[index] not in HELD_OUT_FAMILIES]

    result = {'scope': 'which feature form recovers the weighting a world is built from',
              'descriptor_dimensions': dimensions, 'active_dimensions': ACTIVE_DIMENSIONS,
              'training_worlds': TRAINING_WORLDS, 'seed': SEED, 'draws': []}

    for draw in range(DRAWS):
        rng = random.Random(SEED + draw)
        weight_rng = np.random.default_rng(SEED + 1000 + draw)
        true_weights = np.zeros(dimensions)
        active = weight_rng.choice(dimensions, ACTIVE_DIMENSIONS, replace=False)
        true_weights[active] = weight_rng.uniform(.5, 4., ACTIVE_DIMENSIONS)

        worlds, attempts = [], 0
        while len(worlds) < TRAINING_WORLDS and attempts < TRAINING_WORLDS * 60:
            attempts += 1
            centre = centres[rng.randrange(len(centres))]
            distance = weighted_distance(latent, true_weights, centre)
            chosen = [harness.key_names[index]
                      for index in np.argsort(distance)[:KEYS_PER_WORLD]]
            members = [index for index in world_members(harness.catalog, harness.by_key, chosen)
                       if DENSITY[0] <= harness.density[index] <= DENSITY[1]]
            if len(members) >= MINIMUM_MEMBERS:
                worlds.append({'keys': chosen, 'members': members})
        observed = [sorted({harness.key_index[key] for key in harness.observed_keys(
            rng.sample(world['members'], min(PRIOR_SOLVED, len(world['members']))))})
            for world in worlds]

        row = {'draw': draw, 'worlds': len(worlds)}
        for form in ('product', 'squared_difference'):
            fitted = fit(latent, observed, random.Random(SEED + 50 + draw), form)
            row[form] = {
                'pearson': float(np.corrcoef(fitted, true_weights)[0, 1]),
                'spearman': float(spearmanr(fitted, true_weights).statistic),
                'active_recall_at_40': float(np.isin(
                    np.argsort(-fitted)[:ACTIVE_DIMENSIONS], active).mean()),
                'nonzero': int((fitted > 1e-6).sum())}
        result['draws'].append(row)
        print('draw {}: product r={:.3f} recall={:.2f} | squared r={:.3f} recall={:.2f}'
              .format(draw, row['product']['pearson'],
                      row['product']['active_recall_at_40'],
                      row['squared_difference']['pearson'],
                      row['squared_difference']['active_recall_at_40']))

    summary = {}
    for form in ('product', 'squared_difference'):
        summary[form] = {
            key: float(np.mean([row[form][key] for row in result['draws']]))
            for key in ('pearson', 'spearman', 'active_recall_at_40')}
    result['mean'] = summary
    result['verdict'] = {
        'squared_difference_better': bool(
            summary['squared_difference']['active_recall_at_40']
            > summary['product']['active_recall_at_40'] + .1),
        'worth_rebuilding': bool(summary['squared_difference']['active_recall_at_40'] >= .5)}
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    print('\nmean over {} draws:'.format(DRAWS))
    for form in ('product', 'squared_difference'):
        print('  {:<20s} pearson {:+.3f} spearman {:+.3f} active recall {:.2f}'.format(
            form, summary[form]['pearson'], summary[form]['spearman'],
            summary[form]['active_recall_at_40']))
    print('verdict:', result['verdict'])
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
