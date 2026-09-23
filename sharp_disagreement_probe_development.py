"""Development-only one-query arbitration of sharp and context evaluators."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from active_probe_diagnostic import program_output
from mixed_evaluator_transfer import choose


RUN = ROOT / 'runs/temperature-ranker-transfer-20260917'
OUT = ROOT / 'analysis/sharp-disagreement-probe-development.json'


def main():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((RUN / 'frozen_decisions.json').read_text(encoding='utf-8'))
    results = []
    for task, record in zip(tasks, decisions):
        rows = pools[task['id']]
        sharp = record['selected']['temp_0.25_120']
        context = record['selected']['blend']
        probe = None
        if sharp != context:
            for j, pair in enumerate(task['hidden'][:8]):
                a = program_output(rows[sharp]['program'], pair[0])
                b = program_output(rows[context]['program'], pair[0])
                if a != b:
                    probe = j
                    break
        two_choice = sharp
        full_pool = sharp
        if probe is not None:
            inp, truth = task['hidden'][probe]
            a = program_output(rows[sharp]['program'], inp)
            b = program_output(rows[context]['program'], inp)
            if b == truth and a != truth:
                two_choice = context
            matching = [i for i, row in enumerate(rows)
                        if program_output(row['program'], inp) == truth]
            if matching:
                scores = record['scores']['temp_0.25_120']
                full_pool = max(matching, key=lambda i: (scores[i],
                    -len(rows[i]['program']), rows[i]['program']))
        indices = {'sharp': sharp, 'context': context,
                   'two_choice': two_choice, 'full_pool': full_pool}
        correct = {name: bool(evaluate_program(rows[index]['program'],
                                               task['hidden'][8:]))
                   for name, index in indices.items()}
        results.append({'id': task['id'], 'seed': task['seed'],
                        'family': task['family'], 'query': probe,
                        'different_choices': sharp != context,
                        'correct': correct})
    names = ('sharp', 'context', 'two_choice', 'full_pool')
    def aggregate(group):
        return {'tasks': len(group), 'queries': sum(row['query'] is not None for row in group),
                'correct': {name: sum(row['correct'][name] for row in group)
                            for name in names}}
    summary = {'scope': 'development only; probe and final labels previously inspected',
               'overall': aggregate(results),
               'by_bank': {str(seed): aggregate([row for row in results
                                                if row['seed'] == seed])
                           for seed in sorted({row['seed'] for row in results})},
               'by_family': {family: aggregate([row for row in results
                                                if row['family'] == family])
                             for family in sorted({row['family'] for row in results})},
               'discordant_choices': sum(row['different_choices'] for row in results)}
    write_json(OUT, {'summary': summary, 'tasks': results})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
