"""Frozen mixed-bank test of stacked specialist evaluator feedback."""
from __future__ import annotations

import hashlib
import json
import sys

import joblib
import numpy as np

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank, shifted_ast_bank
from wide_candidate_reranker_development import features
from dual_specialist_seed_evaluator import load_models, FAMILIAR, SHIFTED
from cross_family_meta_improver_transfer import interval
import post_query_feedback_transfer as previous


DEST = ROOT / 'runs/candidate-stacking-feedback-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-candidate-stacking-feedback-transfer.md'
SCRIPT = ROOT / 'candidate_stacking_feedback_transfer.py'
DEVELOPMENT = ROOT / 'analysis/candidate-stacking-development-20260918.json'
MODEL_DIR = ROOT / 'analysis/candidate-stacking-models-20260918'
CONTROL_DIR = ROOT / 'analysis/candidate-stacking-controls-20260918'
SEEDS = tuple(range(905100, 905124))
MODELS = {'early': MODEL_DIR / 'early_stacked.joblib',
          'later': MODEL_DIR / 'later_stacked.joblib',
          'scrambled': CONTROL_DIR / 'scrambled.joblib',
          'duplicate': CONTROL_DIR / 'duplicate.joblib',
          'pooled': MODEL_DIR / 'later_pooled.joblib'}
NAMES = ('dual100', 'mean100', 'familiar100', 'shifted100',
         'early100', 'later100', 'scrambled100', 'duplicate100',
         'pooled100', 'selective_dual200', 'dual200', 'later200')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def tasks_for():
    tasks = []
    for seed in SEEDS:
        familiar = random_bank(seed, 4, ('ast_transition',), visible=1, hidden=23)
        shifted = shifted_ast_bank(seed + 100000, 4, visible=1, hidden=23)
        for a, b in zip(familiar, shifted):
            tasks.extend(({**a, 'seed': seed}, {**b, 'seed': seed}))
    return tasks


def public_run(tasks):
    before = previous.SEEDS
    previous.SEEDS = SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS = before


def models_for():
    return {name: joblib.load(path) for name, path in MODELS.items()}


def choices_for(tasks, wide, records, specialists, models):
    rows = []
    for task, rec in zip(tasks, records):
        pool = wide[task['id']]
        order = rec['orders']['old']
        n200 = min(200, len(order))
        n100 = min(100, n200)
        x = features(task, pool, rec, n200)
        pf = specialists['familiar'].predict_proba(x)[:, 1]
        ps = specialists['shifted'].predict_proba(x)[:, 1]
        scores = np.asarray(rec['old_scores'], float)
        std = max(float(scores.std()), .05)
        extra = np.stack((pf, ps, np.maximum(pf, ps),
            np.abs(pf - ps), pf * ps,
            (scores[order[:n200]] - scores[order[0]]) / std,
            np.arange(n200) / 100.), axis=1).astype(np.float32)
        stack = np.c_[x, extra]
        probabilities = {name: model.predict_proba(
            x if name == 'pooled' else stack)[:, 1]
            for name, model in models.items()}
        head = lambda arr, n: max(range(n), key=lambda i: (float(arr[i]), -i))
        f100 = head(pf, n100)
        s100 = head(ps, n100)
        f200 = head(pf, n200)
        s200 = head(ps, n200)
        dual100 = s100 if ps[s100] > pf[f100] else f100
        dual200 = s200 if ps[s200] > pf[f200] else f200
        local = {'dual100': dual100, 'mean100': head((pf + ps)/2, n100),
                 'familiar100': f100, 'shifted100': s100,
                 'dual200': dual200,
                 'early100': head(probabilities['early'], n100),
                 'later100': head(probabilities['later'], n100),
                 'scrambled100': head(probabilities['scrambled'], n100),
                 'duplicate100': head(probabilities['duplicate'], n100),
                 'pooled100': head(probabilities['pooled'], n100),
                 'later200': head(probabilities['later'], n200)}
        choice = {name: order[i] for name, i in local.items()}
        costs = {name: (n100 if name == 'pooled100' else
                        3*n100 if name in ('early100', 'later100',
                                           'scrambled100', 'duplicate100') else
                        2*n200 if name == 'dual200' else
                        3*n200 if name == 'later200' else 2*n100)
                 for name in local}
        rows.append({'id': task['id'], 'seed': task['seed'],
                     'pool_sha256': digest(pool), 'choices': choice,
                     'candidate_scores': costs,
                     'selective_priority': float(ps[s100] - pf[f100]),
                     'selective_extra_scores': 2*(n200-n100),
                     'top100_indices': order[:n100],
                     'top200_indices': order[:n200]})
    by_seed = {seed: [i for i, r in enumerate(rows) if r['seed'] == seed]
               for seed in SEEDS}
    selected = sorted(i for ids in by_seed.values() for i in sorted(
        ids, key=lambda j: (-rows[j]['selective_priority'], rows[j]['id']))[:4])
    chosen = set(selected)
    for i, row in enumerate(rows):
        row['choices']['selective_dual200'] = row['choices'][
            'dual200' if i in chosen else 'dual100']
        row['candidate_scores']['selective_dual200'] = (
            row['candidate_scores']['dual100']
            + (row['selective_extra_scores'] if i in chosen else 0))
    return rows, selected


def manifest():
    files = ('sealed_bank.json', 'base_pools.json', 'ast_wide_pools.json',
             'frozen_records.json', 'public_choices.json', 'allocations.json')
    return {'protocol_sha256': sha(PROTOCOL), 'script_sha256': sha(SCRIPT),
            'development_sha256': sha(DEVELOPMENT),
            'control_stats_sha256': sha(CONTROL_DIR / 'stats.json'),
            'specialist_sha256': {'familiar': sha(FAMILIAR),
                                  'shifted': sha(SHIFTED)},
            'models_sha256': {name: sha(path) for name, path in MODELS.items()},
            'seeds': list(SEEDS), 'tasks': 192,
            'frozen_sha256': {name: sha(DEST / name) for name in files}}


def verify_manifest():
    saved = json.loads((DEST / 'manifest.json').read_text())
    expected = manifest()
    assert all(saved[key] == val for key, val in expected.items())
    return saved


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    assert json.loads(DEVELOPMENT.read_text())['scope'] == 'opened development only'
    tasks = tasks_for()
    base, wide, _, records, _, _, cost = public_run(tasks)
    rows, selected = choices_for(tasks, wide, records,
                                 load_models(), models_for())
    DEST.mkdir(parents=True)
    for name, value in (('sealed_bank.json', tasks), ('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('frozen_records.json', records),
                        ('public_choices.json', rows),
                        ('allocations.json', selected)):
        write_json(DEST / name, value)
    write_json(DEST / 'manifest.json', {**manifest(), 'generation_cost': cost})
    print(json.dumps({'frozen': True, 'tasks': len(tasks),
                      'selective_width_tasks': len(selected),
                      'generation_cost': cost}, indent=2))


def outcome_rows(tasks, wide, rows):
    outcome, checked = [], 0
    for task, row in zip(tasks, rows):
        pool = wide[task['id']]
        assert task['id'] == row['id'] and digest(pool) == row['pool_sha256']
        labels = [int(bool(evaluate_program(item['program'], task['hidden'][8:])))
                  for item in pool]
        checked += len(labels)
        outcome.append({'id': task['id'], 'seed': task['seed'],
                        'domain': 'shifted' if task['family'] == 'shifted_ast'
                        else 'familiar',
                        'labels': {name: labels[index] for name, index
                                   in row['choices'].items()},
                        'top100_reachable': int(any(labels[i] for i
                                                    in row['top100_indices'])),
                        'top200_reachable': int(any(labels[i] for i
                                                    in row['top200_indices'])),
                        'full_reachable': int(any(labels))})
    return outcome, checked


def contrast(banks, a, b):
    d = [row[a] - row[b] for row in banks]
    return {'gain': sum(d), 'positive_banks': sum(v > 0 for v in d),
            'negative_banks': sum(v < 0 for v in d),
            'interval': interval(d), 'bank_differences': d}


def summarize(outcome, rows, checked):
    banks = []
    for seed in SEEDS:
        ids = [i for i, r in enumerate(outcome) if r['seed'] == seed]
        bank = {'seed': seed,
                'top100_reachable': sum(outcome[i]['top100_reachable'] for i in ids),
                'top200_reachable': sum(outcome[i]['top200_reachable'] for i in ids),
                'full_reachable': sum(outcome[i]['full_reachable'] for i in ids)}
        for name in NAMES:
            bank[name] = sum(outcome[i]['labels'][name] for i in ids)
            bank[name + '_candidate_scores'] = sum(
                rows[i]['candidate_scores'][name] for i in ids)
            for domain in ('familiar', 'shifted'):
                bank[name + '_' + domain] = sum(
                    outcome[i]['labels'][name] for i in ids
                    if outcome[i]['domain'] == domain)
        banks.append(bank)
    totals = {key: sum(b[key] for b in banks)
              for key in banks[0] if key != 'seed'}
    pairs = [('later100', name) for name in
             ('early100', 'scrambled100', 'duplicate100', 'dual100',
              'mean100', 'selective_dual200', 'dual200')]
    pairs += [('early100', 'dual100'), ('later200', 'later100'),
              ('later100', 'pooled100')]
    comparisons = {f'{a}_minus_{b}': contrast(banks, a, b) for a, b in pairs}
    needed = [comparisons[f'later100_minus_{name}'] for name in
              ('early100', 'scrambled100', 'duplicate100', 'dual100', 'mean100')]
    early = comparisons['later100_minus_early100']
    dual = comparisons['later100_minus_dual100']
    growth = (all(c['gain'] >= 5 for c in needed) and
              early['interval'][0] > 0 and dual['interval'][0] > 0 and
              early['positive_banks'] >= 8)
    integration = (dual['gain'] >= 8 and dual['interval'][0] > 0 and
                   dual['positive_banks'] >= 12 and
                   totals['later100_familiar'] >= totals['familiar100_familiar'] - 8 and
                   totals['later100_shifted'] >= totals['shifted100_shifted'] - 8)
    return {'tasks': len(outcome), 'candidate_labels_checked': checked,
            'totals': totals, 'comparisons': comparisons,
            'gates': {'evaluator_growth': growth, 'integration': integration},
            'banks': banks}


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    verify_manifest()
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    wide = json.loads((DEST / 'ast_wide_pools.json').read_text())
    rows = json.loads((DEST / 'public_choices.json').read_text())
    outcome, checked = outcome_rows(tasks, wide, rows)
    summary = summarize(outcome, rows, checked)
    write_json(DEST / 'results.json', {'manifest_sha256': sha(DEST / 'manifest.json'),
                                      'summary': summary, 'tasks': outcome})
    print(json.dumps({k: v for k, v in summary.items() if k != 'banks'}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    m = verify_manifest()
    tasks = tasks_for()
    assert normalize(tasks) == json.loads((DEST / 'sealed_bank.json').read_text())
    base, wide, _, records, _, _, cost = public_run(tasks)
    rows, selected = choices_for(tasks, wide, records,
                                 load_models(), models_for())
    for name, value in (('base_pools.json', base), ('ast_wide_pools.json', wide),
                        ('frozen_records.json', records),
                        ('public_choices.json', rows),
                        ('allocations.json', selected)):
        assert normalize(value) == json.loads((DEST / name).read_text()), name
    stable = ('base_candidates', 'extra_ast_candidates',
              'predicted_output_cells', 'e0_candidate_scores',
              'post_query_candidate_scores')
    assert all(cost[k] == m['generation_cost'][k] for k in stable)
    outcome, checked = outcome_rows(tasks, wide, rows)
    summary = summarize(outcome, rows, checked)
    saved = json.loads((DEST / 'results.json').read_text())
    assert saved == {'manifest_sha256': sha(DEST / 'manifest.json'),
                     'summary': summary, 'tasks': outcome}
    result = {'passed': True, 'tasks_rebuilt': len(tasks),
              'candidate_output_cells_rebuilt': cost['predicted_output_cells'],
              'frozen_model_predictions_rebuilt': sum(
                  len(r['top200_indices'])*7 for r in rows),
              'candidate_labels_rebuilt': checked,
              'selective_allocations_rebuilt': len(selected)}
    write_json(DEST / 'audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
