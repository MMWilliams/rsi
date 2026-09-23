"""Opened threshold screen for public-only and paired-effect specialist routing."""
from __future__ import annotations

import json

from rsi.common import ROOT, write_json


SOURCE = ROOT / 'analysis/specialist-applicability-development-v2-20260918.json'
OUT = ROOT / 'analysis/applicability-threshold-screen-20260918.json'


def main():
    if OUT.exists():
        raise RuntimeError('screen exists')
    rows = json.loads(SOURCE.read_text())['target_rows']
    rules = [('effect', value, None) for value in
             (-.05, 0., .05, .1, .15, .2, .25, .3)]
    rules += [('visible', value, None) for value in
              (.5, .6, .7, .8, .9, .95)]
    rules += [('both', a, b) for a in (0., .05, .1, .15, .2)
              for b in (.5, .7, .9)]
    output = []
    for kind, a, b in rules:
        def accept(row):
            effect = row['predicted_effect'] > a
            visible = row['visible_probability'] > a if b is None else \
                row['visible_probability'] > b
            return (effect if kind == 'effect' else visible if kind == 'visible'
                    else effect and visible)
        result = {'kind': kind, 'effect_threshold': a if kind != 'visible' else None,
                  'visible_threshold': a if kind == 'visible' else b}
        for domain in ('familiar', 'shifted'):
            subset = [r for r in rows if r['domain'] == domain]
            selected = [r for r in subset if accept(r)]
            result[domain] = {'selected': len(selected),
                              'gain_vs_e0': sum(r['specialist'] - r['e0']
                                                for r in selected)}
        output.append(result)
    write_json(OUT, {'scope': 'opened threshold screen only', 'rules': output})
    shortlist = sorted(output, key=lambda r: (r['familiar']['gain_vs_e0'] >= 0,
        r['shifted']['gain_vs_e0']), reverse=True)[:12]
    print(json.dumps({'best_nonharmful_or_near': shortlist}, indent=2))


if __name__ == '__main__':
    main()
