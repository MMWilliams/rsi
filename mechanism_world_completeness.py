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
from mechanism_self_simulation import simulate

SEEDS = (643101, 644101, 645101)
RULES = (('all', 10 ** 9), ('n<=1', 1))
COUNTS = (6, 7, 8)
TRAIN = 1280
OUT = ROOT / 'analysis/mechanism-world-completeness-20261005.json'


def rate(half):
    present, found = np.array(half['present']), np.array(half['found'])
    return np.where(present >= 10, found / np.maximum(present, 1), np.nan)


def pearson(a, b):
    ok = ~np.isnan(a) & ~np.isnan(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]), float(np.abs(a[ok] - b[ok]).mean()), int(ok.sum())


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    warnings.filterwarnings('ignore', message='Graph is not fully connected')
    harness = Harness()
    simulator = Simulator(harness)
    keys = len(harness.key_names)
    families = sorted(harness.by_family)
    family_of = np.array([families.index(k.split(':')[0]) for k in harness.key_names])
    bench = json.loads((ROOT / 'analysis/mechanism-world-benchmark-20261005.json').read_text())
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
            imagined, _present = simulate(harness, simulator, model, seed, 7)
            imagined = np.where(_present >= 10, imagined, np.nan)
            block[name] = {'groups': best, 'atoms_grouped': int(grouped.sum()),
                           'ari': float(adjusted_rand_score(family_of[grouped],
                                                            model.labels[grouped])),
                           'discovery_fidelity': pearson(imagined, target)}
            print(seed, name, block[name], 'ceiling', block['ceiling'], flush=True)
        result[str(seed)] = block
    write_json(OUT, result)


if __name__ == '__main__':
    sys.exit(main())
