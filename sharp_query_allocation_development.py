"""Development-only matched-budget one-query allocation controls."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from active_probe_diagnostic import program_output


RUN = ROOT / 'runs/temperature-ranker-transfer-20260917'
OUT = ROOT / 'analysis/sharp-query-allocation-development.json'


def entropy(values):
    counts = Counter(values)
    total = len(values)
    return -sum((n/total)*math.log(n/total) for n in counts.values())


def main():
    tasks = json.loads((RUN / 'sealed_bank.json').read_text(encoding='utf-8'))
    pools = json.loads((RUN / 'candidate_pools.json').read_text(encoding='utf-8'))
    decisions = json.loads((RUN / 'frozen_decisions.json').read_text(encoding='utf-8'))
    public = []
    for task, record in zip(tasks, decisions):
        rows = pools[task['id']]
        sharp = record['selected']['temp_0.25_120']
        context = record['selected']['blend']
        scores = record['scores']['temp_0.25_120']
        order = sorted(range(len(rows)), key=lambda i: (-scores[i],
                       len(rows[i]['program']), rows[i]['program']))
        top = order[:16]
        outputs = [[program_output(rows[i]['program'], pair[0])
                    for pair in task['hidden'][:8]] for i in top]
        probe_entropy = max(range(8), key=lambda j: (entropy([out[j] for out in outputs]), -j))
        top_two_disagreement = sum(program_output(rows[order[0]]['program'], pair[0]) !=
                                   program_output(rows[order[1]]['program'], pair[0])
                                   for pair in task['hidden'][:8])
        two_model_probe = next((j for j, pair in enumerate(task['hidden'][:8])
                                if program_output(rows[sharp]['program'], pair[0]) !=
                                   program_output(rows[context]['program'], pair[0])), None)
        public.append({'id': task['id'], 'seed': task['seed'],
                       'sharp': sharp, 'context': context,
                       'two_model_probe': two_model_probe,
                       'entropy_probe': probe_entropy,
                       'margin': scores[order[0]] - scores[order[1]],
                       'top_two_disagreement': top_two_disagreement,
                       'random_key': hashlib.sha256(('query:'+task['id']).encode()).hexdigest()})
    budget = sum(row['two_model_probe'] is not None for row in public)
    ranks = {
        'random': sorted(range(len(public)), key=lambda i: public[i]['random_key']),
        'uncertainty': sorted(range(len(public)), key=lambda i: (public[i]['margin'],
                                                                public[i]['id'])),
        'top_disagreement': sorted(range(len(public)), key=lambda i: (
            -public[i]['top_two_disagreement'], public[i]['margin'], public[i]['id'])),
    }
    selected = {name: set(order[:budget]) for name, order in ranks.items()}
    correct = {name: 0 for name in ('no_query', 'two_model_two_choice',
                                    'two_model_full_pool', *ranks)}
    by_bank = {task['seed']: {name: 0 for name in correct} for task in tasks}
    rows_out = []
    for i, (task, record, info) in enumerate(zip(tasks, decisions, public)):
        rows = pools[task['id']]
        scores = record['scores']['temp_0.25_120']
        choice = {'no_query': info['sharp']}
        two = info['sharp']
        if info['two_model_probe'] is not None:
            j = info['two_model_probe']
            inp, truth = task['hidden'][j]
            if program_output(rows[info['context']]['program'], inp) == truth and \
               program_output(rows[info['sharp']]['program'], inp) != truth:
                two = info['context']
        choice['two_model_two_choice'] = two
        def filtered(probe):
            inp, truth = task['hidden'][probe]
            matching = [k for k, row in enumerate(rows)
                        if program_output(row['program'], inp) == truth]
            return max(matching, key=lambda k: (scores[k], -len(rows[k]['program']),
                                               rows[k]['program'])) if matching else info['sharp']
        choice['two_model_full_pool'] = (filtered(info['two_model_probe'])
                                         if info['two_model_probe'] is not None
                                         else info['sharp'])
        for name in ranks:
            choice[name] = filtered(info['entropy_probe']) if i in selected[name] else info['sharp']
        outcome = {name: bool(evaluate_program(rows[index]['program'], task['hidden'][8:]))
                   for name, index in choice.items()}
        for name, value in outcome.items():
            correct[name] += value
            by_bank[task['seed']][name] += value
        rows_out.append({'id': task['id'], 'seed': task['seed'],
                         'two_model_probe': info['two_model_probe'],
                         'entropy_probe': info['entropy_probe'],
                         'choice': choice, 'correct': outcome})
    summary = {'scope': 'development only; probe and final labels inspected',
               'tasks': len(tasks), 'matched_query_budget': budget,
               'correct': correct, 'by_bank': by_bank}
    write_json(OUT, {'summary': summary, 'tasks': rows_out})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
