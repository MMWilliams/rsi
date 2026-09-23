"""Complete the global half of the train-depth by test-width grid.

`region_depth_development.py` finished its regional grid and then died on commit
exhaustion partway through the global arms, leaving only train25/test25. The
cost-matched claim in CONSTRUCTION-SPACE-DEVELOPMENT compares global uniform@25
against region@25 at test width 100, so the missing cells matter. This reuses
the models screen 1 already saved and loads each panel once.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from region_specialist_repayment_development import TARGET, load_cache


OUT = ROOT / 'analysis/global-depth-completion-20260920.json'
GLOBAL = ROOT / 'analysis/construction-space-models-20260920'
DEPTHS = (25, 50, 100)


def main():
    if OUT.exists():
        raise RuntimeError('development exists')
    panels = {name: load_cache(name) for name in TARGET}
    models = {depth: joblib.load(GLOBAL / f'uniform@{depth}.joblib')
              for depth in DEPTHS}
    grid = {}
    for depth, model in models.items():
        cached = {name: model.predict_proba(x)[:, 1]
                  for name, (x, _) in panels.items()}
        for width in DEPTHS:
            per_panel = {}
            for name, (_, meta) in panels.items():
                p = cached[name]
                banks = defaultdict(lambda: [0, 0])
                for task in meta:
                    take = min(width, task['count'])
                    window = p[task['start']:task['start'] + take]
                    labels = task['labels'][:take]
                    bank = banks[task['seed']]
                    bank[0] += labels[max(range(take),
                                          key=lambda i: (float(window[i]), -i))]
                    bank[1] += task['e0_label']
                diffs = [a - b for a, b in banks.values()]
                per_panel[name] = {'correct': sum(a for a, _ in banks.values()),
                                   'e0': sum(b for _, b in banks.values()),
                                   'gain': sum(diffs),
                                   'positive_banks': sum(d > 0 for d in diffs),
                                   'losing_banks': sum(d < 0 for d in diffs),
                                   'interval': interval(diffs)}
            key = f'train{depth}_test{width}'
            grid[key] = per_panel
            print(f'global train={depth:3d} test={width:3d} '
                  f'gain={sum(v["gain"] for v in per_panel.values()):+4d}',
                  flush=True)
    totals = {key: sum(v['gain'] for v in value.values())
              for key, value in grid.items()}
    write_json(OUT, {
        'scope': 'opened development only; completes the global grid',
        'target_panels': list(TARGET), 'global_uniform': grid,
        'global_totals': totals,
        'limits': ['Opened panels; development evidence.',
                   'Models come from the matched 40,000-label screen, so train '
                   'depth also changes how many source tasks were labelled.']})
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
