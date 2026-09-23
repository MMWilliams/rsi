"""Development-only learned value of one exact output query per task."""
from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from active_probe_diagnostic import program_output


RUN = ROOT / 'runs/temperature-ranker-transfer-20260917'
OUT = ROOT / 'analysis/sharp-query-value-development.json'
LAMBDAS = (.1, 1., 10., 100.)
BUDGET = 95
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')


def entropy(values):
    counts = Counter(values)
    n = len(values)
    return -sum((k/n)*math.log(k/n) for k in counts.values())


def features(task, record, rows):
    scores = np.asarray(record['scores']['temp_0.25_120'], dtype=float)
    blend = np.asarray(record['scores']['blend'], dtype=float)
    order = sorted(range(len(rows)), key=lambda i: (-scores[i],
                   len(rows[i]['program']), rows[i]['program']))
    top = order[:16]
    outputs = [[program_output(rows[i]['program'], pair[0])
                for pair in task['hidden'][:8]] for i in top]
    entropies = [entropy([out[j] for out in outputs]) for j in range(8)]
    probe = max(range(8), key=lambda j: (entropies[j], -j))
    top_two_disagreement = sum(outputs[0][j] != outputs[1][j] for j in range(8))
    sharp = record['selected']['temp_0.25_120']
    context = record['selected']['blend']
    context_disagreement = sum(
        program_output(rows[sharp]['program'], pair[0]) !=
        program_output(rows[context]['program'], pair[0])
        for pair in task['hidden'][:8])
    shifted = scores[top] - scores[top[0]]
    probabilities = np.exp(np.clip(shifted, -50, 0))
    probabilities /= probabilities.sum()
    same_top = sum(out[probe] == outputs[0][probe] for out in outputs)
    x = [math.log1p(len(rows)), scores[top[0]],
         scores[top[0]] - scores[top[1]], scores[top[0]] - scores[top[-1]],
         float(probabilities[0]), entropies[probe],
         len(set(out[probe] for out in outputs)), same_top/len(top),
         top_two_disagreement, float(sharp != context), context_disagreement,
         scores[sharp] - scores[context], blend[context] - blend[sharp],
         len(rows[sharp]['program']), probe]
    x.extend(float(task['family'] == family) for family in FAMILIES)
    return probe, x, top_two_disagreement


def ridge(train_x, train_y, test_x, lam):
    mean = train_x.mean(axis=0)
    scale = np.maximum(train_x.std(axis=0), .1)
    a = np.c_[(train_x-mean)/scale, np.ones(len(train_x))]
    b = np.c_[(test_x-mean)/scale, np.ones(len(test_x))]
    penalty = np.diag([lam] * train_x.shape[1] + [0.])
    weights = np.linalg.solve(a.T@a + penalty, a.T@train_y)
    return b@weights


def main():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((RUN / 'frozen_decisions.json').read_text(encoding='utf-8'))
    data = []
    for task, record in zip(tasks, decisions):
        rows = pools[task['id']]
        probe, x, disagreement = features(task, record, rows)
        inp, truth = task['hidden'][probe]
        matching = [i for i, row in enumerate(rows)
                    if program_output(row['program'], inp) == truth]
        scores = record['scores']['temp_0.25_120']
        after = max(matching, key=lambda i: (scores[i], -len(rows[i]['program']),
                                            rows[i]['program'])) if matching else record['selected']['temp_0.25_120']
        before = record['selected']['temp_0.25_120']
        before_correct = bool(evaluate_program(rows[before]['program'], task['hidden'][8:]))
        after_correct = bool(evaluate_program(rows[after]['program'], task['hidden'][8:]))
        data.append({'id': task['id'], 'seed': task['seed'], 'family': task['family'],
                     'probe': probe, 'features': x, 'top_two_disagreement': disagreement,
                     'before': before_correct, 'after': after_correct,
                     'gain': int(after_correct) - int(before_correct)})
    x = np.asarray([row['features'] for row in data], dtype=float)
    y = np.asarray([row['gain'] for row in data], dtype=float)
    seeds = sorted({row['seed'] for row in data})
    learned = {}
    for lam in LAMBDAS:
        predictions = np.empty(len(data), dtype=float)
        for seed in seeds:
            heldout = np.array([row['seed'] == seed for row in data])
            predictions[heldout] = ridge(x[~heldout], y[~heldout], x[heldout], lam)
        chosen = set(np.argsort(-predictions, kind='stable')[:BUDGET].tolist())
        learned[str(lam)] = {'correct': int(sum(row['before'] + (row['gain'] if i in chosen else 0)
                                            for i, row in enumerate(data))),
                             'by_bank': {str(seed): int(sum(
                                 row['before'] + (row['gain'] if i in chosen else 0)
                                 for i, row in enumerate(data) if row['seed'] == seed))
                                         for seed in seeds},
                             'predictions': predictions.tolist()}
    fixed = set(sorted(range(len(data)), key=lambda i: (-data[i]['top_two_disagreement'],
                  data[i]['features'][2], data[i]['id']))[:BUDGET])
    fixed_correct = sum(row['before'] + (row['gain'] if i in fixed else 0)
                        for i, row in enumerate(data))
    summary = {'scope': 'development only; cross-bank predictions on inspected labels',
               'tasks': len(data), 'query_budget': BUDGET,
               'no_query': sum(row['before'] for row in data),
               'query_all': sum(row['after'] for row in data),
               'query_gain_counts': dict(Counter(row['gain'] for row in data)),
               'fixed_top_disagreement': fixed_correct,
               'learned': {key: value['correct'] for key, value in learned.items()}}
    write_json(OUT, {'summary': summary, 'tasks': data, 'learned': learned})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
