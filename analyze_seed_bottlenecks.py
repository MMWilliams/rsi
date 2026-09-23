"""Recompute seed-improver bottlenecks from audited common-bank outcomes."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT,write_json
from seed_casebanks import FAMILIES

COMPONENT=ROOT/'runs/cross-component-mixed-transfer-20260918'
STABLE=ROOT/'runs/stable-cross-family-improver-transfer-20260918'
OUT=ROOT/'analysis/seed-bottleneck-dissection-20260918.json'


def main():
    c=json.loads((COMPONENT/'results.json').read_text())
    crows=c['tasks'];cs=c['summary']
    assert len(crows)==288 and all(len([r for r in crows if r['family']==f])==48 for f in FAMILIES)
    by_family={}
    for family in FAMILIES:
        rows=[r for r in crows if r['family']==family]
        correct={name:sum(r['correct'][name] for r in rows)
                 for name in cs['overall']['correct']}
        by_family[family]={'tasks':48,
                           'base_reachable':sum(r['base_reachable'] for r in rows),
                           'wide_reachable':sum(r['wide_reachable'] for r in rows),
                           'correct':correct,
                           'sharp_minus_fixed':correct['sharp_global']-correct['fixed_map'],
                           'ranker_minus_fixed':correct['ast_ranker']-correct['fixed_map'],
                           'top20_minus_ranker':correct['top20_one']-correct['ast_ranker'],
                           'adaptive_minus_top20':correct['adaptive']-correct['top20_one']}
        assert correct==cs['by_family'][family]['correct']
    s=[]
    for stage in ('a','b'):
        s+=json.loads((STABLE/stage/'results.json').read_text())['tasks']
    assert len(s)==576
    banks=defaultdict(list)
    for row in s:banks[row['seed']].append(row)
    assert len(banks)==12 and all(len(v)==48 for v in banks.values())
    reach=sum(r['reachable'] for r in s);zero=sum(r['zero'] for r in s)
    one=sum(r['one'] for r in s)
    gains=sum(r['one'] and not r['zero'] for r in s)
    harms=sum(r['zero'] and not r['one'] for r in s)
    hindsight=sum(sum(r['zero'] for r in rows)+sum(sorted(
        (int(r['one'])-int(r['zero']) for r in rows),reverse=True)[:8])
        for rows in banks.values())
    selected=json.loads((STABLE/'summary.json').read_text())['correct']['later_stable']
    family_query={family:{'tasks':len(rows),'reachable':sum(r['reachable'] for r in rows),
                          'zero_correct':sum(r['zero'] for r in rows),
                          'one_each_correct':sum(r['one'] for r in rows)}
                  for family in FAMILIES
                  for rows in ([r for r in s if r['family']==family],)}
    assert sum(v['tasks'] for v in family_query.values())==576
    result={'scope':'descriptive analysis of opened, previously frozen synthetic banks',
            'cross_component':{'tasks':len(crows),'by_family':by_family,
                               'overall_correct':cs['overall']['correct']},
            'fresh_query':{'tasks':len(s),'banks':len(banks),'reachable':reach,
                           'no_query_correct':zero,'one_query_each_correct':one,
                           'query_gains':gains,'query_harms':harms,
                           'oracle_hindsight_eight_per_bank':hindsight,
                           'learned_eight_per_bank_correct':selected,
                           'ranking_misses_among_reachable':reach-zero,
                           'remaining_after_one_each':reach-one,
                           'allocation_regret_to_hindsight':hindsight-selected,
                           'by_family':family_query},
            'limits':['Hindsight query allocation uses unavailable final labels.',
                      'Correctness uses fifteen held-out examples, not universal equivalence.',
                      'Opened banks are development evidence for future design.']}
    write_json(OUT,result)
    print(json.dumps({'cross_component':result['cross_component']['overall_correct'],
                      'fresh_query':{k:v for k,v in result['fresh_query'].items()
                                     if k!='by_family'}},indent=2))


if __name__=='__main__':main()
