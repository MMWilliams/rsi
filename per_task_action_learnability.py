"""Is the per-task residual learnable, or is it noise?

The seven-action per-task space is the first to clear P2c: default regret of +38
and +51 against "use your own region's specialist"
(`DEFAULT-REGRET-2026-09-20.md`). But the cross-region matrix shows the
own-region specialist wins 11 of 12 region cells, so that residual is not
region-level structure. It is per task.

P2c is necessary and not sufficient, exactly as P2b was. A budget only matters if
a policy fitted on held-out banks can capture some of it. This trains a per-task
action selector on one audited panel's public features and tests it on the other,
against the own-region default.

If the selector cannot beat the default, the residual is task-level noise, no
improver can grow on it, and this action space is rejected before any improver
is built for it. Development evidence on opened panels.
"""
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from wide_candidate_reranker_development import features


DEST = ROOT / 'runs/region-acquisition-improver-transfer-20260920'
OUT = ROOT / 'analysis/per-task-action-learnability-20260920.json'
PANELS = ('transfer_b', 'transfer_c')
REGIONS = ('transform_transition', 'ast_transition', 'novel_operator_transition',
           'stack_transition', 'mutation_transition', 'self_edit_transition')
ACTIONS = ('e0',) + REGIONS
WIDTH = 100


def panel_features(name):
    """Public per-task summary plus each action's verified outcome."""
    tasks = json.loads((DEST / f'{name}_bank.json').read_text())
    base = json.loads((DEST / f'{name}_base_pools.json').read_text())
    wide = json.loads((DEST / f'{name}_wide_pools.json').read_text())
    records = json.loads((DEST / f'{name}_records.json').read_text())
    rows = json.loads((DEST / f'audit_rows_{name}.json').read_text())['rows']
    assert len(rows) == len(tasks)

    out = []
    for task, record, row in zip(tasks, records, rows):
        pool = wide.get(task['id'], base[task['id']])
        old = record['orders']['old']
        head = old[:min(WIDTH, len(old))]
        scores = np.asarray(record['old_scores'], float)
        std = max(float(scores.std()), .05)
        top = float(scores[old[0]])
        x = features(task, pool, record, len(head))
        public = np.r_[
            np.asarray([np.log1p(len(pool)) / 8., len(head) / 100.,
                        (top - float(scores[old[1]])) / std if len(old) > 1 else 0.,
                        float(np.mean([(top - scores[i]) / std for i in head])),
                        float(np.std([scores[i] for i in head])) / std],
                       np.float32),
            np.asarray([float(task['family'] == r) for r in REGIONS], np.float32),
            x.mean(axis=0)[:32]]
        out.append({'seed': row['seed'], 'region': row['region'],
                    'features': public.astype(np.float32),
                    'labels': row['labels']})
    return out


def fit_selector(rows):
    """One model per action: probability that action is correct on a task."""
    x = np.asarray([r['features'] for r in rows], np.float32)
    models = {}
    for action in ACTIONS:
        y = np.asarray([r['labels'][action] for r in rows], np.int8)
        models[action] = (model_for(15).fit(x, y) if 0 < y.sum() < len(y)
                          else float(y.mean()))
    return models


def apply_selector(models, rows):
    x = np.asarray([r['features'] for r in rows], np.float32)
    scores = {}
    for action, model in models.items():
        scores[action] = (np.full(len(rows), model) if isinstance(model, float)
                          else model.predict_proba(x)[:, 1])
    picks = []
    for index in range(len(rows)):
        picks.append(max(ACTIONS, key=lambda a: (float(scores[a][index]),
                                                 a == rows[index]['region'], a)))
    return picks


def by_bank(rows, picks):
    banks = defaultdict(int)
    for row, action in zip(rows, picks):
        banks[row['seed']] += row['labels'][action]
    return [banks[s] for s in sorted(banks)]


def main():
    if OUT.exists():
        raise RuntimeError('analysis exists')
    panels = {name: panel_features(name) for name in PANELS}
    result = {
        'scope': 'opened development; learnability screen for the seven-action '
                 'per-task space',
        'question': 'can a selector fitted on one audited panel beat the '
                    'own-region default on the other',
        'directions': {}}

    for train_name, test_name in ((PANELS[0], PANELS[1]), (PANELS[1], PANELS[0])):
        train, test = panels[train_name], panels[test_name]
        models = fit_selector(train)
        learned = by_bank(test, apply_selector(models, test))
        default = by_bank(test, [r['region'] for r in test])
        oracle = by_bank(test, [max(ACTIONS, key=lambda a: r['labels'][a])
                                for r in test])
        diffs = [a - b for a, b in zip(learned, default)]
        result['directions'][f'{train_name}_to_{test_name}'] = {
            'learned': sum(learned), 'own_region_default': sum(default),
            'oracle': sum(oracle),
            'default_regret': sum(oracle) - sum(default),
            'learned_minus_default': {
                'gain': sum(diffs),
                'positive_banks': sum(d > 0 for d in diffs),
                'losing_banks': sum(d < 0 for d in diffs),
                'interval': interval(diffs)},
            'fraction_of_regret_captured':
                (sum(diffs) / (sum(oracle) - sum(default))
                 if sum(oracle) != sum(default) else 0.)}
        value = result['directions'][f'{train_name}_to_{test_name}']
        d = value['learned_minus_default']
        print(f'{train_name} -> {test_name}: learned={value["learned"]} '
              f'default={value["own_region_default"]} oracle={value["oracle"]} '
              f'regret={value["default_regret"]}')
        print(f'   learned - default = {d["gain"]:+d} '
              f'{d["positive_banks"]}w/{d["losing_banks"]}l {d["interval"]}  '
              f'captured {value["fraction_of_regret_captured"]:.0%}')

    gains = [v['learned_minus_default']['gain']
             for v in result['directions'].values()]
    lows = [v['learned_minus_default']['interval'][0]
            for v in result['directions'].values()]
    result['learnable'] = bool(all(g > 0 for g in gains) and all(l > 0 for l in lows))
    result['limits'] = [
        'Opened panels; development evidence only.',
        'Public features are pool and score summaries plus a region indicator '
        'and the mean of the candidate feature block; a richer set might do '
        'better.',
        'Each direction trains on 576 tasks, which is small for a seven-way '
        'per-task decision.',
        'Oracle uses final labels and is not a deployable policy.']
    write_json(OUT, result)
    print('learnable:', result['learnable'])


if __name__ == '__main__':
    main()
