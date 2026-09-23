"""Opened mixed-bank reachability and post-probe action ceiling decomposition."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program


RUN = ROOT / 'runs/specialist-applicability-transfer-20260918'
OUT = ROOT / 'analysis/mixed-action-space-diagnostic-20260918.json'
WIDTHS = (20, 50, 100, 200)


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    assert json.loads((RUN / 'audit.json').read_text())['passed']
    tasks = json.loads((RUN / 'sealed_bank.json').read_text())
    pools = json.loads((RUN / 'ast_wide_pools.json').read_text())
    matrices = json.loads((RUN / 'predicted_probe_outputs.json').read_text())
    records = json.loads((RUN / 'frozen_records.json').read_text())
    results = json.loads((RUN / 'results.json').read_text())['tasks']
    allocations = json.loads((RUN / 'frozen_allocations.json').read_text())
    rows = []
    checked = 0
    for task, rec, result in zip(tasks, records, results):
        key = task['id']
        assert key == rec['id'] == result['id']
        pool = pools[key]
        labels = [int(bool(evaluate_program(item['program'], task['hidden'][8:])))
                  for item in pool]
        checked += len(labels)
        correct = {i for i, value in enumerate(labels) if value}
        probe = rec['probe']
        truth = rec['probe_output']
        survivor = {i for i in range(len(pool))
                    if matrices[key][i][probe] == truth}
        if not survivor:
            survivor = set(range(len(pool)))
        old = rec['orders']['old']
        queried = key in allocations[str(task['seed'])]
        row = {'id': key, 'seed': task['seed'], 'domain': result['domain'],
               'queried': queried, 'zero': result['zero'],
               'e0_one': result['one']['e0'],
               'specialist_one': result['one']['specialist'],
               'two_action_oracle': max(result['one']['e0'],
                                         result['one']['specialist']),
               'reachable': int(bool(correct)),
               'survivor_reachable': int(bool(correct & survivor)),
               'width': {str(w): {
                   'reachable': int(bool(correct & set(old[:w]))),
                   'survivor_reachable': int(bool(correct & survivor & set(old[:w])))}
                   for w in WIDTHS}}
        rows.append(row)
    assert checked == json.loads((RUN / 'results.json').read_text())[
        'summary']['final_candidate_labels_checked']
    groups = defaultdict(list)
    for row in rows:
        groups[row['domain']].append(row)
    by_domain = {}
    for domain, subset in groups.items():
        by_domain[domain] = {
            'tasks': len(subset), 'full_reachable': sum(r['reachable'] for r in subset),
            'post_probe_reachable': sum(r['survivor_reachable'] for r in subset),
            'width': {str(w): {field: sum(r['width'][str(w)][field]
                         for r in subset) for field in
                         ('reachable', 'survivor_reachable')} for w in WIDTHS},
            'one_each': {name: sum(r[name] for r in subset) for name in
                         ('zero', 'e0_one', 'specialist_one', 'two_action_oracle')},
            'budgeted': {name: sum(r[name] if r['queried'] else r['zero']
                          for r in subset) for name in
                          ('e0_one', 'specialist_one', 'two_action_oracle')},
            'top100_survivor_both_actions_miss': sum(
                r['width']['100']['survivor_reachable'] and
                not r['two_action_oracle'] for r in subset)}
    report = {'scope': 'opened diagnostic; all oracle ceilings use final labels',
              'tasks': len(rows), 'candidate_labels_rechecked': checked,
              'by_domain': by_domain, 'rows': rows}
    write_json(OUT, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
