"""Hindsight bound for choosing one whole-bank policy from tested catalogs."""
from __future__ import annotations

import json

from rsi.common import ROOT,write_json


OUT=ROOT/'analysis/edit-catalog-headroom-20260918.json'
RUNS=('focused-feedback-transfer-20260918','pairwise-query-transfer-20260918')


def analyze(run):
    path=ROOT/'runs'/run/'results.json'
    data=json.loads(path.read_text())
    banks=data['banks'];names=tuple(banks[0]['correct'])
    totals={name:sum(bank['correct'][name] for bank in banks) for name in names}
    fixed=max(names,key=lambda name:(totals[name],-names.index(name)))
    best_each=[max(bank['correct'].values()) for bank in banks]
    return {'run':run,'banks':len(banks),'tasks':len(data['tasks']),
            'policies':names,'totals':totals,'best_fixed_policy':fixed,
            'best_fixed_correct':totals[fixed],
            'unavailable_best_whole_bank_correct':sum(best_each),
            'whole_bank_selector_headroom':sum(best_each)-totals[fixed],
            'unavailable_best_eight_individual_calls':sum(b['hindsight_eight'] for b in banks),
            'individual_call_placement_headroom':sum(b['hindsight_eight'] for b in banks)-totals[fixed],
            'by_bank':[{'seed':b['seed'],'best_fixed':b['correct'][fixed],
                        'best_catalog':max(b['correct'].values()),
                        'hindsight_eight':b['hindsight_eight']} for b in banks]}


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    result={'scope':'hindsight analysis of already opened fresh-run outcomes',
            'runs':{name:analyze(name) for name in RUNS},
            'limits':['Best whole-bank policy uses unavailable final labels.',
                      'Individual-call hindsight also uses unavailable labels and is a different action class.',
                      'Catalog headroom depends on the tested policy set and does not bound new edits.']}
    write_json(OUT,result)
    print(json.dumps({name:{k:v for k,v in run.items() if k in
                      ('best_fixed_policy','best_fixed_correct',
                       'unavailable_best_whole_bank_correct','whole_bank_selector_headroom',
                       'unavailable_best_eight_individual_calls','individual_call_placement_headroom')}
                      for name,run in result['runs'].items()},indent=2))


if __name__=='__main__':main()
