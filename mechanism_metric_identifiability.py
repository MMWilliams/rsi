"""Screen: at what descriptor width is the world's weighting recoverable at all?

Correcting the estimator's feature form barely moved weight recovery: 0.29 of
the active dimensions against 0.28 (`mechanism-metric-form-20260921.json`). So
the G4 arm was not failing because it was fitted to the wrong thing.

The suspect is identifiability. The catalog has 368 atoms and the descriptor
has 385 dimensions, so the distance structure of 368 points in 385 dimensions
does not determine a weighting over those dimensions: there are more unknowns
than points, and the whitened spectra are correlated on top of that. A metric
that cannot be recovered even in principle is not evidence about learning.

This sweeps the descriptor down to its leading principal components, which are
computed from the catalog alone and cost no experience, draws the world's
weighting in the reduced space, and reports how much of it 300 observed worlds
recover. It locates the width at which the question G4 asks becomes answerable,
and nothing else. No tasks, no arms, no transfer.
"""
from __future__ import annotations

import random
import time

import numpy as np
import psutil
from scipy.stats import spearmanr

from rsi.common import ROOT, write_json
from rsi.mechanism_space import DENSITY, world_members
from rsi.mechanism_worlds import Harness
from mechanism_atom_clustering import descriptors
from mechanism_metric_form import fit
from mechanism_metric_worlds import weighted_distance

OUT = ROOT / 'analysis/mechanism-metric-identifiability-20260921.json'
SEED = 616101
WIDTHS = (8, 16, 32, 64, 128, 385)
DRAWS = 3
ACTIVE_FRACTION = .25
TRAINING_WORLDS = 300
PRIOR_SOLVED = 64
KEYS_PER_WORLD = 14
MINIMUM_MEMBERS = 110
HELD_OUT_FAMILIES = ('popcount', 'xormod')


def reduce_to(latent, width):
    """Leading principal components of the atom descriptors, re-whitened.

    Computed from the catalog, so every atom has coordinates whether or not any
    world ever contained it."""
    if width >= latent.shape[1]:
        return latent
    centred = latent - latent.mean(axis=0, keepdims=True)
    _u, _s, vectors = np.linalg.svd(centred, full_matrices=False)
    reduced = centred @ vectors[:width].T
    return reduced / np.maximum(reduced.std(axis=0, keepdims=True), 1e-9)


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    full = descriptors(harness)
    families = np.array([key.split(':')[0] for key in harness.key_names])
    centres = [index for index in range(len(families))
               if families[index] not in HELD_OUT_FAMILIES]

    result = {'scope': 'descriptor width at which a world weighting is recoverable',
              'atoms': int(full.shape[0]), 'widths': list(WIDTHS), 'draws': DRAWS,
              'training_worlds': TRAINING_WORLDS, 'seed': SEED, 'by_width': {}}

    for width in WIDTHS:
        latent = reduce_to(full, width)
        dimensions = latent.shape[1]
        active_count = max(2, int(round(dimensions * ACTIVE_FRACTION)))
        rows = []
        for draw in range(DRAWS):
            rng = random.Random(SEED + 17 * draw + width)
            weight_rng = np.random.default_rng(SEED + 1000 * draw + width)
            true_weights = np.zeros(dimensions)
            active = weight_rng.choice(dimensions, active_count, replace=False)
            true_weights[active] = weight_rng.uniform(.5, 4., active_count)

            worlds, attempts = [], 0
            while len(worlds) < TRAINING_WORLDS and attempts < TRAINING_WORLDS * 60:
                attempts += 1
                centre = centres[rng.randrange(len(centres))]
                distance = weighted_distance(latent, true_weights, centre)
                chosen = [harness.key_names[index]
                          for index in np.argsort(distance)[:KEYS_PER_WORLD]]
                members = [index for index in
                           world_members(harness.catalog, harness.by_key, chosen)
                           if DENSITY[0] <= harness.density[index] <= DENSITY[1]]
                if len(members) >= MINIMUM_MEMBERS:
                    worlds.append(members)
            observed = [sorted({harness.key_index[key] for key in harness.observed_keys(
                rng.sample(members, min(PRIOR_SOLVED, len(members))))})
                for members in worlds]
            fitted = fit(latent, observed, random.Random(SEED + 99 + draw), 'squared_difference')
            rows.append({'pearson': float(np.corrcoef(fitted, true_weights)[0, 1]),
                         'spearman': float(spearmanr(fitted, true_weights).statistic),
                         'active_recall': float(np.isin(
                             np.argsort(-fitted)[:active_count], active).mean()),
                         'worlds': len(worlds)})
        block = {'dimensions': dimensions, 'active': active_count, 'draws': rows,
                 'mean': {key: float(np.mean([row[key] for row in rows]))
                          for key in ('pearson', 'spearman', 'active_recall')}}
        result['by_width'][str(width)] = block
        print('width {:>4d} ({} active): pearson {:+.3f} spearman {:+.3f} recall {:.2f}'
              .format(width, active_count, block['mean']['pearson'],
                      block['mean']['spearman'], block['mean']['active_recall']))

    best = max(WIDTHS, key=lambda w: result['by_width'][str(w)]['mean']['active_recall'])
    result['verdict'] = {
        'best_width': best,
        'best_recall': result['by_width'][str(best)]['mean']['active_recall'],
        'identifiable': bool(result['by_width'][str(best)]['mean']['active_recall'] >= .7)}
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)
    print('\nverdict:', result['verdict'])
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
