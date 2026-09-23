"""Opened-source controls for the fresh stacked-ranker feedback test."""
from __future__ import annotations

import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from candidate_reranker_transfer import model_for
from candidate_stacking_development import SOURCE, ADDED, panel
from dual_specialist_seed_evaluator import load_models


DEST = ROOT / 'analysis/candidate-stacking-controls-20260918'


def main():
    if DEST.exists():
        raise RuntimeError('control models already exist')
    paths = SOURCE + (ADDED,)
    assert all(json.loads((p / 'audit.json').read_text())['passed']
               for p in paths)
    specialist = load_models()
    first, second, added = [panel(p, specialist) for p in paths]
    xearly = np.r_[first['stack'], second['stack']]
    yearly = np.r_[first['y'], second['y']]
    rng = np.random.default_rng(905099)
    scrambled = added['y'].copy()
    for row in added['rows']:
        a, b = row['start'], row['start'] + row['count']
        scrambled[a:b] = rng.permutation(scrambled[a:b])
    source_groups = []
    for data in (first, second):
        for row in data['rows']:
            a, b = row['start'], row['start'] + row['count']
            source_groups.append((data['stack'][a:b], data['y'][a:b]))
    dup_ids = rng.choice(len(source_groups), len(added['rows']), replace=True)
    xdup = np.concatenate([source_groups[i][0] for i in dup_ids])
    ydup = np.concatenate([source_groups[i][1] for i in dup_ids])
    models = {
        'scrambled': model_for(15).fit(
            np.r_[xearly, added['stack']], np.r_[yearly, scrambled]),
        'duplicate': model_for(15).fit(
            np.r_[xearly, xdup], np.r_[yearly, ydup])}
    DEST.mkdir(parents=True)
    for name, model in models.items():
        joblib.dump(model, DEST / f'{name}.joblib', compress=3)
    stats = {'scope': 'opened-source controls only',
             'early_tasks': len(first['rows']) + len(second['rows']),
             'added_tasks': len(added['rows']),
             'early_labels': len(yearly),
             'added_labels': len(added['y']),
             'duplicate_added_labels': len(ydup),
             'added_positive': int(added['y'].sum()),
             'scrambled_positive': int(scrambled.sum()),
             'duplicate_positive': int(ydup.sum())}
    write_json(DEST / 'stats.json', stats)
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
