"""Inspected-bank diagnostic for forgetting after the AST-only feedback edit."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from ast_evaluator_feedback import model_inputs, select_model


RUN = ROOT / 'runs/temperature-ranker-transfer-20260917'
OUT = ROOT / 'analysis/ast-feedback-retention-diagnostic.json'


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic already exists')
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    old = json.loads((RUN / 'frozen_decisions.json').read_text(encoding='utf-8'))
    child = model_inputs()
    results = []
    for task, record in zip(tasks, old):
        rows = pools[task['id']]
        assert task['id'] == record['id']
        old_index = record['selected']['temp_0.25_120']
        new_index = select_model(task, rows, child)
        results.append({'id': task['id'], 'seed': task['seed'], 'family': task['family'],
                        'old': bool(evaluate_program(rows[old_index]['program'], task['hidden'][8:])),
                        'updated': bool(evaluate_program(rows[new_index]['program'], task['hidden'][8:]))})
    summary = {'scope': 'development diagnostic on already inspected source-like transfer bank',
               'tasks': len(results), 'old': sum(r['old'] for r in results),
               'updated': sum(r['updated'] for r in results),
               'by_family': {family: {'tasks': sum(r['family'] == family for r in results),
                                      'old': sum(r['old'] for r in results if r['family'] == family),
                                      'updated': sum(r['updated'] for r in results if r['family'] == family)}
                             for family in sorted({r['family'] for r in results})}}
    write_json(OUT, {'summary': summary, 'tasks': results})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
