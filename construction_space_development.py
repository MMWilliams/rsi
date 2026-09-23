"""Opened screen of the construction action space for a candidate reranker.

The region-acquisition transfer showed that *selecting* among prebuilt
specialists leaves only +1 to +5 of oracle headroom, while +69 to +79 of ranking
headroom survives every selection. This screen measures the alternative verb.
Under one fixed verified-label budget, a construction chooses which source tasks
to label and how wide a shortlist to label them over. It reports the spread of
realized quality across constructions, which bounds what a construction-choosing
improver could ever be worth.

Development evidence only; no policy is frozen here.
"""
from __future__ import annotations

import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from candidate_reranker_transfer import model_for
from cross_family_meta_improver_transfer import interval
from region_specialist_repayment_development import (
    SOURCE, TARGET, REGIONS, load_cache)


OUT = ROOT / 'analysis/construction-space-development-20260920.json'
MODELS = ROOT / 'analysis/construction-space-models-20260920'
WIDTHS = (25, 50, 100)
COMPOSITIONS = ('uniform', 'top_regions', 'low_margin', 'e0_wrong')
REFERENCE = 'reachable_e0_wrong'
LABEL_BUDGET = 40000
TOP_REGIONS = ('ast_transition', 'transform_transition')
ORDER_SEED = 907500


def source_tasks():
    """Every candidate source task, with the public and verified facts a
    composition may use to select it."""
    tasks = []
    for name in SOURCE:
        x, meta = load_cache(name)
        for task in meta:
            tasks.append({'panel': name, 'x': x, 'start': task['start'],
                          'count': task['count'], 'region': task['region'],
                          'labels': task['labels'], 'e0_label': task['e0_label'],
                          'margin': task['stats']['margin']})
    return tasks


def rows_for(task, width):
    take = min(width, task['count'])
    start = task['start']
    return (task['x'][start:start + take],
            np.asarray(task['labels'][:take], np.int8))


def order_for(composition, tasks, rng):
    """Task priority under one composition. Public unless noted."""
    if composition == 'uniform':
        by_region = {region: [i for i, t in enumerate(tasks)
                              if t['region'] == region] for region in REGIONS}
        for group in by_region.values():
            rng.shuffle(group)
        order = []
        while any(by_region.values()):
            for region in REGIONS:
                if by_region[region]:
                    order.append(by_region[region].pop())
        return order
    if composition == 'top_regions':
        inside = [i for i, t in enumerate(tasks) if t['region'] in TOP_REGIONS]
        outside = [i for i, t in enumerate(tasks)
                   if t['region'] not in TOP_REGIONS]
        rng.shuffle(inside)
        rng.shuffle(outside)
        return inside + outside
    if composition == 'low_margin':
        return sorted(range(len(tasks)), key=lambda i: tasks[i]['margin'])
    if composition == 'e0_wrong':
        # charged: one verified label per screened task
        return sorted(range(len(tasks)),
                      key=lambda i: (tasks[i]['e0_label'], i))
    if composition == REFERENCE:
        # charged: full head labels per screened task, so not cost-matched
        return sorted(range(len(tasks)),
                      key=lambda i: (-(any(tasks[i]['labels'])
                                       and not tasks[i]['e0_label']), i))
    raise ValueError(composition)


def build(composition, width, tasks):
    """Spend the label budget under one construction and fit the reranker."""
    rng = np.random.default_rng(ORDER_SEED)
    order = order_for(composition, tasks, rng)
    xs = []
    ys = []
    used = 0
    screened = 0
    for index in order:
        screened += 1
        x, y = rows_for(tasks[index], width)
        if used + len(y) > LABEL_BUDGET:
            break
        xs.append(x)
        ys.append(y)
        used += len(y)
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    charge = {'labels_spent': int(used), 'tasks_labelled': len(ys),
              'tasks_screened': screened,
              'selection_labels': (screened if composition == 'e0_wrong'
                                   else sum(min(width, tasks[i]['count'])
                                            for i in order[:screened])
                                   if composition == REFERENCE else 0)}
    return model_for(15).fit(x, y), charge


def score(model, width, panels):
    """Zero-query top choice against the frozen E0 choice, per panel."""
    out = {}
    for name in panels:
        x, meta = load_cache(name)
        p = model.predict_proba(x)[:, 1]
        banks = {}
        for task in meta:
            take = min(width, task['count'])
            window = p[task['start']:task['start'] + take]
            pick = task['labels'][max(range(take),
                                      key=lambda i: (float(window[i]), -i))]
            bank = banks.setdefault(task['seed'], [0, 0])
            bank[0] += pick
            bank[1] += task['e0_label']
        diffs = [a - b for a, b in banks.values()]
        out[name] = {'correct': sum(a for a, _ in banks.values()),
                     'e0': sum(b for _, b in banks.values()),
                     'gain': sum(diffs), 'banks': len(diffs),
                     'positive_banks': sum(d > 0 for d in diffs),
                     'losing_banks': sum(d < 0 for d in diffs),
                     'interval': interval(diffs)}
    return out


def main():
    if OUT.exists() or MODELS.exists():
        raise RuntimeError('development exists')
    tasks = source_tasks()
    MODELS.mkdir(parents=True)
    results = {}
    for composition in COMPOSITIONS + (REFERENCE,):
        for width in WIDTHS:
            key = f'{composition}@{width}'
            model, charge = build(composition, width, tasks)
            joblib.dump(model, MODELS / f'{key}.joblib', compress=3)
            results[key] = {'composition': composition, 'width': width,
                            'charge': charge, 'panels': score(model, width, TARGET)}
            total = sum(v['gain'] for v in results[key]['panels'].values())
            print(f'{key:32s} labels={charge["labels_spent"]:6d} '
                  f'tasks={charge["tasks_labelled"]:4d} gain={total:+4d}',
                  flush=True)

    totals = {key: sum(v['gain'] for v in value['panels'].values())
              for key, value in results.items()}
    matched = {k: v for k, v in totals.items()
               if not k.startswith(REFERENCE)}
    best = max(matched, key=matched.get)
    worst = min(matched, key=matched.get)
    summary = {
        'scope': 'opened development only; no frozen policy',
        'question': 'how much does the choice of construction change realized '
                    'reranker quality at one matched verified-label budget',
        'label_budget': LABEL_BUDGET,
        'source_panels': list(SOURCE),
        'target_panels': list(TARGET),
        'constructions': results,
        'total_gain_over_e0': totals,
        'cost_matched_best': {'construction': best, 'gain': matched[best]},
        'cost_matched_worst': {'construction': worst, 'gain': matched[worst]},
        'cost_matched_spread': matched[best] - matched[worst],
        'limits': [
            'Opened panels; all gains are development evidence.',
            'Widths are nested prefixes of one cached top-100 order, so this '
            'varies labelling depth, not candidate coverage.',
            f'{REFERENCE} needs full head labels to select its tasks and is '
            'reported as a cost-unmatched reference, not a competing option.']}
    write_json(OUT, summary)
    print(json.dumps({k: v for k, v in summary.items()
                      if k in ('total_gain_over_e0', 'cost_matched_best',
                               'cost_matched_worst', 'cost_matched_spread')},
                     indent=2))


if __name__ == '__main__':
    main()
