"""Opened screen: does the depth finding compose with region routing?

`construction_space_development.py` found that labelling 25 candidates on every
source task beats labelling 100 on a third of them for a single global reranker.
The six region specialists were built at depth 100. This screen builds them at
25, 50 and 100 and scores every train depth at every test width, so that a
better model can be told apart from a narrower shortlist. The same 3x3 is run
for the global uniform construction from the saved models.

If region@25 beats region@100 by a margin outside training noise, an improver
that has separately observed "region beats global" and "shallow beats deep" has
an unobserved construction worth proposing. Development evidence only.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from region_specialist_repayment_development import (
    SOURCE, TARGET, REGIONS, load_cache)


OUT = ROOT / 'analysis/region-depth-development-20260920.json'
MODELS = ROOT / 'analysis/region-depth-models-20260920'
GLOBAL = ROOT / 'analysis/construction-space-models-20260920'
DEPTHS = (25, 50, 100)


def region_rows(region, depth):
    xs = []
    ys = []
    tasks = 0
    for name in SOURCE:
        x, meta = load_cache(name)
        for task in meta:
            if task['region'] != region:
                continue
            take = min(depth, task['count'])
            xs.append(x[task['start']:task['start'] + take])
            ys.append(np.asarray(task['labels'][:take], np.int8))
            tasks += 1
    return np.concatenate(xs), np.concatenate(ys), tasks


def score(pick_for, width):
    """pick_for(meta_task, window_probabilities) -> label. Returns per-panel
    paired gain over E0 with the pick restricted to the top `width`."""
    out = {}
    for name in TARGET:
        x, meta = load_cache(name)
        banks = defaultdict(lambda: [0, 0])
        for task in meta:
            take = min(width, task['count'])
            label = pick_for(task, x[task['start']:task['start'] + take],
                             task['labels'][:take])
            bank = banks[task['seed']]
            bank[0] += label
            bank[1] += task['e0_label']
        diffs = [a - b for a, b in banks.values()]
        out[name] = {'correct': sum(a for a, _ in banks.values()),
                     'e0': sum(b for _, b in banks.values()),
                     'gain': sum(diffs),
                     'positive_banks': sum(d > 0 for d in diffs),
                     'losing_banks': sum(d < 0 for d in diffs),
                     'interval': interval(diffs)}
    return out


def argmax_label(p, labels):
    return labels[max(range(len(labels)), key=lambda i: (float(p[i]), -i))]


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development exists')
    MODELS.mkdir(parents=True)
    regional = {}
    labels_by_depth = {}
    for depth in DEPTHS:
        models = {}
        spent = 0
        for region in REGIONS:
            x, y, _ = region_rows(region, depth)
            models[region] = model_for(15).fit(x, y)
            spent += len(y)
            joblib.dump(models[region], MODELS / f'{region}@{depth}.joblib',
                        compress=3)
        labels_by_depth[depth] = spent
        for width in DEPTHS:
            def pick(task, window, labels, models=models):
                model = models[task['region']]
                return argmax_label(model.predict_proba(window)[:, 1], labels)
            regional[f'train{depth}_test{width}'] = score(pick, width)
            total = sum(v['gain'] for v in
                        regional[f'train{depth}_test{width}'].values())
            print(f'region train={depth:3d} test={width:3d} gain={total:+4d}',
                  flush=True)

    global_grid = {}
    for depth in DEPTHS:
        model = joblib.load(GLOBAL / f'uniform@{depth}.joblib')
        for width in DEPTHS:
            def pick(task, window, labels, model=model):
                return argmax_label(model.predict_proba(window)[:, 1], labels)
            global_grid[f'train{depth}_test{width}'] = score(pick, width)
            total = sum(v['gain'] for v in
                        global_grid[f'train{depth}_test{width}'].values())
            print(f'global train={depth:3d} test={width:3d} gain={total:+4d}',
                  flush=True)

    def totals(grid):
        return {key: sum(v['gain'] for v in value.values())
                for key, value in grid.items()}

    result = {
        'scope': 'opened development only; no frozen policy',
        'question': 'does shallow labelling compose with region routing, and '
                    'is the depth effect a better model or a narrower shortlist',
        'source_panels': list(SOURCE), 'target_panels': list(TARGET),
        'region_labels_spent_by_depth': labels_by_depth,
        'regional': regional, 'global_uniform': global_grid,
        'regional_totals': totals(regional),
        'global_totals': totals(global_grid),
        'limits': ['Opened panels; development evidence.',
                   'Test widths are prefixes of one cached top-100 order; '
                   'coverage is unchanged.',
                   'Region models are trained on 192 source tasks each; the '
                   'global model on all 1,152, so label totals differ by depth '
                   'and are reported.']}
    write_json(OUT, result)
    print(json.dumps({'region_labels_spent_by_depth': labels_by_depth,
                      'regional_totals': result['regional_totals'],
                      'global_totals': result['global_totals']}, indent=2))


if __name__ == '__main__':
    main()
