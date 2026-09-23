"""Opened effect/confusion decomposition of specialist applicability transfer."""
from __future__ import annotations

import json
from collections import defaultdict

from rsi.common import ROOT, write_json
from cross_family_meta_improver_transfer import interval


RUN = ROOT / 'runs/specialist-applicability-transfer-20260918'
OUT = ROOT / 'analysis/applicability-failure-diagnostic-20260918.json'


def main():
    if OUT.exists():
        raise RuntimeError('diagnostic exists')
    records = json.loads((RUN / 'frozen_records.json').read_text())
    results = json.loads((RUN / 'results.json').read_text())['tasks']
    allocations = json.loads((RUN / 'frozen_allocations.json').read_text())
    rows = []
    for rec, result in zip(records, results):
        assert rec['id'] == result['id']
        queried = rec['id'] in allocations[str(rec['seed'])]
        effect = result['one']['specialist'] - result['one']['e0']
        choices = rec['router_choices']
        rows.append({'id': rec['id'], 'seed': rec['seed'],
                     'domain': result['domain'], 'queried': queried,
                     'effect': effect,
                     'predicted_effect': rec['router_forecasts']['predicted_effect'],
                     'conservative_accept': choices['effect_conservative'] ==
                                            choices['specialist'] and
                                            rec['router_forecasts']['predicted_effect'] > .15,
                     'zero_accept': rec['router_forecasts']['predicted_effect'] > 0.})
    domains = {}
    for domain in ('familiar', 'shifted'):
        subset = [r for r in rows if r['domain'] == domain]
        entry = {'tasks': len(subset)}
        for label, group in (('all', subset),
                             ('queried', [r for r in subset if r['queried']])):
            entry[label] = {'tasks': len(group),
                'positive_effect': sum(r['effect'] > 0 for r in group),
                'negative_effect': sum(r['effect'] < 0 for r in group),
                'effect_mse': sum((r['predicted_effect'] - r['effect'])**2
                                  for r in group) / max(1, len(group))}
            for rule in ('conservative', 'zero'):
                accepted = [r for r in group if r[rule + '_accept']]
                entry[label][rule] = {
                    'accepted': len(accepted),
                    'positive_accepted': sum(r['effect'] > 0 for r in accepted),
                    'negative_accepted': sum(r['effect'] < 0 for r in accepted),
                    'realized_gain': sum(r['effect'] for r in accepted),
                    'missed_positive': sum(r['effect'] > 0 and
                                           not r[rule + '_accept'] for r in group)}
        domains[domain] = entry
    banks = []
    for seed in sorted({r['seed'] for r in rows}):
        group = [r for r in rows if r['seed'] == seed and r['queried']]
        banks.append({'seed': seed,
                      'oracle_action_gain': sum(max(0, r['effect']) for r in group),
                      'always_gain': sum(r['effect'] for r in group),
                      'conservative_gain': sum(r['effect'] for r in group
                                               if r['conservative_accept']),
                      'zero_gain': sum(r['effect'] for r in group
                                       if r['zero_accept'])})
    totals = {name: sum(b[name] for b in banks) for name in banks[0]
              if name != 'seed'}
    zero_vs_always = [b['zero_gain'] - b['always_gain'] for b in banks]
    report = {'scope': 'opened diagnostic; oracle action uses final labels',
              'domains': domains, 'totals': totals,
              'zero_vs_always': {'gain': sum(zero_vs_always),
                  'positive_banks': sum(x > 0 for x in zero_vs_always),
                  'losing_banks': sum(x < 0 for x in zero_vs_always),
                  'interval': interval(zero_vs_always)},
              'banks': banks}
    write_json(OUT, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'banks'}, indent=2))


if __name__ == '__main__':
    main()
