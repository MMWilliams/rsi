"""Screen: does behaviour alone recover the atom families a world is built from?

Three attempts to reach a family no training world contained have failed, and
they failed for one reason each time: what was learned was stated over atoms
training had seen. An identity affinity has no entry for a new atom; a
similarity metric fitted on training atoms was matched by the same descriptions
permuted; hedging bounds the loss without creating transfer.

There is one source of structure that covers atoms nobody has seen and costs no
experience at all: the catalog. Every atom's truth mask is there, and a
clustering of those masks is computable for the whole catalog before any world
is drawn. If such a clustering recovers the families, then the only thing that
needs to be learned from training worlds is a fact *about clusters* rather than
about atoms, and that fact applies to a cluster whose atoms were never in a
training world.

This screens the precondition and nothing else. Descriptors are the Fourier and
Walsh magnitude spectra used before, whitened; the clustering is k-means at
several k; the measure is how well clusters recover the nine families, reported
per family so that the two normally withheld can be read separately. No world,
no prior, no arm. If the recovery is poor for the withheld families, the
cluster-prior idea is dead before it is built, which is the point of a screen.
"""
from __future__ import annotations

import time

import numpy as np
import psutil
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.mechanism_space import ALPHABET_SIZE, mask_of
from rsi.mechanism_worlds import Harness

OUT = ROOT / 'analysis/mechanism-atom-clustering-20260921.json'
SEED = 613101
CLUSTERS = (6, 9, 12, 16, 24, 32)
WITHHELD = ('popcount', 'xormod')


def fwht(rows):
    rows = rows.astype(np.float64).copy()
    width = rows.shape[-1]
    step = 1
    while step < width:
        for start in range(0, width, step * 2):
            left = rows[:, start:start + step].copy()
            right = rows[:, start + step:start + 2 * step].copy()
            rows[:, start:start + step] = left + right
            rows[:, start + step:start + 2 * step] = left - right
        step *= 2
    return rows


def descriptors(harness):
    lookup = {atom[0]: atom[2] for atom in harness.catalog.atoms}
    rows = np.zeros((len(harness.key_names), ALPHABET_SIZE))
    for index, key in enumerate(harness.key_names):
        mask = mask_of(lookup[key])
        rows[index] = np.array([(mask >> bit) & 1 for bit in range(ALPHABET_SIZE)],
                               float) * 2 - 1
    fourier = np.abs(np.fft.rfft(rows, axis=1))
    walsh = np.abs(fwht(rows))
    block = np.concatenate([fourier / np.linalg.norm(fourier, axis=1, keepdims=True),
                            walsh / np.linalg.norm(walsh, axis=1, keepdims=True)], axis=1)
    centred = block - block.mean(axis=0, keepdims=True)
    return centred / np.maximum(centred.std(axis=0, keepdims=True), 1e-9)


def purity(labels, families, name):
    """Of the atoms of one family, the largest share landing in one cluster,
    and how much of that cluster is not this family."""
    mine = families == name
    counts = np.bincount(labels[mine], minlength=labels.max() + 1)
    home = int(np.argmax(counts))
    captured = counts[home] / mine.sum()
    contamination = 1. - counts[home] / max((labels == home).sum(), 1)
    return {'atoms': int(mine.sum()), 'home_cluster': home,
            'captured': float(captured), 'contamination': float(contamination),
            'clusters_touched': int((counts > 0).sum())}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    process = psutil.Process()
    wall, cpu = time.perf_counter(), time.process_time()

    harness = Harness()
    latent = descriptors(harness)
    families = np.array([key.split(':')[0] for key in harness.key_names])
    names = sorted(set(families))

    result = {'scope': 'can unsupervised behavioural clustering recover atom families',
              'atoms': len(families), 'families': {name: int((families == name).sum())
                                                   for name in names},
              'withheld': list(WITHHELD), 'seed': SEED, 'clusterings': {}}

    for k in CLUSTERS:
        labels = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(latent)
        block = {'adjusted_rand': float(adjusted_rand_score(families, labels)),
                 'per_family': {name: purity(labels, families, name) for name in names}}
        result['clusterings'][str(k)] = block
        print('k={:<3d} adjusted rand {:.3f} | '.format(k, block['adjusted_rand'])
              + ' '.join('{}:{:.2f}'.format(name[:4], block['per_family'][name]['captured'])
                         for name in names))

    best = max(CLUSTERS, key=lambda k: result['clusterings'][str(k)]['adjusted_rand'])
    result['best_k'] = best
    withheld_capture = [result['clusterings'][str(best)]['per_family'][name]['captured']
                        for name in WITHHELD]
    result['verdict'] = {
        'best_k': best,
        'adjusted_rand': result['clusterings'][str(best)]['adjusted_rand'],
        'withheld_captured': dict(zip(WITHHELD, withheld_capture)),
        'precondition_met': bool(min(withheld_capture) >= .5
                                 and result['clusterings'][str(best)]['adjusted_rand'] >= .3)}
    result['cost'] = {'wall_seconds': time.perf_counter() - wall,
                      'cpu_seconds': time.process_time() - cpu,
                      'peak_rss_mb': process.memory_info().rss / 1e6}
    write_json(OUT, result)

    print('\nbest k={} adjusted rand {:.3f}'.format(best, result['verdict']['adjusted_rand']))
    for name in names:
        row = result['clusterings'][str(best)]['per_family'][name]
        flag = ' (withheld)' if name in WITHHELD else ''
        print('  {:<10s} {:3d} atoms, {:.2f} captured into cluster {:2d}, '
              '{:.2f} of it foreign, {} clusters touched{}'.format(
                  name, row['atoms'], row['captured'], row['home_cluster'],
                  row['contamination'], row['clusters_touched'], flag))
    print('precondition met:', result['verdict']['precondition_met'])
    print('cost: {wall_seconds:.1f}s wall, {cpu_seconds:.1f}s cpu, {peak_rss_mb:.0f} MB'
          .format(**result['cost']))


if __name__ == '__main__':
    main()
