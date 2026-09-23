"""Freeze the 10-ridge query-gain predictor chosen on development banks."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from rsi.common import ROOT, write_json


SOURCE = ROOT / 'analysis/sharp-query-value-development.json'
OUT = ROOT / 'analysis/sharp-query-value-frozen.json'
RIDGE = 10.


def main():
    if OUT.exists():
        raise RuntimeError('frozen model already exists')
    raw = SOURCE.read_bytes()
    data = json.loads(raw)['tasks']
    x = np.asarray([row['features'] for row in data], dtype=float)
    y = np.asarray([row['gain'] for row in data], dtype=float)
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), .1)
    design = np.c_[(x-mean)/scale, np.ones(len(x))]
    penalty = np.diag([RIDGE] * x.shape[1] + [0.])
    weights = np.linalg.solve(design.T@design + penalty, design.T@y)
    frozen = {'source_sha256': hashlib.sha256(raw).hexdigest(),
              'source_tasks': len(data), 'source_positive_query_effects': int(sum(y > 0)),
              'ridge': RIDGE, 'mean': mean.tolist(), 'scale': scale.tolist(),
              'weights': weights.tolist(),
              'features': ['log_n','sharp_top_score','sharp_margin','sharp_top16_span',
                           'sharp_top16_mass','probe_entropy','probe_unique_outputs',
                           'probe_top_output_fraction','top_two_disagreement',
                           'sharp_context_different','sharp_context_output_disagreement',
                           'sharp_context_sharp_score_gap','context_score_gap',
                           'sharp_program_length','probe_index',
                           'stack','mutation','self_edit']}
    write_json(OUT, frozen)
    print(json.dumps({'status': 'frozen', 'source_tasks': len(data),
                      'source_positive_query_effects': int(sum(y > 0)),
                      'features': x.shape[1]}, indent=2))


if __name__ == '__main__':
    main()
