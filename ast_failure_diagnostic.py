"""Inspect two already scored AST transfers; no fresh inference claim."""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
import torch

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from ast_evaluator_feedback import model_inputs, features


FIRST = ROOT / 'runs/ast-feedback-transfer-20260917'
SECOND = ROOT / 'runs/gated-ast-feedback-20260917'
OUT = ROOT / 'analysis/ast-feedback-failure-diagnostic.json'


def load_tasks(run, mixed):
    tasks = json.loads((run / 'sealed_bank.json').read_text(encoding='utf-8'))
    if mixed:
        tasks = [task for task in tasks if task['family'] == 'ast_transition']
        pools = json.loads((run / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    else:
        pools = {key: value['512'] for key, value in
                 json.loads((run / 'candidate_pools.json').read_text(encoding='utf-8')).items()}
    return tasks, pools


def examine(run, mixed, data):
    model, mean, scale = data
    tasks, pools = load_tasks(run, mixed)
    records = []
    with torch.no_grad():
        for task in tasks:
            rows = pools[task['id']]
            x = np.asarray(features(task, rows), dtype=np.float32)
            logits = model(torch.from_numpy((x - mean) / scale)).numpy()
            order = sorted(range(len(rows)), key=lambda i: (float(logits[i]),
                           -len(rows[i]['program']), rows[i]['program']), reverse=True)
            labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
            ranks = [rank + 1 for rank, index in enumerate(order) if labels[index]]
            selected = order[0]
            records.append({'id': task['id'], 'seed': task['seed'], 'reference': task['reference'],
                            'candidates': len(rows), 'correct_candidates': sum(labels),
                            'best_correct_rank': min(ranks, default=None),
                            'selected_correct': labels[selected],
                            'selected_source': rows[selected]['source'],
                            'selected_complexity': len(rows[selected]['program']),
                            'best_correct_complexity': min((len(rows[i]['program']) for i, y in enumerate(labels)
                                                            if y), default=None)})
    def summary(group):
        reachable = [r for r in group if r['best_correct_rank'] is not None]
        return {'tasks': len(group), 'reachable': len(reachable),
                'selected': sum(r['selected_correct'] for r in group),
                'correct_candidate_count': sum(r['correct_candidates'] for r in group),
                'top_k_reachable': {str(k): sum(r['best_correct_rank'] <= k for r in reachable)
                                    for k in (1, 5, 10, 20, 50, 100)}}
    return {'summary': summary(records),
            'by_rule': {rule: summary([r for r in records if rule in r['reference']])
                        for rule in ('affine_fold', 'affine_alt')},
            'records': records}


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    data = model_inputs()
    result = {'scope': 'diagnostic on two inspected AST transfers',
              'ast_only': examine(FIRST, False, data),
              'mixed': examine(SECOND, True, data)}
    write_json(OUT, result)
    print(json.dumps({name: {'summary': result[name]['summary'],
                             'by_rule': result[name]['by_rule']}
                      for name in ('ast_only', 'mixed')}, indent=2))


if __name__ == '__main__':
    main()
