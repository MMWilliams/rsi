"""Opened matched-width control for shifted-trained top-100 survivor ranking."""
from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0, SOURCE
from shifted_survivor_growth_development import rows_for, source_arrays


TARGET = ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918'
OUT = ROOT / 'analysis/familiar-top100-survivor-diagnostic-20260918.json'
MODEL = ROOT / 'analysis/familiar-top100-survivor-model-20260918.joblib'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists() or MODEL.exists():
        raise RuntimeError('diagnostic output exists')
    assert json.loads((TARGET / 'audit.json').read_text())['passed']
    e0 = joblib.load(E0)
    sources = [source_arrays(path, e0) for path in SOURCE]
    x = np.concatenate([source['plain'] for source in sources])
    y = np.concatenate([source['labels'] for source in sources])
    model = model_for(15).fit(x, y)
    joblib.dump(model, MODEL, compress=3)
    tasks = json.loads((TARGET / 'sealed_bank.json').read_text())
    pools = json.loads((TARGET / 'ast_wide_pools.json').read_text())
    matrices = json.loads((TARGET / 'predicted_probe_outputs.json').read_text())
    records = json.loads((TARGET / 'frozen_records.json').read_text())
    allocations = json.loads((TARGET / 'frozen_allocations.json').read_text())
    results = json.loads((TARGET / 'results.json').read_text())['tasks']
    by_seed = {}
    predictions = 0
    for task, rec, result in zip(tasks, records, results):
        key = task['id']
        assert key == rec['id'] == result['id']
        pool = pools[key]
        rows, surviving = rows_for(task, pool, rec, matrices[key], e0)
        if rows:
            z = np.asarray([row['plain'] for row in rows], np.float32)
            p = model.predict_proba(z)[:, 1]
            predictions += len(rows)
            index = rows[max(range(len(rows)), key=lambda i: (float(p[i]), -i))]['index']
        else:
            index = rec['top100_choices']['e0']
        assert index in surviving
        one = int(bool(evaluate_program(pool[index]['program'], task['hidden'][8:])))
        by_seed.setdefault(str(task['seed']), []).append({
            'id': key, 'zero': result['zero'], 'one': one,
            'e0': result['one']['e0'],
            'a_plain100': result['one']['a_plain100'],
            'ab_plain100': result['one']['ab_plain100']})
    banks = []
    for seed, group in sorted(by_seed.items()):
        selected = set(allocations[seed])
        bank = {'seed': int(seed)}
        for name in ('one', 'e0', 'a_plain100', 'ab_plain100'):
            bank[name + '_one_each'] = sum(r[name] for r in group)
            bank[name + '_budgeted'] = sum(r[name] if r['id'] in selected else r['zero']
                                          for r in group)
        banks.append(bank)
    totals = {name: sum(b[name] for b in banks) for name in banks[0] if name != 'seed'}
    comparisons = {}
    for baseline in ('e0', 'a_plain100', 'ab_plain100'):
        comparisons[baseline] = {}
        for field in ('one_each', 'budgeted'):
            diffs = [b['one_' + field] - b[baseline + '_' + field] for b in banks]
            comparisons[baseline][field] = {
                'gain': sum(diffs), 'positive_banks': sum(v > 0 for v in diffs),
                'losing_banks': sum(v < 0 for v in diffs),
                'interval': interval(diffs)}
    report = {'scope': 'opened diagnostic after protected transfer',
              'source_tasks': sum(source['tasks'] for source in sources),
              'source_verified_survivor_labels': len(y),
              'source_positive_labels': int(y.sum()),
              'model_sha256': sha(MODEL),
              'target_tasks': len(tasks), 'target_model_predictions': predictions,
              'totals': totals, 'comparisons': comparisons, 'banks': banks}
    write_json(OUT, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'banks'}, indent=2))


if __name__ == '__main__':
    main()
