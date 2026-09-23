"""Opened same-base I0/I1 edit-effect feedback screen across shifted panels."""
from __future__ import annotations

import json

import joblib
import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_development import fit_method
from cross_family_meta_improver_transfer import interval
from post_query_candidate_development import E0
from wide_post_query_development import MODELS
from joint_survivor_query_development import ACTIONS, panel_rows, model_rows
from shifted_feedback_query_development import score


PANEL_A = ROOT / 'runs/shifted-ast-seed-transfer-20260918'
PANEL_B = ROOT / 'runs/post-query-feedback-transfer-20260918'
PANEL_C = ROOT / 'runs/shifted-feedback-value-transfer-20260918'
OUT = ROOT / 'analysis/incremental-joint-improver-development-20260918.json'


def fit_actions(rows):
    return {name: fit_method(model_rows(rows, name), 'basic_100')
            for name in ACTIONS}


def main():
    if OUT.exists():
        raise RuntimeError('development output exists')
    e0 = joblib.load(E0)
    candidates = {name: joblib.load(MODELS / f'{name}.joblib')
                  for name in ('plain', 'sensor')}
    a, ca = panel_rows(PANEL_A, e0, candidates)
    b, cb = panel_rows(PANEL_B, e0, candidates)
    c, cc = panel_rows(PANEL_C, e0, candidates)
    assert (len(a), len(b), len(c)) == (96, 192, 192)
    rng = np.random.default_rng(21419)
    permutations = {name: rng.permutation(len(b)) for name in ACTIONS}
    scrambled_b = [{**row, 'gain': {name: b[int(permutations[name][i])]
                                    ['gain'][name] for name in ACTIONS}}
                   for i, row in enumerate(b)]
    training = {'i0': a,
                'i1': a + b,
                'i1_scrambled': a + scrambled_b,
                'i1_duplicate': a * 3}
    models = {('prior' if name == 'i0' else name): fit_actions(rows)
              for name, rows in training.items()}
    target = score(c, models)
    target['i0'] = target.pop('prior')
    for name in ('i1', 'i1_scrambled', 'i1_duplicate'):
        target[name]['vs_i0'] = {}
        for policy in ('e0', 'route'):
            diffs = [x[policy] - y[policy]
                     for x, y in zip(target[name]['banks'], target['i0']['banks'])]
            target[name]['vs_i0'][policy] = {
                'gain': sum(diffs), 'positive_banks': sum(x > 0 for x in diffs),
                'losing_banks': sum(x < 0 for x in diffs),
                'interval': interval(diffs)}
    diagnostic = json.loads((ROOT / 'analysis/shifted-feedback-effect-diagnostic-20260918.json').read_text())
    result = {'scope': 'opened development, not fresh transfer',
              'same_base_candidate_models': [str((MODELS / f'{name}.joblib').relative_to(ROOT))
                                             for name in ('plain', 'sensor')],
              'i0_effect_tasks': len(a), 'i1_effect_tasks': len(a) + len(b),
              'candidate_choices_checked': ca + cb + cc,
              'fixed_cheap_e0': diagnostic['totals']['cheap_e0'],
              'fixed_cheap_plain': diagnostic['totals']['cheap_plain'],
              'target': target}
    write_json(OUT, result)
    print(json.dumps({**{k: v for k, v in result.items() if k != 'target'},
                      'target': {name: {k: v for k, v in value.items() if k != 'banks'}
                                 for name, value in target.items()}}, indent=2))


if __name__ == '__main__':
    main()
