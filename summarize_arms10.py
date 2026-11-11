"""The review-002 arms on ten seeds, with intervals over seeds (the follow-up
frozen in EXPERIMENT-seed-confirmation.md, tag prereg-review002-v2).

Per arm: G(arm) - G(full) on each seed, its mean, the paired 95% bootstrap
interval over seeds and the verdict (ahead or behind when the interval excludes
zero, else tie). Primary: the seven seeds no arm had run on. Secondary: all ten.
Time-matched had run on no seed, so its primary set is all ten; a seed on which
its seconds differ from the reference arm's by more than a tenth is flagged.
Invention is judged on the unfamiliar-family pools, as in rule 4."""
import json
import statistics

import numpy as np

from rsi.common import ROOT, write_json
from summarize_arms import ARMS, TAGS, UNFAMILIAR, run

NEW = ('c22', 'c23', 'c27', 'c28', 'c29', 'c30', 'c31')
ALTERNATIVES = ARMS[1:] + ('time-matched',)
DRAWS = 10_000
FORECASTS = (('matched ahead of full', .55), ('time-matched ahead of full', .3), ('time-matched behind full', .1),
             ('accept-all tie', .7), ('point tie', .7), ('no-guidance behind', .97), ('frequency behind', .85),
             ('no-invention behind in G', .8), ('no-invention behind on both unfamiliar pools', .95))


def paired(diff, rng):
    d = np.array(diff)
    low, high = np.percentile(d[rng.integers(len(d), size=(DRAWS, len(d)))].mean(axis=1), [2.5, 97.5])
    return {'per_seed': [float(x) for x in d], 'mean': float(d.mean()), 'interval': [float(low), float(high)],
            'ahead_on': int((d > 0).sum()), 'verdict': 'ahead' if low > 0 else 'behind' if high < 0 else 'tie'}


def main():
    rng = np.random.default_rng(20261111)
    runs = {arm: {t: run(arm, t) for t in TAGS + NEW} for arm in ('full',) + ALTERNATIVES}
    out = {'new': NEW, 'all': TAGS + NEW, 'arms': {}}
    for arm in ALTERNATIVES:
        a = {'mean_G': statistics.mean(runs[arm][t]['G'] for t in TAGS + NEW),
             'mean_total_scans': statistics.mean(runs[arm][t]['live_scans'] + runs[arm][t]['proof_scans'] for t in TAGS + NEW)}
        for label, tags in (('new', NEW), ('all', TAGS + NEW)):
            a[label] = paired([runs[arm][t]['G'] - runs['full'][t]['G'] for t in tags], rng)
        harm = [runs[arm][t]['harm'] for t in TAGS + NEW if runs[arm][t]['harm']]
        if harm:
            a['harm'] = {k: sum(h[k] for h in harm) for k in ('harmful', 'kept')}
        out['arms'][arm] = a
    harm = [runs['full'][t]['harm'] for t in TAGS + NEW]
    out['full'] = {'mean_G': statistics.mean(runs['full'][t]['G'] for t in TAGS + NEW), 'per_seed': [runs['full'][t]['G'] for t in TAGS + NEW],
                   'harm': {k: sum(h[k] for h in harm) for k in ('harmful', 'kept')}}
    out['unfamiliar'] = {x: paired([runs['no-invention'][t]['unfamiliar'][x] - runs['full'][t]['unfamiliar'][x] for t in NEW], rng) for x in UNFAMILIAR}
    v = {arm: out['arms'][arm]['all' if arm == 'time-matched' else 'new']['verdict'] for arm in ALTERNATIVES}
    happened = [v['matched'] == 'ahead', v['time-matched'] == 'ahead', v['time-matched'] == 'behind', v['accept-all'] == 'tie', v['point'] == 'tie',
                v['no-guidance'] == 'behind', v['frequency'] == 'behind', v['no-invention'] == 'behind',
                all(out['unfamiliar'][x]['verdict'] == 'behind' for x in UNFAMILIAR)]
    out['forecasts'] = [{'event': e, 'p': p, 'happened': h, 'squared_error': (p - h) ** 2} for (e, p), h in zip(FORECASTS, happened)]
    out['brier'] = statistics.mean(f['squared_error'] for f in out['forecasts'])
    clocks = {t: json.loads((ROOT / 'seeds' / f'time-matched_{t}' / 'state.json').read_text()) for t in TAGS + NEW}
    out['clock'] = {t: {'seconds': sum(s['clock']), 'reference': s['reference'][-1], 'lives': s['plan']} for t, s in clocks.items()}
    out['clock_flagged'] = [t for t, c in out['clock'].items() if abs(c['seconds'] / c['reference'] - 1) > .1]
    write_json(ROOT / 'analysis/review002-arms10.json', out)
    for arm, a in out['arms'].items():
        print(f'{arm:13s} G {a["mean_G"]:.3f}  new {a["new"]["mean"]:+.3f} [{a["new"]["interval"][0]:+.3f}, {a["new"]["interval"][1]:+.3f}] {a["new"]["verdict"]:6s} '
              f'all {a["all"]["mean"]:+.3f} [{a["all"]["interval"][0]:+.3f}, {a["all"]["interval"][1]:+.3f}] {a["all"]["verdict"]}')
    print(f'Brier over {len(FORECASTS)} forecasts: {out["brier"]:.4f}')


if __name__ == '__main__':
    main()
