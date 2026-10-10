"""Is the world model complete? Scored by what it makes the agent do.

For each dev seed and each evidence rule (every pick, or only picks where the
agent found at most `n` consistent hypotheses, which it can tell are reliable:
0.90 correct at n=1 against 0.26 above 16), fit the world model with restarts,
group count by held-out likelihood. Then the agent imagines worlds from it,
lives them with its own policy and tie-break, and its measured discovery rate
per atom is compared with the benchmark (`mechanism_world_benchmark.py`: the
same agent in the true generator under test conditions). Ceiling: the
benchmark's two independent halves against each other. Also reported: groups
against families. Ground truth scores only; the agent never sees it.
"""
from __future__ import annotations

import json
import os
import sys
import warnings

import numpy as np
from sklearn.metrics import adjusted_rand_score

from rsi.common import ROOT, write_json
from rsi.growth_coach import Simulator
from rsi.mechanism_worlds import Harness
from rsi.self_world_model import _matrix, fit_restarts
import mechanism_earned_confirmation as conf
from mechanism_earn_traced import load
from mechanism_self_simulation import IMAGINED, simulate

SEEDS = (643101, 644101, 645101)
RULES = (('all', 10 ** 9), ('n<=1', 1))
COUNTS = (6, 7, 8)
TRAIN = 1280
OUT = ROOT / 'analysis/mechanism-world-completeness-20261010.json'
BENCH = ROOT / 'analysis/mechanism-world-benchmark-trained-20261010.json'
conf.WORKERS = int(os.environ.get('RSI_WORKERS', conf.WORKERS))   # each worker commits ~1.6 GB


def rate(half):
    present, found = np.array(half['present']), np.array(half['found'])
    return np.where(present >= 10, found / np.maximum(present, 1), np.nan)


def pearson(a, b, ok=None):
    ok = ~np.isnan(a) & ~np.isnan(b) & (True if ok is None else ok)
    if ok.sum() < 6:
        return None
    return float(np.corrcoef(a[ok], b[ok])[0, 1]), float(np.abs(a[ok] - b[ok]).mean()), int(ok.sum())


def per_family(imagined, target, other, family_of, families):
    """Fidelity and ceiling on the same atoms, family by family: within most
    families atoms barely differ in how often they are found, so the benchmark's
    own split-half agreement there is the most any model can reach."""
    ok = ~np.isnan(imagined) & ~np.isnan(target) & ~np.isnan(other)
    out = {}
    for f, name in enumerate(families):
        sel = ok & (family_of == f)
        if sel.sum() >= 6:
            out[name] = {'fidelity': pearson(imagined, target, sel), 'ceiling': pearson(other, target, sel)}
    out['all'] = {'fidelity': pearson(imagined, target, ok), 'ceiling': pearson(other, target, ok)}
    return out


def presence(imagined_present, bench, family_of, families, imagined_worlds):
    """Atoms of each family per world, imagined against true."""
    true = np.array(bench[0]['present']) + np.array(bench[1]['present'])
    true_worlds = true.sum() / conf.KEYS_PER_WORLD
    return {name: [float(imagined_present[family_of == f].sum() / imagined_worlds),
                   float(true[family_of == f].sum() / true_worlds)]
            for f, name in enumerate(families)}


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    families = sorted(harness.by_family)
    family_of = np.array([families.index(k.split(':')[0]) for k in harness.key_names])
    bench = {seed: block['halves'] for seed, block in json.loads(BENCH.read_text()).items()}
    result = {}
    for seed in SEEDS:
        earning = load(seed)
        target, other = rate(bench[str(seed)][0]), rate(bench[str(seed)][1])
        block = {'ceiling': pearson(target, other)}
        for name, limit in RULES:
            sets = [sorted({int(k) for pick, _hit, n, _s in world if pick >= 0 and n <= limit
                            for k in simulator.row_keys[pick]}) for world in earning]
            held = _matrix(sets[TRAIN:], keys)
            fits = {g: fit_restarts(sets[:TRAIN], keys, g, restarts=4) for g in COUNTS}
            scores = {g: m.log_likelihood(held) for g, (m, _t) in fits.items()}
            best = max(scores, key=scores.get)
            model = fits[best][0]
            grouped = model.labels >= 0
            imagined, imagined_present = simulate(harness, simulator, model, seed, 7)
            imagined = np.where(imagined_present >= 10, imagined, np.nan)
            block[name] = {'groups': best, 'held_out_ll': {str(g): float(s) for g, s in scores.items()},
                           'atoms_grouped': int(grouped.sum()),
                           'ari': float(adjusted_rand_score(family_of[grouped],
                                                            model.labels[grouped])),
                           'discovery_fidelity': pearson(imagined, target),
                           'by_family': per_family(imagined, target, other, family_of, families),
                           'atoms_per_world': presence(imagined_present, bench[str(seed)],
                                                       family_of, families, IMAGINED)}
            print(seed, name, json.dumps(block[name]), 'ceiling', block['ceiling'], flush=True)
        result[str(seed)] = block
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
