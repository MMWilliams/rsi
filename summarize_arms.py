"""The review-002 arms (required experiments 1 and 3): per run G, total scans,
kept changes and harm; per alternative arm the paired differences against full
and the outcome of the preregistered rules 1 to 4; the committed forecasts and
their Brier score. Rules and forecasts as frozen in EXPERIMENT-seed-confirmation.md
(tag prereg-review002-arms)."""
import json
import math
import statistics

from rsi.common import ROOT, write_json

ARMS = ('full', 'accept-all', 'point', 'matched', 'no-guidance', 'frequency', 'no-invention')
COST = ('accept-all', 'point', 'matched')
TAGS = ('c24', 'c25', 'c26')
AREAS = ('mech', 'drawn7', 'metric777001', 'drawn11', 'drawn13', 'metric555001', 'str7')
UNFAMILIAR = ('mech', 'str7')
FORECASTS = (('full beats accept-all on all three', .4), ('full beats matched on all three', .3),
             ('matched ahead on two or more', .45), ('point ahead on two or more', .4),
             ('accept-all ahead on two or more', .35), ('full beats no-guidance on all three', .95),
             ('full beats frequency on all three', .6), ('invention rule 4 holds', .9))


def load(path):
    return json.loads((ROOT / path).read_text())


def run(arm, tag):
    d = load(f'analysis/seed-check-{arm}_{tag}.json')
    a = d['areas']
    per = {x: math.log(a[x]['carried']['total'] / a[x]['start']['total']) for x in AREAS}
    harm = ROOT / f'analysis/harmful-{arm}_{tag}.json'
    h = json.loads(harm.read_text()) if harm.exists() else None
    return {'G': statistics.mean(per.values()), 'G5': statistics.mean(v for x, v in per.items() if not x.startswith('metric')),
            'per_area': per, 'live_scans': d['resource']['live_scans'], 'proof_scans': d['resource']['proof_scans'],
            'kept': len(d['kept_changes']), 'invented_kept': d['invented']['kept'],
            'unfamiliar': {x: a[x]['carried']['by_pool']['unfamiliar'] for x in UNFAMILIAR},
            'min_pool_ratio': min(v['carried']['by_pool'][p] / s for v in a.values() for p, s in v['start']['by_pool'].items()),
            'harm': {'harmful': h['harmful'], 'kept': h['kept']} if h else None,
            'start': [a[x]['start']['total'] for x in AREAS]}


def main():
    runs = {arm: {t: run(arm, t) for t in TAGS} for arm in ARMS}
    for t in TAGS:   # every arm starts from the same state on a seed, so carried totals compare directly
        starts = {tuple(runs[arm][t].pop('start')) for arm in ARMS}
        assert len(starts) == 1, t
    full = runs['full']
    arms = {}
    for arm in ARMS:
        r = runs[arm]
        g = [r[t]['G'] for t in TAGS]
        harm = [r[t]['harm'] for t in TAGS if r[t]['harm']]
        out = {'runs': r, 'mean_G': statistics.mean(g), 'mean_G5': statistics.mean(r[t]['G5'] for t in TAGS),
               'mean_total_scans': statistics.mean(r[t]['live_scans'] + r[t]['proof_scans'] for t in TAGS),
               'harm': {k: sum(h[k] for h in harm) for k in ('harmful', 'kept')} if harm else None}
        if arm != 'full':
            diff = [r[t]['G'] - full[t]['G'] for t in TAGS]
            ahead, full_all = sum(x > 0 for x in diff), all(x < 0 for x in diff)
            if arm in COST:
                rule = 'rule 1: test wins' if full_all else 'rule 2: withdraw' if ahead >= 2 else 'rule 3: inconclusive'
            else:
                if arm == 'no-invention':   # rule 4 judges invention on the unfamiliar-family pools, not on G
                    full_all = all(full[t]['unfamiliar'][x] > r[t]['unfamiliar'][x] for t in TAGS for x in UNFAMILIAR)
                rule = f'rule 4: {"shown" if full_all else "not shown"}'
            out.update({'G_minus_full': diff, 'G5_minus_full': [r[t]['G5'] - full[t]['G5'] for t in TAGS],
                        'ahead_of_full': ahead, 'full_ahead_all': full_all, 'rule': rule})
        arms[arm] = out
    outcomes = [arms['accept-all']['full_ahead_all'], arms['matched']['full_ahead_all'],
                arms['matched']['ahead_of_full'] >= 2, arms['point']['ahead_of_full'] >= 2,
                arms['accept-all']['ahead_of_full'] >= 2, arms['no-guidance']['full_ahead_all'],
                arms['frequency']['full_ahead_all'], arms['no-invention']['full_ahead_all']]
    forecasts = [{'event': e, 'p': p, 'happened': o, 'squared_error': (p - o) ** 2} for (e, p), o in zip(FORECASTS, outcomes)]
    result = {'tags': TAGS, 'arms': arms, 'forecasts': forecasts,
              'brier': statistics.mean(f['squared_error'] for f in forecasts)}
    write_json(ROOT / 'analysis/review002-arms.json', result)
    for arm, a in arms.items():
        print(f'{arm:13s} G {a["mean_G"]:.3f}  G5 {a["mean_G5"]:.3f}  scans {a["mean_total_scans"] / 1e6:4.0f}M  {a.get("rule", "")}')
    print(f'Brier over {len(forecasts)} forecasts: {result["brier"]:.4f} (always 0.5 scores 0.25)')


if __name__ == '__main__':
    main()
