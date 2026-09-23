"""Development-only standardized score blends of listwise and context evaluators."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from mixed_evaluator_transfer import choose


RUN = ROOT / 'runs/listwise-evaluator-transfer-20260917'
OUT = ROOT / 'analysis/listwise-blend-development.json'
ALPHAS = (0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1)


def standardize(values):
    scores = np.asarray(values, dtype=float)
    return (scores - scores.mean()) / max(scores.std(), 1e-6)


def main():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((RUN / 'frozen_decisions.json').read_text(encoding='utf-8'))
    rows = []
    for task, record in zip(tasks, decisions):
        candidates = pools[task['id']]
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in candidates]
        listwise = standardize(record['scores']['listwise_120'])
        blend = standardize(record['scores']['blend'])
        selected = {str(alpha): choose(alpha * listwise + (1-alpha) * blend,
                                       candidates) for alpha in ALPHAS}
        rows.append({'id': task['id'], 'seed': task['seed'], 'family': task['family'],
                     'correct': {alpha: labels[index] for alpha, index in selected.items()}})
    def aggregate(group):
        return {str(alpha): sum(row['correct'][str(alpha)] for row in group)
                for alpha in ALPHAS}
    summary = {'scope': 'development only; previously inspected target labels',
               'tasks': len(rows), 'overall': aggregate(rows),
               'by_family': {family: aggregate([row for row in rows
                                                if row['family'] == family])
                             for family in sorted({row['family'] for row in rows})},
               'by_bank': {str(seed): aggregate([row for row in rows if row['seed'] == seed])
                           for seed in sorted({row['seed'] for row in rows})}}
    write_json(OUT, {'summary': summary, 'tasks': rows})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
