"""Is the optimal action stable across banks, or does it need context?

Four action spaces have now been measured and all four showed the same shape: a
large total value, captured almost entirely by one choice any competent policy
makes, leaving a marginal decision of +1 to +5 inside bank noise. That pattern
has a testable cause. If the optimal action is the *same* on every bank, then no
amount of accumulated experience can beat a one-observation policy, and improver
growth is unmeasurable in this environment by construction.

This module quantifies that directly from an audited run's per-bank rows:

- `fixed_regret`: what the single best fixed action loses against per-bank
  hindsight. This is the entire budget available to any contextual improver.
- `argmax_stability`: how often each bank's own optimum equals the global
  optimum.
- `one_shot_sufficiency`: how well a policy fitted on one bank does on the
  remaining banks, against a policy fitted on all but one.

Reads only `audit_rows_*.json`, which the independent auditor regenerated from
seeds, so this inherits the audit's provenance.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval


DEST = ROOT / 'runs/region-acquisition-improver-transfer-20260920'
OUT = ROOT / 'analysis/action-space-stationarity-20260920.json'
REGIONS = ('transform_transition', 'ast_transition', 'novel_operator_transition',
           'stack_transition', 'mutation_transition', 'self_edit_transition')
BUDGET = 3
BANKS = ('transfer_b', 'transfer_c')


def load_rows(name):
    return json.loads((DEST / f'audit_rows_{name}.json').read_text())['rows']


def per_bank_totals(rows, installed):
    banks = defaultdict(int)
    for row in rows:
        key = row['region'] if row['region'] in installed else 'e0'
        banks[row['seed']] += row['labels'][key]
    return banks


def per_bank_region_gain(rows):
    """gain[seed][region] = specialist correct - E0 correct, inside that region."""
    gain = defaultdict(lambda: dict.fromkeys(REGIONS, 0))
    for row in rows:
        if row['region'] in REGIONS:
            gain[row['seed']][row['region']] += (row['labels'][row['region']]
                                                 - row['labels']['e0'])
    return {seed: dict(value) for seed, value in gain.items()}


def best_set(gain, seeds):
    """The budget-B region set maximising summed gain over the given banks."""
    return max(combinations(REGIONS, BUDGET),
               key=lambda combo: sum(gain[s][r] for s in seeds for r in combo))


def analyse(name):
    rows = load_rows(name)
    gain = per_bank_region_gain(rows)
    seeds = sorted(gain)

    global_best = best_set(gain, seeds)
    global_value = sum(gain[s][r] for s in seeds for r in global_best)

    hindsight = {s: best_set(gain, [s]) for s in seeds}
    hindsight_value = sum(gain[s][r] for s in seeds for r in hindsight[s])

    # What one bank of experience buys, against all-but-one.
    one_shot = []
    leave_one = []
    for held in seeds:
        rest = [s for s in seeds if s != held]
        pick_one = best_set(gain, [rest[0]])
        pick_many = best_set(gain, rest)
        one_shot.append(sum(gain[held][r] for r in pick_one))
        leave_one.append(sum(gain[held][r] for r in pick_many))

    counts = Counter(hindsight.values())
    per_region_rank = {region: float(np.mean(
        [sorted(REGIONS, key=lambda r: -gain[s][r]).index(region)
         for s in seeds])) for region in REGIONS}

    diffs = [a - b for a, b in zip(leave_one, one_shot)]
    return {
        'banks': len(seeds),
        'global_best_set': list(global_best),
        'global_best_value': global_value,
        'per_bank_hindsight_value': hindsight_value,
        'fixed_regret': hindsight_value - global_value,
        'argmax_stability': {
            'distinct_optimal_sets': len(counts),
            'banks_matching_global_optimum': counts[global_best],
            'most_common': [list(k) for k, _ in counts.most_common(3)],
            'most_common_counts': [v for _, v in counts.most_common(3)]},
        'mean_region_rank': per_region_rank,
        'one_shot_sufficiency': {
            'one_bank_of_experience': sum(one_shot),
            'eleven_banks_of_experience': sum(leave_one),
            'gain_from_more_experience': sum(diffs),
            'interval': interval(diffs)},
        'per_bank_region_gain': {str(s): gain[s] for s in seeds}}


def main():
    result = {
        'scope': 'stationarity of the region-purchase action space, from '
                 'audited per-bank rows',
        'question': 'can any contextual or experience-accumulating improver '
                    'beat a one-observation policy in this environment',
        'budget': BUDGET,
        'banks': {name: analyse(name) for name in BANKS},
        'limits': [
            'Hindsight sets use final labels and are not deployable policies.',
            'This bounds the region-purchase space only; a construction space '
            'with different actions needs its own measurement.',
            'Leave-one-out uses the first remaining seed as the one-bank '
            'sample, so the one-shot arm is a single draw, not an average.']}
    for name, value in result['banks'].items():
        print(f'{name}: fixed_regret={value["fixed_regret"]:+d} '
              f'distinct_optima={value["argmax_stability"]["distinct_optimal_sets"]}'
              f'/{value["banks"]} '
              f'more_experience={value["one_shot_sufficiency"]["gain_from_more_experience"]:+d} '
              f'{value["one_shot_sufficiency"]["interval"]}')
    write_json(OUT, result)
    print(json.dumps({name: {k: v for k, v in value.items()
                             if k != 'per_bank_region_gain'}
                      for name, value in result['banks'].items()}, indent=2))


if __name__ == '__main__':
    main()
