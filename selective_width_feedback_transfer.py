"""Fresh frozen test of incremental width-edit feedback on mixed AST banks."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from rsi.common import ROOT, digest, write_json
from rsi.semantic_invention import evaluate_program
from seed_casebanks import random_bank, shifted_ast_bank
from specialist_applicability_development import pair_features
from wide_candidate_reranker_development import features
from dual_specialist_seed_evaluator import load_models, FAMILIAR, SHIFTED
from cross_family_meta_improver_transfer import interval
from selective_width_policy_development import select
import post_query_feedback_transfer as previous

DEST = ROOT / 'runs/selective-width-feedback-transfer-20260918'
PROTOCOL = ROOT / 'EXPERIMENT-selective-width-feedback-transfer.md'
SCRIPT = ROOT / 'selective_width_feedback_transfer.py'
SOURCE = ROOT / 'analysis/selective-width-rows-development-20260918.json'
SEEDS = tuple(range(904950, 904974))
PANELS = ('zero-query-mixed-integration-transfer-20260918',
          'three-action-improver-transfer-20260918',
          'dual-specialist-integration-transfer-20260918')
NAMES = ('early', 'later', 'scrambled', 'duplicate', 'shifted_priority',
         'uncertain', 'random', 'none', 'all200', 'oracle')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_for():
    tasks = []
    for seed in SEEDS:
        familiar = random_bank(seed, 4, ('ast_transition',), visible=1, hidden=23)
        shifted = shifted_ast_bank(seed + 100000, 4, visible=1, hidden=23)
        for a, b in zip(familiar, shifted):
            tasks.extend(({**a, 'seed': seed}, {**b, 'seed': seed}))
    return tasks


def public_run(tasks):
    old = previous.SEEDS
    previous.SEEDS = SEEDS
    try:
        return previous.public_run(tasks)
    finally:
        previous.SEEDS = old


def fit(rows):
    x = np.asarray([r['public_features'] for r in rows], np.float32)
    heads = {}
    for width in ('100', '200'):
        y = np.asarray([r['outcomes'][width] for r in rows], int)
        heads[width] = HistGradientBoostingClassifier(
            max_depth=2, max_iter=60, learning_rate=.05,
            min_samples_leaf=12, l2_regularization=5,
            random_state=221).fit(x, y)
    return heads


def forecast(heads, rows):
    x = np.asarray([r['public_features'] for r in rows], np.float32)
    return (heads['200'].predict_proba(x)[:, 1]
            - heads['100'].predict_proba(x)[:, 1])


def source_rows():
    src = json.loads(SOURCE.read_text())['rows']
    early = [r for r in src if r['panel'] in PANELS[:2]]
    added = [r for r in src if r['panel'] == PANELS[2]]
    assert len(early) == 384 and len(added) == 192
    rng = np.random.default_rng(904974)
    scrambled = []
    for seed in sorted({r['seed'] for r in added}):
        group = [r for r in added if r['seed'] == seed]
        perm = rng.permutation([r['outcomes']['200'] for r in group])
        scrambled.extend([{**r, 'outcomes': {**r['outcomes'], '200': int(v)}}
                          for r, v in zip(group, perm)])
    duplicate = []
    for domain in ('familiar', 'shifted'):
        group = [r for r in early if r['domain'] == domain]
        duplicate.extend([group[i] for i in rng.choice(len(group), 96,
                                                       replace=True)])
    return {'early': early, 'later': early + added,
            'scrambled': early + scrambled, 'duplicate': early + duplicate}


def public_rows(tasks, wide, records, specialists):
    rows = []
    for task, rec in zip(tasks, records):
        pool = wide[task['id']]
        old = rec['orders']['old']
        n = min(200, len(old))
        x = features(task, pool, rec, n)
        p = {name: model.predict_proba(x)[:, 1]
             for name, model in specialists.items()}
        choices = {}
        info = None
        for width in (100, 200):
            k = min(width, n)
            head = {name: max(range(k), key=lambda i: (float(prob[i]), -i))
                    for name, prob in p.items()}
            expert = ('shifted' if p['shifted'][head['shifted']] >
                      p['familiar'][head['familiar']] else 'familiar')
            choices[str(width)] = old[head[expert]]
            if width == 100:
                info = {'familiar': float(p['familiar'][head['familiar']]),
                        'shifted': float(p['shifted'][head['shifted']]),
                        'expert': expert}
        scores = np.asarray(rec['old_scores'], float)
        std = max(float(scores.std()), .05)
        public = pair_features(task['visible'][0]) + [
            len(pool) / 512., len(old) / 512., std,
            info['familiar'], info['shifted'],
            info['shifted'] - info['familiar'],
            float(info['expert'] == 'shifted'),
            float(choices['100'] == rec['orders']['e0'][0]),
            (scores[choices['100']] - scores[rec['orders']['e0'][0]]) / std]
        rows.append({'id': task['id'], 'seed': task['seed'],
                     'public_features': public, 'choices': choices,
                     'pool_sha256': digest(pool),
                     'extra_scores': 2 * (n - min(100, n))})
    return rows


def allocations(rows, trained):
    out = {'none': set(), 'all200': set(range(len(rows)))}
    for name, heads in trained.items():
        out[name] = select(rows, forecast(heads, rows))
    out['shifted_priority'] = select(rows, np.asarray([
        r['public_features'][-4] for r in rows]))
    out['uncertain'] = select(rows, np.asarray([
        -max(r['public_features'][-6], r['public_features'][-5])
        for r in rows]))
    out['random'] = select(rows, np.random.default_rng(904975).random(len(rows)))
    return {name: sorted(ids) for name, ids in out.items()}


def manifest():
    return {'protocol_sha256': sha(PROTOCOL), 'script_sha256': sha(SCRIPT),
            'source_sha256': sha(SOURCE), 'specialist_sha256':
            {'familiar': sha(FAMILIAR), 'shifted': sha(SHIFTED)},
            'seeds': list(SEEDS), 'tasks': 192,
            'frozen_sha256': {name: sha(DEST / name) for name in (
                'sealed_bank.json', 'base_pools.json', 'ast_wide_pools.json',
                'frozen_records.json', 'public_rows.json',
                'allocations.json')},
            'trained_sha256': {name: sha(DEST / f'{name}.joblib') for name in
                               ('early', 'later', 'scrambled', 'duplicate')}}


def prepare():
    if DEST.exists():
        raise RuntimeError('run already exists')
    data = source_rows()
    trained = {name: fit(rows) for name, rows in data.items()}
    tasks = tasks_for()
    base, wide, _, records, _, _, cost = public_run(tasks)
    rows = public_rows(tasks, wide, records, load_models())
    chosen = allocations(rows, trained)
    DEST.mkdir(parents=True)
    for name, model in trained.items():
        joblib.dump(model, DEST / f'{name}.joblib', compress=3)
    for name, value in (('sealed_bank.json', tasks), ('base_pools.json', base),
                        ('ast_wide_pools.json', wide),
                        ('frozen_records.json', records),
                        ('public_rows.json', rows),
                        ('allocations.json', chosen)):
        write_json(DEST / name, value)
    write_json(DEST / 'manifest.json', {**manifest(), 'generation_cost': cost,
                                      'source_rows': {k: len(v) for k, v in data.items()}})
    print(json.dumps({'frozen': True, 'tasks': len(tasks),
                      'selection_count': {k: len(v) for k, v in chosen.items()},
                      'generation_cost': cost}, indent=2))


def verify_manifest():
    saved = json.loads((DEST / 'manifest.json').read_text())
    fresh = manifest()
    assert all(saved[k] == v for k, v in fresh.items())
    return saved


def score_rows(tasks, wide, rows):
    results = []
    checked = 0
    for task, row in zip(tasks, rows):
        pool = wide[task['id']]
        assert row['id'] == task['id'] and row['pool_sha256'] == digest(pool)
        labels = [int(bool(evaluate_program(item['program'], task['hidden'][8:])))
                  for item in pool]
        checked += len(labels)
        outcomes = {width: labels[index] for width, index in row['choices'].items()}
        results.append({'id': task['id'], 'seed': task['seed'],
                        'domain': 'shifted' if task['family'] == 'shifted_ast'
                        else 'familiar', 'outcomes': outcomes,
                        'effect': outcomes['200'] - outcomes['100'],
                        'full_reachable': int(any(labels))})
    return results, checked


def summarize(results, rows, chosen, checked):
    policies = {**chosen}
    policies['oracle'] = sorted(select(rows, np.asarray([r['effect']
                                                         for r in results])))
    banks = []
    for seed in SEEDS:
        ids = [i for i, r in enumerate(results) if r['seed'] == seed]
        bank = {'seed': seed}
        for name in NAMES:
            picked = set(policies[name])
            bank[name] = sum(results[i]['outcomes']['200' if i in picked else '100']
                             for i in ids)
            bank[name + '_scores'] = sum(rows[i]['extra_scores'] for i in ids
                                          if i in picked)
            bank[name + '_positive_edits'] = sum(results[i]['effect'] > 0
                                                  for i in ids if i in picked)
            bank[name + '_negative_edits'] = sum(results[i]['effect'] < 0
                                                  for i in ids if i in picked)
            for domain in ('familiar', 'shifted'):
                bank[name + '_' + domain] = sum(
                    results[i]['outcomes']['200' if i in picked else '100']
                    for i in ids if results[i]['domain'] == domain)
        banks.append(bank)
    totals = {k: sum(b[k] for b in banks) for k in banks[0] if k != 'seed'}
    comparisons = {}
    for baseline in ('early', 'scrambled', 'duplicate', 'shifted_priority',
                     'uncertain', 'random'):
        d = [b['later'] - b[baseline] for b in banks]
        comparisons['later_minus_' + baseline] = {
            'gain': sum(d), 'positive_banks': sum(v > 0 for v in d),
            'negative_banks': sum(v < 0 for v in d), 'interval': interval(d),
            'bank_differences': d}
    best_fixed = max(('shifted_priority', 'uncertain', 'random'),
                     key=lambda n: totals[n])
    early = comparisons['later_minus_early']
    fixed = comparisons['later_minus_' + best_fixed]
    growth = (all(c['gain'] >= 5 for c in comparisons.values()) and
              early['interval'][0] > 0 and fixed['interval'][0] > 0 and
              early['positive_banks'] >= 8)
    return {'tasks': len(results), 'candidate_labels_checked': checked,
            'totals': totals, 'comparisons': comparisons,
            'best_fixed': best_fixed, 'improver_growth_gate': growth,
            'total_positive_edits': sum(r['effect'] > 0 for r in results),
            'total_negative_edits': sum(r['effect'] < 0 for r in results),
            'banks': banks}


def score():
    if (DEST / 'results.json').exists():
        raise RuntimeError('already scored')
    verify_manifest()
    tasks = json.loads((DEST / 'sealed_bank.json').read_text())
    wide = json.loads((DEST / 'ast_wide_pools.json').read_text())
    rows = json.loads((DEST / 'public_rows.json').read_text())
    chosen = json.loads((DEST / 'allocations.json').read_text())
    results, checked = score_rows(tasks, wide, rows)
    summary = summarize(results, rows, chosen, checked)
    write_json(DEST / 'results.json', {'manifest_sha256': sha(DEST / 'manifest.json'),
                                      'summary': summary, 'tasks': results})
    print(json.dumps({k: v for k, v in summary.items() if k != 'banks'}, indent=2))


def audit():
    if (DEST / 'audit.json').exists():
        raise RuntimeError('already audited')
    m = verify_manifest()
    tasks = tasks_for()
    assert json.loads(json.dumps(tasks, ensure_ascii=False)) == json.loads(
        (DEST / 'sealed_bank.json').read_text())
    data = source_rows()
    trained = {name: fit(rows) for name, rows in data.items()}
    saved = {name: joblib.load(DEST / f'{name}.joblib') for name in trained}
    base, wide, _, records, _, _, cost = public_run(tasks)
    rows = public_rows(tasks, wide, records, load_models())
    x = np.asarray([r['public_features'] for r in rows], np.float32)
    for name in trained:
        for width in ('100', '200'):
            assert np.array_equal(trained[name][width].predict_proba(x),
                                  saved[name][width].predict_proba(x))
    chosen = allocations(rows, saved)
    for name, value in (('base_pools.json', base), ('ast_wide_pools.json', wide),
                        ('frozen_records.json', records), ('public_rows.json', rows),
                        ('allocations.json', chosen)):
        assert json.loads(json.dumps(value, ensure_ascii=False)) == json.loads(
            (DEST / name).read_text()), name
    stable = ('base_candidates', 'extra_ast_candidates',
              'predicted_output_cells', 'e0_candidate_scores',
              'post_query_candidate_scores')
    assert all(cost[k] == m['generation_cost'][k] for k in stable)
    results, checked = score_rows(tasks, wide, rows)
    summary = summarize(results, rows, chosen, checked)
    result = json.loads((DEST / 'results.json').read_text())
    assert result == {'manifest_sha256': sha(DEST / 'manifest.json'),
                      'summary': summary, 'tasks': results}
    audit = {'passed': True, 'tasks_rebuilt': len(tasks),
             'source_rows_retrained': sum(map(len, data.values())),
             'target_model_predictions_rechecked': len(rows) * 8,
             'predicted_output_cells_rechecked': cost['predicted_output_cells'],
             'target_candidate_labels_rechecked': checked,
             'frozen_selections_rechecked': sum(map(len, chosen.values()))}
    write_json(DEST / 'audit.json', audit)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    {'prepare': prepare, 'score': score, 'audit': audit}[sys.argv[1]]()
