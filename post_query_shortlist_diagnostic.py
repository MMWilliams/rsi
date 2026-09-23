"""Opened fresh-panel diagnosis of candidate shortlist ceilings after probe feedback."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program


RUN = ROOT / 'runs/post-query-feedback-transfer-20260918'
OUT = ROOT / 'analysis/post-query-shortlist-diagnostic-20260918.json'
WIDTHS = (20, 50, 100, 200)


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    assert json.loads((RUN / 'audit.json').read_text())['passed']
    tasks = json.loads((RUN / 'sealed_bank.json').read_text())
    pools = json.loads((RUN / 'ast_wide_pools.json').read_text())
    matrix = json.loads((RUN / 'predicted_probe_outputs.json').read_text())
    records = json.loads((RUN / 'frozen_records.json').read_text())
    results = json.loads((RUN / 'results.json').read_text())['tasks']
    rows = []
    checked = 0
    for task, rec, result in zip(tasks, records, results):
        key = task['id']
        assert key == rec['id'] == result['id']
        pool = pools[key]
        labels = [int(bool(evaluate_program(item['program'], task['hidden'][8:])))
                  for item in pool]
        checked += len(labels)
        old = rec['orders']['old']
        correct = {i for i, value in enumerate(labels) if value}
        truth = rec['probe_output']
        survivor = {i for i in range(len(pool)) if matrix[key][i][rec['probe']] == truth}
        if not survivor:
            survivor = set(range(len(pool)))
        row = {'id': key, 'seed': task['seed'], 'pool_size': len(pool),
               'full_reachable': int(bool(correct)),
               'post_probe_reachable': int(bool(correct & survivor)),
               'best_correct_old_rank': next((r for r, i in enumerate(old)
                                              if i in correct), None),
               'e0_one': result['one']['e0'],
               'width': {str(w): {
                   'reachable': int(bool(correct & set(old[:w]))),
                   'survivor_reachable': int(bool(correct & survivor & set(old[:w])))}
                   for w in WIDTHS}}
        rows.append(row)
    assert checked == json.loads((RUN / 'results.json').read_text())[
        'summary']['final_candidate_labels_checked']
    totals = {'tasks': len(rows), 'candidate_labels_rechecked': checked,
              'full_reachable': sum(r['full_reachable'] for r in rows),
              'post_probe_reachable': sum(r['post_probe_reachable'] for r in rows),
              'e0_one': sum(r['e0_one'] for r in rows),
              'width': {str(w): {
                  field: sum(r['width'][str(w)][field] for r in rows)
                  for field in ('reachable', 'survivor_reachable')}
                  for w in WIDTHS},
              'reachable_missed_by_e0': sum(r['full_reachable'] and not r['e0_one']
                                            for r in rows),
              'top20_survivor_missed_by_e0': sum(
                  r['width']['20']['survivor_reachable'] and not r['e0_one']
                  for r in rows)}
    write_json(OUT, {'scope': 'opened diagnostic; no fresh promotion claim',
                     'totals': totals, 'rows': rows})
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    main()
