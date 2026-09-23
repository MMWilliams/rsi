"""Decompose the fresh mixed zero-query integration result without tuning it."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT, write_json

RUN=ROOT/'runs/zero-query-mixed-integration-transfer-20260918'
OUT=ROOT/'analysis/mixed-zero-query-failure-diagnostic-20260918.json'


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    data=json.loads((RUN/'results.json').read_text())
    manifest=json.loads((RUN/'manifest.json').read_text())
    rows=data['tasks']
    groups=defaultdict(list)
    for row in rows:
        groups[row['domain']].append(row)
    result={}
    for domain,items in [('all',rows),*sorted(groups.items())]:
        result[domain]={
            'tasks':len(items),
            'full_reachable':sum(r['full_reachable'] for r in items),
            'top100_reachable':sum(r['top100_reachable'] for r in items),
            'e0':sum(r['labels']['e0'] for r in items),
            'ab':sum(r['labels']['ab'] for r in items),
            'pooled':sum(r['labels']['pooled'] for r in items),
            'visible_later':sum(r['labels']['visible_later'] for r in items),
            'effect_later':sum(r['labels']['effect_later'] for r in items),
            'type_oracle':sum(r['labels']['type_oracle'] for r in items),
            'two_choice_oracle':sum(max(r['labels'][name]
                                        for name in ('e0','ab')) for r in items),
            'three_choice_oracle':sum(max(r['labels'][name]
                                          for name in ('e0','ab','pooled'))
                                      for r in items),
            'top100_reachable_missed_by_three':sum(
                r['top100_reachable'] and not any(r['labels'][name]
                for name in ('e0','ab','pooled')) for r in items),
            'full_reachable_below_top100':sum(
                r['full_reachable'] and not r['top100_reachable'] for r in items),
            'ab_fixes_e0':sum(r['labels']['ab']>r['labels']['e0']
                              for r in items),
            'ab_harms_e0':sum(r['labels']['ab']<r['labels']['e0']
                              for r in items),
            'pooled_fixes_ab':sum(r['labels']['pooled']>r['labels']['ab']
                                  for r in items),
            'pooled_harms_ab':sum(r['labels']['pooled']<r['labels']['ab']
                                  for r in items),
            'later_visible_fixes_early':sum(
                r['labels']['visible_later']>r['labels']['visible_early']
                for r in items),
            'later_visible_harms_early':sum(
                r['labels']['visible_later']<r['labels']['visible_early']
                for r in items)}
    result['cost']={k:manifest['cost'][k] for k in
        ('base_candidates','extra_ast_candidates','predicted_output_cells',
         'e0_candidate_scores')}
    result['candidate_scores']=manifest['candidate_scores']
    result['scope']='post-test diagnostic; unavailable oracle policies are ceilings'
    write_json(OUT,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
