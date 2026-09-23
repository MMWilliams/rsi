"""Opened-bank E0/E3/E6/E18 replay for the selected pairwise ranking rule."""
from __future__ import annotations

import json

from rsi.common import ROOT,write_json
from cross_family_meta_improver_development import source_rows,fit_method
from cross_family_meta_improver_transfer import stage_rows,interval
from focused_feedback_development import fit_weighted,grouped
from pairwise_query_ranking_development import train_pairwise,evaluate,focused_rows


OUT=ROOT/'analysis/pairwise-checkpoint-development-20260918.json'


def main():
    if OUT.exists():raise RuntimeError(f'{OUT} exists')
    source=source_rows();admission=stage_rows('admission')
    group=grouped(admission)
    histories={'p0':source,'p3':source+[r for bank in group[:3] for r in bank],
               'p6':source+admission,
               'p18':source+admission+stage_rows('a')+stage_rows('b')}
    e0=fit_weighted(source,[1]*len(source))
    models={'e0':e0,**{name:train_pairwise(rows,.001,False,e0)
                       for name,rows in histories.items()},
            'ridge18_10':fit_method(histories['p18'],'interaction_10')}
    panels={'meta_transfer':stage_rows('a')+stage_rows('b'),
            'focused_opened':focused_rows()}
    results={panel:{name:evaluate(model,rows) for name,model in models.items()
                    if not (panel=='meta_transfer' and name in ('p18','ridge18_10'))}
             for panel,rows in panels.items()}
    diffs={panel:{name:{'sum':result['correct']-scores['p0']['correct'],
                        'by_bank':[b['correct']-a['correct'] for b,a in zip(
                            result['by_bank'],scores['p0']['by_bank'])],
                        'interval':interval([b['correct']-a['correct'] for b,a in zip(
                            result['by_bank'],scores['p0']['by_bank'])])}
                  for name,result in scores.items() if name not in ('e0','p0')}
           for panel,scores in results.items()}
    out={'scope':'opened-bank developmental checkpoint replay','training_rows':
         {name:len(rows) for name,rows in histories.items()},
         'results':results,'differences_from_p0':diffs,
         'model_rule':'all within-bank positive-vs-nonpositive gain pairs, Adam 300 steps, lambda .001',
         'limits':['All validation labels had been opened before this analysis.',
                   'Counterfactual task gain is supplied by an expensive research oracle.',
                   'No autonomous improver generated this rule.']}
    write_json(OUT,out)
    print(json.dumps({panel:{name:{'correct':value['correct'],
                                  'ast_calls':value['ast_calls']}
                             for name,value in scores.items()}
                      for panel,scores in results.items()},indent=2))


if __name__=='__main__':main()
