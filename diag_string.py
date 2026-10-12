"""Where a seed's string area loses tasks: per pool, hit / wrong on the
hidden pairs / unsolved, and for the unsolved whether a program exists in
the carried language's full catalog (a window or budget miss) or nowhere
in the generator's (an inexpressible task). Usage: diag_string.py <name> [seed]"""
import collections
import pathlib
import sys

import numpy as np

from rsi import seed_string as S
from rsi.seed import Seed, make_area

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'd_str2'
    seed_no = int(sys.argv[2]) if len(sys.argv) > 2 else 644101
    seed = Seed(ROOT / 'seeds' / name)
    area = make_area('str7', seed_no)
    fresh = area.held_out(8, salt=4321)
    st = seed.state
    a = seed.area_state('str7', st)
    model = a['model']
    prior_sets = [e['picks'] for e in st['experience'] if e['area'] == 'str7'] if a['prior'] else None
    S.init_string(st['language'], model['labels'] if model else None, prior_sets, st['tiebreak'], 1024)
    s = S._S
    rows, rk = s['rows'], s['rk']
    full_rows = S.rows_from(S.GENERATOR_KEYS)

    def keys_of(prog):
        return frozenset(k for i in prog for k in rk[i].tolist())

    def solvable(catalog, visible, targets):
        comp = S.compatible(catalog, visible)
        return bool(comp) and any(True for _ in S.programs([o for _, o in comp], targets, [10 ** 6]))

    tally = collections.Counter()
    for w in fresh:
        pool = w['pool']
        evidence = np.zeros(len(s['keys']))
        window = terms = None
        for task in w['tasks']:
            visible, hidden = task['visible'], task['hidden']
            targets = [o for _, o in visible]
            fresh_terms = S.key_terms(s, evidence)
            if terms is None or not np.array_equal(fresh_terms, terms):
                terms = fresh_terms
                window = np.lexsort((s['tie'], -(s['incidence'] @ terms)))[:1024]
            comp = S.compatible(rows, visible, window)
            found, _ = S.search(comp, targets, 1024, keys_of) if comp else (None, True)
            if found is None:
                where = ('in language' if solvable(rows, visible, targets)
                         else 'in generator' if solvable(full_rows, visible, targets) else 'nowhere')
                tally[pool, 'unsolved', where] += 1
                continue
            for k in keys_of(found):
                evidence[k] += 1.
            prog = [rows[i] for i in found]
            hit = all(S.run_program(prog, inp) == out for inp, out in hidden)
            tally[pool, 'hit' if hit else 'wrong', ''] += 1
    for pool in area.pools:
        print(pool, {f'{k[1]} {k[2]}'.strip(): v for k, v in sorted(tally.items()) if k[0] == pool})
    print('total', {k: sum(v for kk, v in tally.items() if kk[1] == k) for k in ('hit', 'wrong', 'unsolved')})


if __name__ == '__main__':
    main()
