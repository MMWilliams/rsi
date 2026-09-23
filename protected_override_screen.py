"""P2d retry: learn when to deviate, instead of learning all actions.

The depth-heterogeneous action set is the only one to clear P2c with a broken
zero-knowledge rule: "most confident" collapses to 339 because shallow models
are overconfident, while "own region, deepest model" reaches 423 against an
oracle of 475. Its P2d test then failed by only 6, with a selector that had to
predict the correctness of all twelve actions independently.

That is the harder problem. This asks the easier and better-posed one, which is
the protected-admission pattern used elsewhere in this project: keep the default
unless a learned model says a specific alternative is better by more than a
margin, with the margin fitted on training panels only.

If a protected override beats the default on a held-out panel, the space clears
P2d and an improver can be built for it. Development evidence on opened panels.
"""
from __future__ import annotations

import json
from collections import defaultdict

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval
from candidate_reranker_transfer import model_for
from region_specialist_repayment_development import (
    TARGET, REGIONS, load_cache, MODELS as DEEP)

SHALLOW = ROOT / 'analysis/region-depth-models-20260920'
OUT = ROOT / 'analysis/protected-override-screen-20260920.json'
MARGINS = (0.0, 0.02, 0.05, 0.10, 0.15, 0.25, 0.40)


def name_of(region, depth):
    return f'{region}@{depth}'


def load_actions():
    models = {}
    for region in REGIONS:
        models[name_of(region, 100)] = joblib.load(DEEP / f'{region}.joblib')
        models[name_of(region, 25)] = joblib.load(SHALLOW / f'{region}@25.joblib')
    return models


def panel_rows(name, models):
    x, meta = load_cache(name)
    scored = {k: m.predict_proba(x)[:, 1] for k, m in models.items()}
    rows = []
    for task in meta:
        s, c = task['start'], task['count']
        entry = {'seed': task['seed'], 'region': task['region'],
                 'labels': {'e0': task['e0_label']}, 'confidence': {},
                 'stats': task['stats']}
        for k, p in scored.items():
            w = p[s:s + c]
            pick = max(range(c), key=lambda i: (float(w[i]), -i))
            entry['labels'][k] = task['labels'][pick]
            entry['confidence'][k] = float(w[pick])
        rows.append(entry)
    return rows


def feats(row, actions):
    return np.asarray(
        [row['stats']['log_pool'], row['stats']['margin'],
         row['stats']['spread'], row['stats']['distinct']]
        + [float(row['region'] == r) for r in REGIONS]
        + [row['confidence'][a] for a in actions], np.float32)


def totals(rows, picks):
    banks = defaultdict(int)
    for row, a in zip(rows, picks):
        banks[row['seed']] += row['labels'][a]
    return [banks[s] for s in sorted(banks)]


def compare(l, r):
    d = [a - b for a, b in zip(l, r)]
    return {'gain': sum(d), 'positive_banks': sum(x > 0 for x in d),
            'losing_banks': sum(x < 0 for x in d), 'interval': interval(d)}


def main():
    if OUT.exists():
        raise RuntimeError('screen exists')
    models = load_actions()
    actions = sorted(models)
    panels = {n: panel_rows(n, models) for n in TARGET}
    names = list(TARGET)
    train = [r for n in names[:2] for r in panels[n]]
    test = panels[names[2]]

    xtr = np.asarray([feats(r, actions) for r in train], np.float32)
    per_action = {}
    for a in actions:
        y = np.asarray([r['labels'][a] for r in train], np.int8)
        per_action[a] = (model_for(15).fit(xtr, y) if 0 < y.sum() < len(y)
                         else float(y.mean()))

    def predict(rows):
        x = np.asarray([feats(r, actions) for r in rows], np.float32)
        return {a: (np.full(len(rows), m) if isinstance(m, float)
                    else m.predict_proba(x)[:, 1]) for a, m in per_action.items()}

    def override(rows, pred, margin):
        picks = []
        for i, row in enumerate(rows):
            base = name_of(row['region'], 100)
            best = max(actions, key=lambda a: (float(pred[a][i]), a))
            picks.append(best if float(pred[best][i]) - float(pred[base][i])
                         > margin else base)
        return picks

    ptr = predict(train)
    fitted = {}
    for m in MARGINS:
        fitted[m] = sum(totals(train, override(train, ptr, m)))
    best_margin = max(fitted, key=fitted.get)

    pte = predict(test)
    default_picks = [name_of(r['region'], 100) for r in test]
    default = totals(test, default_picks)
    result = {'scope': 'opened development; P2d retry with protected override',
              'train_panels': names[:2], 'test_panel': names[2],
              'margin_grid': list(MARGINS),
              'train_scores_by_margin': {str(k): v for k, v in fitted.items()},
              'selected_margin': best_margin,
              'default_own_region_deep': sum(default),
              'oracle': sum(totals(test, [max(actions, key=lambda a: r['labels'][a])
                                          for r in test])),
              'by_margin': {}}
    for m in MARGINS:
        picks = override(test, pte, m)
        got = totals(test, picks)
        changed = sum(1 for p, d in zip(picks, default_picks) if p != d)
        result['by_margin'][str(m)] = {
            'total': sum(got), 'tasks_overridden': changed,
            'vs_default': compare(got, default)}
    sel = result['by_margin'][str(best_margin)]
    result['selected'] = sel
    result['p2d_passed'] = bool(sel['vs_default']['gain'] > 0
                                and sel['vs_default']['interval'][0] > 0)
    result['limits'] = [
        'Opened panels; development evidence only.',
        'The margin is fitted on the training panels only, never on the test panel.',
        'Oracle uses final labels and is not deployable.']
    write_json(OUT, result)
    print(f"default(own-region-deep)={sum(default)}  oracle={result['oracle']}")
    print(f"selected margin={best_margin} (fitted on train)")
    for m in MARGINS:
        v = result['by_margin'][str(m)]
        c = v['vs_default']
        mark = '  <-- selected' if m == best_margin else ''
        print(f"  margin={m:<5} total={v['total']:4d} overrides={v['tasks_overridden']:4d} "
              f"vs_default={c['gain']:+4d} {c['positive_banks']}w/{c['losing_banks']}l "
              f"{c['interval']}{mark}")
    print('P2d passed:', result['p2d_passed'])


if __name__ == '__main__':
    main()
