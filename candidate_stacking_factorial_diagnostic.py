"""Post-audit task-level decomposition of ranker and width changes."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval


DEST = ROOT / 'runs/candidate-stacking-feedback-transfer-20260918'
OUT = ROOT / 'analysis/candidate-stacking-factorial-diagnostic-20260918.json'


def compare(rows, a, b):
    effect = [r['labels'][a] - r['labels'][b] for r in rows]
    seeds = sorted({r['seed'] for r in rows})
    bank = [sum(e for e, r in zip(effect, rows) if r['seed'] == seed)
            for seed in seeds]
    return {'gain': sum(effect), 'positive_tasks': sum(e > 0 for e in effect),
            'negative_tasks': sum(e < 0 for e in effect),
            'positive_banks': sum(e > 0 for e in bank),
            'negative_banks': sum(e < 0 for e in bank),
            'bank_interval': interval(bank),
            'by_domain': {domain: sum(e for e, r in zip(effect, rows)
                                     if r['domain'] == domain)
                          for domain in ('familiar', 'shifted')}}


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic already exists')
    assert json.loads((DEST / 'audit.json').read_text())['passed']
    rows = json.loads((DEST / 'results.json').read_text())['tasks']
    tests = {name: compare(rows, *arms) for name, arms in {
        'ranker_at_100': ('later100', 'dual100'),
        'ranker_at_200': ('later200', 'dual200'),
        'width_with_dual': ('dual200', 'dual100'),
        'width_with_stack': ('later200', 'later100'),
        'stack_vs_fixed_selective_width': ('later100', 'selective_dual200'),
    }.items()}
    oracle = {}
    for names in (('dual100', 'later100'),
                  ('dual100', 'later100', 'dual200', 'later200')):
        oracle['+'.join(names)] = sum(max(r['labels'][name] for name in names)
                                     for r in rows)
    summary = json.loads((DEST / 'results.json').read_text())['summary']
    total = summary['totals']
    result = {'scope': 'post-audit factorial diagnostic; no new promotion gate',
              'tasks': len(rows), 'effects': tests,
              'retrospective_oracle': oracle,
              'factorial_interaction': (total['later200'] - total['later100']
                                         - total['dual200'] + total['dual100']),
              'reachability': {k: total[k] for k in
                               ('top100_reachable', 'top200_reachable',
                                'full_reachable')},
              'selected': {k: total[k] for k in
                           ('dual100', 'later100', 'dual200', 'later200')},
              'candidate_scores': {k: total[k + '_candidate_scores'] for k in
                                   ('dual100', 'later100', 'dual200', 'later200',
                                    'selective_dual200')}}
    write_json(OUT, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
