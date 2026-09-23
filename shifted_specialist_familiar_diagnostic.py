"""Opened familiar-AST transfer check for the shifted survivor specialist."""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0, load_panel
from shifted_survivor_growth_development import rows_for


SOURCE_MODELS = ROOT / 'runs/shifted-survivor-evaluator-transfer-20260918'
TARGET = ROOT / 'runs/combined-ranker-query-transfer-20260918'
OUT = ROOT / 'analysis/shifted-specialist-familiar-diagnostic-20260918.json'
NAMES = ('e0', 'a_plain100', 'ab_plain100')


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    assert json.loads((SOURCE_MODELS / 'audit.json').read_text())['passed']
    tasks, base, wide, matrices, records = load_panel(TARGET)
    e0 = joblib.load(E0)
    models = {name: joblib.load(SOURCE_MODELS / f'{name}.joblib')
              for name in NAMES[1:]}
    grouped = defaultdict(list)
    count = 0
    predictions = 0
    for task, rec in zip(tasks, records):
        if task['family'] != 'ast_transition':
            continue
        key = task['id']
        pool = wide.get(key, base[key])
        rows, surviving = rows_for(task, pool, rec, matrices[key], e0)
        choices = {'e0': next(i for i in rec['orders']['e0'] if i in surviving)}
        for name, model in models.items():
            if not rows:
                choices[name] = choices['e0']
                continue
            x = np.asarray([row['plain'] for row in rows], np.float32)
            p = model.predict_proba(x)[:, 1]
            predictions += len(rows)
            choices[name] = rows[max(range(len(rows)),
                                    key=lambda i: (float(p[i]), -i))]['index']
        outcome = {name: int(bool(evaluate_program(pool[index]['program'],
                   task['hidden'][8:]))) for name, index in choices.items()}
        grouped[task['seed']].append(outcome)
        count += 1
    assert count == 96 and len(grouped) == 12
    banks = [{'seed': seed, **{name: sum(row[name] for row in group)
                               for name in NAMES}}
             for seed, group in sorted(grouped.items())]
    totals = {name: sum(bank[name] for bank in banks) for name in NAMES}
    comparisons = {}
    for name in NAMES[1:]:
        diffs = [bank[name] - bank['e0'] for bank in banks]
        comparisons[name] = {'gain': sum(diffs),
                             'positive_banks': sum(v > 0 for v in diffs),
                             'losing_banks': sum(v < 0 for v in diffs),
                             'interval': interval(diffs)}
    result = {'scope': 'opened familiar AST diagnostic, one query per AST task',
              'ast_tasks': count, 'logical_output_calls': count,
              'new_model_predictions': predictions,
              'totals': totals, 'comparisons': comparisons, 'banks': banks}
    write_json(OUT, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'banks'}, indent=2))


if __name__ == '__main__':
    main()
