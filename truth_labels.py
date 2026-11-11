"""What each tested candidate really did (review 002, item 5).

The offline re-judging (rejudge_proofs.py) could only compare a smaller test
with the full test's verdict, because a rejected candidate left no state to
score. The recorded runs (run_record.py: the full arm with both states of every
proof saved) do, so here every candidate, kept or not, and the state it was
tested against are scored on a truth set four times the size the test used and
on a salt nothing else has used: 192 worlds of the candidate's own area and,
where the proof ran a cross-area check, 96 worlds of each area it checked.

A candidate is called harmful when the paired 95% bootstrap interval (worlds
resampled within pools) of its gain on the truth set is below zero, beneficial
when it is above zero, and unresolved otherwise. Reported: for the whole rule
as it ran (kept), for the own-area interval test at the full, half and quarter
set, and for a point rule on the half set, how many candidates it passes and
refuses in each class; and for the cross-area check at each tolerance, how many
of the candidates it passes truly lowered an area it checked. The four
forecasts committed with the design are scored here.

  truth_labels.py check   three proofs per seed re-run from their recorded states against the ledger
  truth_labels.py score   scores, resumes from the saved hits
  truth_labels.py         summarises the saved hits; needs only numpy
"""
import json
import sys
import warnings

import numpy as np

from rejudge_proofs import accepted
from rsi.common import ROOT, write_json
from summarize_arms import TAGS

SALT, OWN, OTHER, BUDGET, DRAWS = 30003, 192, 96, 1024, 10_000
TOLERANCES = (0., .02, .05, .1)
FORECASTS = (('fewer than one in ten kept candidates harmful', .8), ('more refused candidates beneficial than harmful', .45),
             ('point passes at least three times the harmful candidates the rule keeps', .6),
             ('cross-area check passes a truly lowering candidate at 10% and none at 2%', .35))
HITS = ROOT / 'analysis/truth-hits.json'
OUT = ROOT / 'analysis/review002-truth.json'


def proofs_of(state):
    return [e for e in state['ledger'] if e['op'] == 'prove']


def recorded(seed, k, side):
    """The state a proof compared, as the seed would have run it then."""
    rec = json.loads((seed.path / 'candidates' / f'{k}.json').read_text())
    state = seed.candidate()
    state.update(language=rec[side]['language'], areas=rec[side]['areas'], inventions=rec[side]['inventions'],
                 experience=state['experience'][:rec['experience_len']])
    return rec, state


def check():
    """A recorded state must give back the hits its proof wrote in the ledger."""
    from rsi.seed import Seed, make_area
    warnings.filterwarnings('ignore')
    for tag in TAGS:
        seed = Seed(ROOT / 'seeds' / f'record_{tag}')
        proofs = proofs_of(seed.state)
        full = [e['candidate']['worlds'] == e['carried']['size'] for e in proofs]
        kinds = ([e['kept'] for e in proofs], [f and not e['kept'] for f, e in zip(full, proofs)], [not f for f in full])
        for k in sorted({kind.index(True) for kind in kinds if True in kind}):   # the first kept, refused on the full set, and stopped
            e = proofs[k]
            area = make_area(seed.state['areas'][e['area']]['spec'], seed.state['seed'])
            held = area.held_out(e['carried']['size'] // len(area.pools), salt=e['salt'])
            for side in ('carried', 'candidate'):
                worlds = held if side == 'carried' or full[k] else held[::2]   # a stopped proof ran the even half
                rec, state = recorded(seed, k, side)
                assert (rec['area'], rec['change']) == (e['area'], e['change'])
                hits = [r['hits'] for r in seed.run(worlds, BUDGET, e['area'], state=state)]
                assert hits == e[side]['hits'], f'{tag} proof {k} {side}: the recorded state does not replay'
            print(f'{tag} proof {k} ({e["area"]}, {"kept" if e["kept"] else "full set" if full[k] else "stopped"}) replays', flush=True)


def score():
    from rsi.seed import Seed, make_area
    warnings.filterwarnings('ignore')
    out = json.loads(HITS.read_text()) if HITS.exists() else {'salt': SALT, 'own': OWN, 'other': OTHER, 'pools': {}, 'hits': {}}
    assert (out['salt'], out['own'], out['other']) == (SALT, OWN, OTHER)
    for tag in TAGS:
        seed = Seed(ROOT / 'seeds' / f'record_{tag}')
        proofs = proofs_of(seed.state)
        used = {e['salt'] for e in proofs} | {e['extension']['salt'] for e in proofs if 'extension' in e} | {999, 20001}
        assert SALT not in used
        sets = {}
        for k, e in enumerate(proofs):
            for name, size in [(e['area'], OWN)] + [(n, OTHER) for n in e.get('elsewhere', {})]:
                if (name, size) not in sets:
                    area = make_area(seed.state['areas'][name]['spec'], seed.state['seed'])
                    sets[name, size] = area.held_out(size // len(area.pools), salt=SALT)
                    out['pools'][f'{tag}/{name}/{size}'] = [w['pool'] for w in sets[name, size]]
                for side in ('carried', 'candidate'):
                    rec, state = recorded(seed, k, side)
                    lived = sum(x['area'] == name for x in state['experience'])
                    # a carried state scores the same in an area until its version or that area's experience changes
                    key = f'{tag}/{name}/{size}/' + (f'v{rec[side]["version"]}e{lived}' if side == 'carried' else f'c{k}')
                    if key not in out['hits']:
                        out['hits'][key] = [r['hits'] for r in seed.run(sets[name, size], BUDGET, name, state=state)]
                        write_json(HITS, out)
                        print(key, sum(out['hits'][key]), flush=True)
                    out.setdefault('carried_key', {})[f'{tag}/{name}/{size}/c{k}'] = f'{tag}/{name}/{size}/v{rec["carried"]["version"]}e{lived}'
        write_json(HITS, out)


def summarize():
    d = json.loads(HITS.read_text())
    rng = np.random.default_rng(SALT)
    index = {}

    def effect(key):
        """Truth-set gain of a candidate over its carried state: per world, relative, and its interval and class."""
        tag, name, size, _ = key.split('/')
        pools = np.array(d['pools'][f'{tag}/{name}/{size}'])
        if (tag, name, size) not in index:
            index[tag, name, size] = np.concatenate([rng.choice(np.flatnonzero(pools == p), size=(DRAWS, int((pools == p).sum())))
                                                     for p in sorted(set(pools))], axis=1)
        cand, base = np.array(d['hits'][key], float), np.array(d['hits'][d['carried_key'][key]], float)
        diff = cand - base
        low, high = np.percentile(diff[index[tag, name, size]].mean(axis=1), [2.5, 97.5])
        return {'gain': float(diff.mean()), 'relative': float(cand.sum() / base.sum() - 1), 'interval': [float(low), float(high)],
                'class': 'harmful' if high < 0 else 'beneficial' if low > 0 else 'unresolved'}

    rows = []
    for tag in TAGS:
        state = json.loads((ROOT / 'seeds' / f'record_{tag}' / 'state.json').read_text())
        for k, e in enumerate(proofs_of(state)):
            base, cand = np.array(e['carried']['hits'], float), np.array(e['candidate']['hits'], float)
            half = cand - base[::2] if len(cand) < len(base) else (cand - base)[::2]   # a stopped proof ran the even half
            row = {'tag': tag, 'proof': k, 'area': e['area'], 'change': e['change'], 'kept': e['kept'],
                   'own': effect(f'{tag}/{e["area"]}/{OWN}/c{k}'),
                   # kept: the whole rule as it ran. full: its own-area test as it ran, early stop and extension
                   # set included, whatever the cross-area check then said. The smaller ones: the plain interval rule.
                   'passes': {'kept': e['kept'], 'full': e['kept'] or 'elsewhere' in e, 'half': accepted(half, e['salt']),
                              'quarter': accepted(half[::2], e['salt']), 'point': bool(half.mean() > 0)}}
            if 'elsewhere' in e:
                row['elsewhere'] = {n: dict(effect(f'{tag}/{n}/{OTHER}/c{k}'), check=[v['carried'], v['candidate']])
                                    for n, v in e['elsewhere'].items()}
            rows.append(row)

    def classes(group):
        out = {c: sum(r['own']['class'] == c for r in group) for c in ('harmful', 'beneficial', 'unresolved')}
        out.update(n=len(group), mean_gain=float(np.mean([r['own']['gain'] for r in group])) if group else None)
        return out

    rules = {rule: {'passed': classes([r for r in rows if r['passes'][rule]]), 'refused': classes([r for r in rows if not r['passes'][rule]])}
             for rule in ('kept', 'full', 'half', 'quarter', 'point')}
    checked = [r for r in rows if 'elsewhere' in r]
    tolerance = {}
    for t in TOLERANCES:
        passed = [all(v['check'][1] >= v['check'][0] * (1 - t) for v in r['elsewhere'].values()) for r in checked]

        def harm(group):
            return {'n': len(group), 'lowered_an_area': sum(any(v['class'] == 'harmful' for v in r['elsewhere'].values()) for r in group),
                    'worst_true_change': [min(v['relative'] for v in r['elsewhere'].values()) for r in group]}
        tolerance[str(t)] = {'passed': harm([r for r, p in zip(checked, passed) if p]), 'refused': harm([r for r, p in zip(checked, passed) if not p])}
    kept, refused, point = rules['kept']['passed'], rules['kept']['refused'], rules['point']['passed']
    happened = [kept['harmful'] < .1 * kept['n'], refused['beneficial'] > refused['harmful'],
                point['harmful'] >= max(3, 3 * kept['harmful']),
                tolerance['0.1']['passed']['lowered_an_area'] >= 1 and tolerance['0.02']['passed']['lowered_an_area'] == 0]
    forecasts = [{'event': e, 'p': p, 'happened': h, 'squared_error': (p - h) ** 2} for (e, p), h in zip(FORECASTS, happened)]
    write_json(OUT, {'salt': SALT, 'own': OWN, 'other': OTHER, 'draws': DRAWS, 'tags': TAGS, 'candidates': len(rows),
                     'all': classes(rows), 'rules': rules, 'reached_cross_area_check': len(checked), 'tolerance': tolerance,
                     'forecasts': forecasts, 'brier': float(np.mean([f['squared_error'] for f in forecasts])), 'rows': rows})
    print('all', classes(rows))
    for rule, r in rules.items():
        print(f'{rule:8s} passed {r["passed"]}\n         refused {r["refused"]}')
    for t, r in tolerance.items():
        print(f'tolerance {t}: passed {r["passed"]["n"]} ({r["passed"]["lowered_an_area"]} lowered an area), '
              f'refused {r["refused"]["n"]} ({r["refused"]["lowered_an_area"]} lowered an area)')


if __name__ == '__main__':
    {'check': check, 'score': score}.get(sys.argv[1] if sys.argv[1:] else '', summarize)()
