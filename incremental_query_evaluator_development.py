"""Opened-bank checkpoint replay for verified evaluator feedback.

This is a development screen only: all three panels have previously been opened.
The later prospective protocol must use new banks and freeze outputs first.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from rsi.common import ROOT, write_json
from cross_family_meta_improver_development import fit_method, select, source_rows
from cross_family_meta_improver_transfer import stage_rows, interval
from cross_family_query_value_development import choose as fixed_choose


OUT = ROOT / 'analysis/incremental-query-evaluator-development-20260918.json'
PANELS = ROOT / 'runs/cross-family-meta-improver-transfer-20260918'
METHOD = 'interaction_100'


def by_seed(rows):
    result = defaultdict(list)
    for row in rows:
        result[row['seed']].append(row)
    assert all(len(group) == 48 for group in result.values())
    return [result[key] for key in sorted(result)]


def scrambled(rows):
    result = [dict(row) for row in rows]
    blocks = sorted({row['public_block'] for row in rows})
    for block in blocks:
        indexes = [i for i,row in enumerate(rows) if row['public_block'] == block]
        donors = indexes[-1:] + indexes[:-1]
        for target, donor in zip(indexes, donors):
            result[target]['gain'] = rows[donor]['gain']
    return result


def score(group, ids):
    assert len(ids) == 8
    return sum(row['one'] if row['id'] in ids else row['zero'] for row in group)


def main():
    if OUT.exists():
        raise RuntimeError(f'{OUT} exists')
    source = source_rows()
    feedback = by_seed(stage_rows('admission'))
    transfer_a = by_seed(stage_rows('a'))
    transfer_b = by_seed(stage_rows('b'))
    assert len(source) == 576 and len(feedback) == len(transfer_a) == len(transfer_b) == 6
    histories = {'e0':source,
                 'e3':source + [r for bank in feedback[:3] for r in bank],
                 'e6':source + [r for bank in feedback for r in bank],
                 'scrambled_e6':source + scrambled([r for bank in feedback for r in bank]),
                 'duplicate_e6':source + source[:288]}
    models = {name:fit_method(rows,METHOD) for name,rows in histories.items()}
    banks=[]
    for panel,groups in (('a',transfer_a),('b',transfer_b)):
        for group in groups:
            correct = {name:score(group,select(group,model)) for name,model in models.items()}
            correct['transform_mutation'] = score(group,fixed_choose(group,'transform_mutation'))
            correct['no_query'] = sum(r['zero'] for r in group)
            correct['one_each'] = sum(r['one'] for r in group)
            banks.append({'panel':panel,'seed':group[0]['seed'],'correct':correct,
                          'chosen':{name:sorted(select(group,model)) for name,model in models.items()}})
    names=tuple(banks[0]['correct'])
    totals={name:sum(b['correct'][name] for b in banks) for name in names}
    diffs=[b['correct']['e6']-b['correct']['e0'] for b in banks]
    summary={'scope':'development replay on already opened banks; not fresh confirmation',
             'method':METHOD,'source_rows':len(source),'feedback_banks':6,
             'transfer_banks':12,'counterfactual_feedback_labels':288,
             'history_rows':{name:len(rows) for name,rows in histories.items()},
             'totals':totals,'e6_minus_e0_by_bank':diffs,
             'e6_minus_e0_interval':interval(diffs),
             'a_totals':{name:sum(b['correct'][name] for b in banks if b['panel']=='a') for name in names},
             'b_totals':{name:sum(b['correct'][name] for b in banks if b['panel']=='b') for name in names}}
    sources={str((PANELS/panel/file).relative_to(ROOT)):
             hashlib.sha256((PANELS/panel/file).read_bytes()).hexdigest()
             for panel in ('admission','a','b') for file in ('frozen_records.json','results.json')}
    write_json(OUT,{'summary':summary,'models':models,'banks':banks,'source_sha256':sources,
                    'limits':['Feedback uses full per-task zero/one counterfactuals provided by the exact research oracle, not only deployed eight-call feedback.',
                              'The target banks and labels were opened before this analysis was designed.',
                              'All checkpoints use identical fixed candidate pools and eight calls per bank.']})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
