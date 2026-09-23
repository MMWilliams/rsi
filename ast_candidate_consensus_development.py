"""Development-only semantic-cluster reranking on inspected AST pools."""
from __future__ import annotations

import json
import math

import numpy as np
import torch

from rsi.common import ROOT, write_json
from rsi.semantic_invention import evaluate_program
from seed_growth import representation
from mixed_probe_diagnostic import bool_safe_structure
from temperature_withheld_families import inputs
from ast_evaluator_feedback import model_inputs
import seed_growth


FIRST = ROOT / 'runs/ast-feedback-transfer-20260917'
SECOND = ROOT / 'runs/gated-ast-feedback-20260917'
OUT = ROOT / 'analysis/ast-candidate-consensus-development.json'
ALPHAS = (0., .2, .5, 1., 2.)


def load(run, mixed):
    tasks = json.loads((run / 'sealed_bank.json').read_text(encoding='utf-8'))
    if mixed:
        tasks = [t for t in tasks if t['family'] == 'ast_transition']
        pools = json.loads((run / 'ast_wide_pools.json').read_text(encoding='utf-8'))
    else:
        pools = {key: value['512'] for key, value in
                 json.loads((run / 'candidate_pools.json').read_text(encoding='utf-8')).items()}
    return tasks, pools


def choose(scores, rows, keys, alpha):
    groups = {}
    for i, key in enumerate(keys):
        groups.setdefault(key, []).append(i)
    candidates = []
    for members in groups.values():
        best = max(members, key=lambda i: (float(scores[i]), -len(rows[i]['program']), rows[i]['program']))
        candidates.append((float(scores[best]) + alpha * math.log(len(members)), best))
    return max(candidates, key=lambda x: (x[0], -len(rows[x[1]]['program']), rows[x[1]]['program']))[1], len(groups)


def study(run, mixed, parent, child):
    tasks, pools = load(run, mixed)
    _, mean, scale, parents, _ = parent
    specialist, child_mean, child_scale = child
    records = []
    with torch.no_grad():
        for task in tasks:
            rows = pools[task['id']]
            f = representation({'id': task['id'], 'visible': task['visible']}, rows)
            x = np.asarray(f['structural'], dtype=np.float32)
            logits = {'parent': parents['0.25'](torch.from_numpy((x - mean) / scale)).numpy(),
                      'specialist': specialist(torch.from_numpy((x - child_mean) / child_scale)).numpy()}
            labels = [bool(evaluate_program(row['program'], task['hidden'][8:])) for row in rows]
            behavior = [np.packbits(np.asarray(sig, dtype=np.uint8)).tobytes()
                        for sig in f['behavior']]
            keys = {'behavior': behavior,
                    'behavior_boundary': [(sig, int(boundary))
                                          for sig, boundary in zip(behavior, f['boundary'])]}
            selected = {}; groups = {}
            for model_name, scores in logits.items():
                scaled = (scores - np.median(scores)) / max(float(np.std(scores)), .01)
                for key_name, signatures in keys.items():
                    for alpha in ALPHAS:
                        index, n_groups = choose(scaled, rows, signatures, alpha)
                        selected[f'{model_name}:{key_name}:{alpha}'] = bool(labels[index])
                        groups[key_name] = n_groups
            records.append({'id': task['id'], 'seed': task['seed'], 'reference': task['reference'],
                            'reachable': any(labels), 'candidates': len(rows), 'groups': groups,
                            'selected': selected})
    keys = list(records[0]['selected'])
    return {'tasks': len(records), 'reachable': sum(r['reachable'] for r in records),
            'mean_groups': {name: sum(r['groups'][name] for r in records)/len(records)
                            for name in records[0]['groups']},
            'correct': {key: sum(r['selected'][key] for r in records) for key in keys},
            'records': records}


def main():
    if OUT.exists():
        raise RuntimeError('development result exists')
    seed_growth.structure = bool_safe_structure
    parent, child = inputs(), model_inputs()
    first = study(FIRST, False, parent, child)
    second = study(SECOND, True, parent, child)
    result = {'scope': 'development only, both label sets previously inspected',
              'alphas': ALPHAS, 'ast_only': first, 'mixed': second}
    write_json(OUT, result)
    print(json.dumps({name: {key: value for key, value in result[name].items() if key != 'records'}
                      for name in ('ast_only', 'mixed')}, indent=2))


if __name__ == '__main__':
    main()
