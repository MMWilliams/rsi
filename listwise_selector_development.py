"""Development-only family-conditioned edit selector from verified feedback."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json


SOURCE = ROOT / 'runs/listwise-evaluator-transfer-20260917/results.json'
OUT = ROOT / 'analysis/listwise-selector-development.json'
NAMES = ('blend', 'listwise_120')
FAMILIES = ('stack_transition', 'mutation_transition', 'self_edit_transition')


def family_counts(rows):
    return {family: {name: sum(row['correct'][name] for row in rows
                               if row['family'] == family) for name in NAMES}
            for family in FAMILIES}


def policy(prior, admission, weight):
    a = family_counts(admission)
    choice = {}
    for family in FAMILIES:
        prior_gap = prior[family]['listwise_120'] - prior[family]['blend']
        admission_gap = a[family]['listwise_120'] - a[family]['blend']
        choice[family] = ('listwise_120' if prior_gap + weight * admission_gap >= 0
                          else 'blend')
    return choice


def evaluate(rows, choice):
    return sum(row['correct'][choice[row['family']]] for row in rows)


def main():
    rows = json.loads(SOURCE.read_text(encoding='utf-8'))['tasks']
    seeds = sorted({row['seed'] for row in rows})
    episodes = []
    for seed in seeds:
        prior_rows = [row for row in rows if row['seed'] != seed]
        bank = [row for row in rows if row['seed'] == seed]
        assert len(bank) == 32
        prior = family_counts(prior_rows)
        admission, final = bank[:16], bank[16:]
        choices = {str(weight): policy(prior, admission, weight)
                   for weight in (0, 1, 2, 4)}
        episodes.append({'seed': seed, 'fixed_listwise': sum(
            row['correct']['listwise_120'] for row in final),
            'fixed_blend': sum(row['correct']['blend'] for row in final),
            'policies': {key: {'choice': choice, 'final_correct': evaluate(final, choice)}
                         for key, choice in choices.items()}})
    summary = {'scope': 'development only; leave-one-bank-out prior',
               'admission_tasks_per_bank': 16, 'final_tasks_per_bank': 16,
               'fixed_listwise': sum(row['fixed_listwise'] for row in episodes),
               'fixed_blend': sum(row['fixed_blend'] for row in episodes),
               'policies': {str(weight): sum(row['policies'][str(weight)]['final_correct']
                                             for row in episodes)
                            for weight in (0, 1, 2, 4)}}
    write_json(OUT, {'summary': summary, 'episodes': episodes,
                     'frozen_prior': family_counts(rows)})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
