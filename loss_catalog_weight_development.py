"""Development-only prior-strength and decay sensitivity after inheritance trial."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json


RUN = ROOT / 'runs/loss-catalog-inheritance-20260917'
PRIOR = ROOT / 'runs/temperature-ranker-transfer-20260917/results.json'
OUT = ROOT / 'analysis/loss-catalog-weight-development.json'
CATALOG = ('t1', 't05', 't025')
WEIGHTS = (0, 8, 16, 32, 64, 128, 192)
DECAYS = (0, .25, .5, 1)


def choose(table):
    return max(CATALOG, key=lambda name: (table[name], -CATALOG.index(name)))


def main():
    journal = json.loads((RUN / 'frozen_policy_choices.json').read_text(encoding='utf-8'))
    result = json.loads((RUN / 'results.json').read_text(encoding='utf-8'))
    raw = json.loads(PRIOR.read_text(encoding='utf-8'))['summary']['overall']['correct']
    rates = {'t1': raw['temp_1.0_120']/192,
             't05': raw['temp_0.5_120']/192,
             't025': raw['temp_0.25_120']/192}
    variants = {}
    for weight in WEIGHTS:
        for decay in DECAYS:
            parent = 0
            child = 0
            parent_choices = []
            child_choices = []
            for entry, outcome in zip(journal['episodes'], result['episodes']):
                admission = entry['parent_admission']
                ptable = {name: weight*rates[name] + sum(
                    row['correct'][name] for row in admission) for name in CATALOG}
                pchoice = choose(ptable)
                ctable = {name: weight*decay*rates[name] + sum(
                    row['correct'][name] for group in (
                        entry['parent_admission'], entry['parent_final'],
                        entry['child_admission']) for row in group)
                          for name in CATALOG}
                cchoice = choose(ctable)
                parent += outcome['parent_fixed'][pchoice]
                child += outcome['child_fixed'][cchoice]
                parent_choices.append(pchoice)
                child_choices.append(cchoice)
            variants[f'{weight}:{decay}'] = {'parent_correct': parent,
                                             'child_correct': child,
                                             'parent_choices': parent_choices,
                                             'child_choices': child_choices}
    summary = {'scope': 'development only; trial outcomes already inspected',
               'episodes': len(journal['episodes']), 'final_tasks_per_stage': 96,
               'fixed': result['summary']['child_fixed'],
               'scores': {key: [v['parent_correct'], v['child_correct']]
                          for key, v in variants.items()}}
    write_json(OUT, {'summary': summary, 'variants': variants})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
