"""Development-only fixed output-query sensors on inspected wide AST pools."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from active_probe_diagnostic import program_output


RUN = ROOT / 'runs/ast-feedback-replay-transfer-20260917'
OUT = ROOT / 'analysis/ast-probe-sensor-development.json'
MODES = ('random', 'minimax', 'top20_entropy', 'top_disagreement', 'weighted_entropy')


def predictions(item):
    task, rows = item
    probes = [text for text, _ in task['hidden'][:8]]
    return task['id'], [[program_output(row['program'], probe) for probe in probes]
                        for row in rows]


def choose_probe(task_id, matrix, order, scores, remaining, used, mode):
    available = [j for j in range(8) if j not in used]
    if mode == 'random':
        return min(available, key=lambda j: hashlib.sha256(
            f'{task_id}:probe-random:{len(used)}:{j}'.encode()).digest())
    ranked = [i for i in order if i in remaining]
    subset = ranked[:20] if mode in ('top20_entropy', 'top_disagreement') else ranked
    if mode == 'weighted_entropy':
        raw = np.asarray([scores[i] for i in subset], dtype=float)
        norm = (raw - raw.max()) / max(float(np.std(raw)), .05)
        weights = np.exp(norm); weights /= weights.sum()
    else:
        weights = np.full(len(subset), 1 / len(subset))
    values = []
    for j in available:
        counts = Counter(matrix[i][j] for i in subset)
        if mode == 'minimax':
            value = -max(counts.values()) / len(subset)
        elif mode == 'top_disagreement':
            value = 1 - counts[matrix[subset[0]][j]] / len(subset)
        else:
            mass = {}
            for i, weight in zip(subset, weights):
                key = matrix[i][j]
                mass[key] = mass.get(key, 0.) + float(weight)
            value = -sum(p * math.log(p) for p in mass.values() if p > 0)
        values.append((value, -j, j))
    return max(values)[2]


def main():
    if OUT.exists():
        raise RuntimeError('development result exists')
    import torch
    from ast_feedback_replay_update import updated_model
    from ast_evaluator_feedback import features
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    with ProcessPoolExecutor(max_workers=8) as executor:
        generated = dict(executor.map(predictions, ((task, pools[task['id']]) for task in tasks)))
    model, mean, scale = updated_model()
    records = []
    with torch.no_grad():
        for task in tasks:
            rows = pools[task['id']]
            x = np.asarray(features(task, rows), dtype=np.float32)
            scores = model(torch.from_numpy((x - mean) / scale)).numpy()
            order = sorted(range(len(rows)), key=lambda i: (-float(scores[i]),
                           len(rows[i]['program']), rows[i]['program']))
            matrix = generated[task['id']]
            labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
            result = {'baseline': bool(labels[order[0]])}
            probes = task['hidden'][:8]
            for mode in MODES:
                remaining = set(range(len(rows))); used = []
                for query in (1, 2):
                    j = choose_probe(task['id'], matrix, order, scores, remaining, used, mode)
                    used.append(j)
                    matches = {i for i in remaining if matrix[i][j] == probes[j][1]}
                    if matches:
                        remaining = matches
                    selected = next((i for i in order if i in remaining), order[0])
                    result[f'{mode}_{query}'] = bool(labels[selected])
            oracle_best_one = False
            for j in range(8):
                matches = {i for i in range(len(rows)) if matrix[i][j] == probes[j][1]}
                selected = next((i for i in order if i in matches), order[0])
                oracle_best_one |= bool(labels[selected])
            records.append({'id': task['id'], 'seed': task['seed'], 'stream': task['stream'],
                            'candidates': len(rows), 'reachable': any(labels),
                            'oracle_best_one': oracle_best_one, 'correct': result})
    names = tuple(records[0]['correct'])
    def agg(group):
        return {'tasks': len(group), 'reachable': sum(r['reachable'] for r in group),
                'oracle_best_one': sum(r['oracle_best_one'] for r in group),
                'correct': {name: sum(r['correct'][name] for r in group) for name in names}}
    summary = {'scope': 'development only; prior target labels inspected',
               'overall': agg(records),
               'by_stream': {stream: agg([r for r in records if r['stream'] == stream])
                             for stream in ('mixed', 'ast_only')},
               'by_bank': [{'seed': seed, **agg([r for r in records if r['seed'] == seed])}
                           for seed in sorted({r['seed'] for r in records})]}
    write_json(OUT, {'summary': summary, 'tasks': records})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
