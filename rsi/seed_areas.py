"""Further areas for the seed, with the same interface as `rsi.seed.Area`.

MetricArea: worlds whose latent structure is behavioural rather than
syntactic (`mechanism_metric_worlds.py`). A sparse weighting over descriptor
dimensions is drawn once and shown to nobody; a world is a centre atom and the
fourteen atoms nearest it under that weighting. Family names play no part in
the structure, so nothing the seed learned about families applies here except
its language and whatever prior and model it fits from its own experience.
"""
from __future__ import annotations

import numpy as np

from .mechanism_space import ALPHABET_SIZE, DENSITY, mask_of, world_members
from .seed import Area, KEYS_PER_WORLD, STREAM


def _fwht(rows):
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
    """Each atom's behaviour as normalised Fourier and Walsh spectra of its
    truth mask (as `mechanism_atom_clustering.descriptors`)."""
    lookup = {atom[0]: atom[2] for atom in harness.catalog.atoms}
    rows = np.zeros((len(harness.key_names), ALPHABET_SIZE))
    for index, key in enumerate(harness.key_names):
        mask = mask_of(lookup[key])
        rows[index] = np.array([(mask >> bit) & 1 for bit in range(ALPHABET_SIZE)], float) * 2 - 1
    fourier = np.abs(np.fft.rfft(rows, axis=1))
    walsh = np.abs(_fwht(rows))
    block = np.concatenate([fourier / np.linalg.norm(fourier, axis=1, keepdims=True),
                            walsh / np.linalg.norm(walsh, axis=1, keepdims=True)], axis=1)
    centred = block - block.mean(axis=0, keepdims=True)
    return centred / np.maximum(centred.std(axis=0, keepdims=True), 1e-9)


class MetricArea(Area):
    pools = ('seen_centre', 'unfamiliar_centre')

    def __init__(self, seed, weight_seed=777001, active=40, unfamiliar=('popcount', 'xormod'),
                 minimum=110, unfamiliar_share=.25):
        super().__init__(seed)
        self.name = f'metric{weight_seed}'
        self.latent = descriptors(self.full)
        rng = np.random.default_rng(weight_seed)
        self.weights = np.zeros(self.latent.shape[1])
        chosen = rng.choice(self.latent.shape[1], active, replace=False)
        self.weights[chosen] = rng.uniform(.5, 4., active)
        families = [k.split(':')[0] for k in self.full.key_names]
        self.centres = {'seen_centre': [i for i, f in enumerate(families) if f not in unfamiliar],
                        'unfamiliar_centre': [i for i, f in enumerate(families) if f in unfamiliar]}
        self.minimum = minimum
        self.unfamiliar_share = unfamiliar_share

    def _members(self, centre):
        distance = (((self.latent - self.latent[centre]) ** 2) * self.weights).sum(axis=1)
        chosen = [self.full.key_names[i] for i in np.argsort(distance)[:KEYS_PER_WORLD]]
        members = world_members(self.full.catalog, self.full.by_key, chosen)
        members = [i for i in members if DENSITY[0] <= self.full.density[i] <= DENSITY[1]]
        return members if len(members) >= self.minimum else None

    def _worlds(self, pool, count, rng):
        centres, out = self.centres[pool], []
        while len(out) < count:
            members = self._members(centres[rng.randrange(len(centres))])
            if members is None:
                continue
            members = list(members)
            rng.shuffle(members)
            out.append({'stream': members[:STREAM]})
        return out

    def life_draw(self, count, rng):
        unfamiliar = round(count * self.unfamiliar_share)
        return (self.draw('seen_centre', count - unfamiliar, rng)
                + self.draw('unfamiliar_centre', unfamiliar, rng))
