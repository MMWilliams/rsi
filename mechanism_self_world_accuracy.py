"""Accuracy of the joint world and self model against ground truth.

On the three opened development seeds, from the blind loop's journaled earning
at 4096: fit `rsi.self_world_model` on 1,280 training worlds' earned sets (raw,
and atoms in at least 3 picks), then score it against what the agent never sees.

world model   adjusted Rand of its groups against the families, atoms grouped;
              on 320 held-out worlds, P(atom in world | earned set) against the
              world's true atoms: AUC, Brier, and recall at the world's size,
              next to the earned set itself and the champion's pair prior.
self model    per-atom discovery rate r against the true rate (share of worlds
              holding the atom in which it was earned), Pearson and mean
              absolute error; import rate f likewise.
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
from sklearn.metrics import adjusted_rand_score, roc_auc_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix, select
import mechanism_earned_confirmation as conf
from mechanism_earned_trust_screen import earning_of

SEEDS = (643101, 644101, 645101)
TRAIN = 1280
OUT = ROOT / 'analysis/mechanism-self-world-accuracy-20261005.json'


def scores(belief, truth):
    flat_b, flat_t = belief.ravel(), truth.ravel()
    top = np.argsort(-belief, axis=1)[:, :14]
    recall = np.take_along_axis(truth, top, axis=1).sum(1) / truth.sum(1)
    return {'auc': float(roc_auc_score(flat_t, flat_b)),
            'brier': float(np.mean((flat_b - flat_t) ** 2)),
            'recall_at_14': float(recall.mean())}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    families = sorted(harness.by_family)
    family_of = np.array([families.index(k.split(':')[0]) for k in harness.key_names])
    result = {}
    for seed in SEEDS:
        _rng, _groups, training, _s, streams, _handed, _prior, _n = conf.setup(harness, seed)
        if seed == 645101:
            cache = ROOT / 'runs/mechanism-earned-confirmation2-dev-645101/earning-dev.json'
            earning = json.loads(cache.read_text())['earning']
        else:
            earning = earning_of(seed, streams)
        truth = _matrix([[harness.key_index[k] for k in w['keys']] for w in training], keys)
        result[str(seed)] = {}
        for m in (1, 3):
            sets = [conf.earned_set(d, simulator.row_keys, m) for d in earning]
            earned = _matrix(sets, keys)
            model, count, _ll, trace = select(sets[:TRAIN], keys)
            held_e, held_t = earned[TRAIN:], truth[TRAIN:]
            belief = model.membership(held_e)
            # pair prior baseline: co-occurrence with the world's earned atoms
            co = earned[:TRAIN].T @ earned[:TRAIN]
            freq = np.maximum(np.diag(co), 1)
            pair = (held_e @ (co / freq[:, None])) / np.maximum(held_e.sum(1, keepdims=True), 1)
            pair = np.where(held_e > 0, 1., np.clip(pair, 0, 1))
            has = truth[:TRAIN].sum(0)
            true_r = np.where(has > 0, (earned[:TRAIN] * truth[:TRAIN]).sum(0) / np.maximum(has, 1),
                              np.nan)
            absent = (1 - truth[:TRAIN]).sum(0)
            true_f = (earned[:TRAIN] * (1 - truth[:TRAIN])).sum(0) / np.maximum(absent, 1)
            ok = ~np.isnan(true_r) & model.seen
            grouped = model.labels >= 0
            block = {
                'groups': int(count), 'em_iterations': len(trace),
                'world': {'ari_vs_families': float(adjusted_rand_score(family_of[grouped],
                                                                        model.labels[grouped])),
                          'atoms_grouped': int(grouped.sum()),
                          'model': scores(belief, held_t),
                          'earned_set_only': scores(held_e, held_t),
                          'pair_prior': scores(pair, held_t)},
                'self': {'r_pearson': float(np.corrcoef(model.r[ok], true_r[ok])[0, 1]),
                         'r_mae': float(np.abs(model.r[ok] - true_r[ok]).mean()),
                         'f_pearson': float(np.corrcoef(model.f[ok], true_f[ok])[0, 1]),
                         'f_mae': float(np.abs(model.f[ok] - true_f[ok]).mean()),
                         'true_r_mean': float(np.nanmean(true_r[ok]))}}
            result[str(seed)][f'm{m}'] = block
            print(seed, f'm{m}', json.dumps(block), flush=True)
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
