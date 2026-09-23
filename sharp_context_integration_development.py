"""Development-only integration of sharp listwise and public-context scores."""
from __future__ import annotations

import json

import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from mixed_evaluator_transfer import choose


RUN = ROOT / 'runs/temperature-ranker-transfer-20260917'
OUT = ROOT / 'analysis/sharp-context-integration-development.json'
ALPHAS = (0., .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.)


def normalize(values):
    x = np.asarray(values, dtype=float)
    return (x - x.mean()) / max(x.std(), 1e-6)


def main():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((RUN / 'frozen_decisions.json').read_text(encoding='utf-8'))
    records = []
    for task, record in zip(tasks, decisions):
        rows = pools[task['id']]
        labels = [bool(evaluate_program(row['program'], task['hidden'][8:]))
                  for row in rows]
        sharp = normalize(record['scores']['temp_0.25_120'])
        blend = normalize(record['scores']['blend'])
        selected = {str(alpha): choose(alpha*sharp + (1-alpha)*blend, rows)
                    for alpha in ALPHAS}
        records.append({'id': task['id'], 'seed': task['seed'], 'family': task['family'],
                        'sharp': labels[record['selected']['temp_0.25_120']],
                        'context': labels[record['selected']['blend']],
                        'correct': {name: labels[index] for name, index in selected.items()}})
    def aggregate(group):
        return {str(alpha): sum(row['correct'][str(alpha)] for row in group)
                for alpha in ALPHAS}
    seeds = sorted({row['seed'] for row in records})
    fold_scores = {}
    for seed in seeds:
        train = [row for row in records if row['seed'] != seed]
        test = [row for row in records if row['seed'] == seed]
        alpha = max(ALPHAS, key=lambda a: (sum(row['correct'][str(a)] for row in train), a))
        fold_scores[str(seed)] = {'chosen_alpha': alpha,
                                  'correct': sum(row['correct'][str(alpha)] for row in test),
                                  'sharp': sum(row['sharp'] for row in test)}
    summary = {'scope': 'development only; target labels inspected',
               'tasks': len(records), 'sharp': sum(row['sharp'] for row in records),
               'context': sum(row['context'] for row in records),
               'oracle_union': sum(row['sharp'] or row['context'] for row in records),
               'overall': aggregate(records),
               'by_family': {family: aggregate([row for row in records
                                                if row['family'] == family])
                             for family in sorted({row['family'] for row in records})},
               'leave_one_bank_out': fold_scores,
               'leave_one_bank_out_total': sum(row['correct'] for row in fold_scores.values())}
    write_json(OUT, {'summary': summary, 'tasks': records})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
