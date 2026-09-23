"""Development-only next edit proposals below temperature 0.25."""
from __future__ import annotations

import json
import time

import numpy as np
import torch

from rsi.common import ROOT, write_json
from listwise_evaluator_development import pack
from temperature_ranker_development import train, score, targets
from mixed_probe_diagnostic import bool_safe_structure
import seed_growth


SOURCE = ROOT / 'analysis/mixed-evaluator-source.json'
OUT = ROOT / 'analysis/temperature-extension-development.json'
TEMPERATURES = (.0625, .125, .1875, .25)


def main():
    seed_growth.structure = bool_safe_structure
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    source = json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    x, _, _ = pack(source)
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), .05)
    start = time.perf_counter()
    target = targets()
    variants = {}
    for temperature in TEMPERATURES:
        model, snapshots = train(temperature, source, mean, scale, device)
        variants[str(temperature)] = {'target': score(model, mean, scale, target, device),
                                      'source': score(model, mean, scale, source, device),
                                      'weights': snapshots}
    summary = {'scope': 'development only; target bank already inspected',
               'source_candidate_labels': sum(row['n'] for row in source),
               'target_tasks': len(target), 'temperatures': TEMPERATURES,
               'target_correct': {key: sum(row['correct'] for row in value['target'])
                                  for key, value in variants.items()},
               'source_correct': {key: sum(row['correct'] for row in value['source'])
                                  for key, value in variants.items()},
               'by_family': {key: {family: sum(row['correct'] for row in value['target']
                                               if row['family'] == family)
                                   for family in sorted({row['family'] for row in target})}
                             for key, value in variants.items()},
               'wall_seconds': time.perf_counter() - start}
    write_json(OUT, {'summary': summary, 'normalization_mean': mean.tolist(),
                     'normalization_scale': scale.tolist(), 'variants': variants})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
