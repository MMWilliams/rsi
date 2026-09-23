"""Opened-task decomposition of feedback value, candidate choice and allocation."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json
from shifted_feedback_value_transfer import ACTIONS, route_action


RUN = ROOT / 'runs/shifted-feedback-value-transfer-20260918'
OUT = ROOT / 'analysis/shifted-feedback-effect-diagnostic-20260918.json'


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    result = json.loads((RUN / 'results.json').read_text())
    outcome = result['tasks']
    allocations = json.loads((RUN / 'frozen_allocations.json').read_text())
    forecasts = json.loads((RUN / 'frozen_forecasts.json').read_text())
    by_seed = {}
    for row in outcome:
        by_seed.setdefault(str(row['seed']), []).append(row)
    banks = []
    action_counts = {'e0': 0, 'plain': 0, 'sensor': 0}
    for seed, group in sorted(by_seed.items()):
        assert len(group) == 8
        cheap = set(allocations[seed]['cheap'])
        shifted = set(allocations[seed]['shifted100'])
        route = set(allocations[seed]['route_shifted100'])
        def utility(ids, action):
            return sum(r['one'][action] if r['id'] in ids else r['zero']
                       for r in group)
        entry = {'seed': int(seed), 'cheap_e0': utility(cheap, 'e0'),
                 'cheap_plain': utility(cheap, 'plain'),
                 'cheap_sensor': utility(cheap, 'sensor'),
                 'shifted_e0': utility(shifted, 'e0'),
                 'route_locations_e0': utility(route, 'e0'),
                 'cheap_oracle_action': sum(max(r['one'].values())
                    if r['id'] in cheap else r['zero'] for r in group),
                 'route_oracle_action': sum(max(r['one'].values())
                    if r['id'] in route else r['zero'] for r in group)}
        entry['route_learned'] = sum(
            r['one'][route_action('route_shifted100', r['id'], forecasts)]
            if r['id'] in route else r['zero'] for r in group)
        for row in group:
            if row['id'] in route:
                action_counts[route_action('route_shifted100', row['id'], forecasts)] += 1
        banks.append(entry)
    fields = [k for k in banks[0] if k != 'seed']
    totals = {field: sum(b[field] for b in banks) for field in fields}
    gain = {}
    for model in ('prior', 'pooled12', 'shifted100', 'scrambled', 'duplicate'):
        predictions = forecasts[model]['e0']
        gain[model] = {'mse_e0_gain': sum(
            (predictions[r['id']] - (r['one']['e0'] - r['zero'])) ** 2
            for r in outcome) / len(outcome)}
    report = {'scope': 'opened diagnostic; oracle action rows use final labels',
              'tasks': len(outcome), 'calls_each_budgeted_policy': 96,
              'totals': totals, 'route_shifted_action_counts': action_counts,
              'forecast_error': gain, 'banks': banks}
    write_json(OUT, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'banks'}, indent=2))


if __name__ == '__main__':
    main()
