"""How often v10's extension rule would fire on a seed's ledger, and what it
would cost: full-set rejections whose interval straddles zero with a mean
gain large enough that a doubled set would clear it. Usage:
extension_triggers.py c1 c2 ... (default: the sealed seeds c1 to c19)."""
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent


def triggers(name):
    s = json.loads((ROOT / 'seeds' / name / 'state.json').read_text())
    live, proof = s['resource']['live_scans'], s['resource']['proof_scans']
    rej = above = trig = extra = 0
    by_area = {}
    for e in s['ledger']:
        if e.get('op') != 'prove' or 'candidate' not in e or e['kept'] or 'extension' in e:
            continue
        c, k = e['candidate'], e['carried']
        if c['worlds'] != k['size']:      # stopped at the half set
            continue
        rej += 1
        lo = c['interval'][0]
        if lo > 0:                        # rejected by the cross-area check
            above += 1
            continue
        d = np.array(c['hits'], float) - np.array(k['hits'], float)
        if d.mean() > 0 and lo > d.mean() * (1 - 2 ** .5):
            trig += 1
            by_area[e['area']] = by_area.get(e['area'], 0) + 1
            extra += 2 * k['size'] * 100 * c['budget']   # carried and candidate on one extension set
    return rej, above, trig, by_area, proof / live, (proof + extra) / live


if __name__ == '__main__':
    names = sys.argv[1:] or [f'c{i}' for i in range(1, 20)]
    for name in names:
        rej, above, trig, by_area, cost, cost_ext = triggers(name)
        print(f'{name}: {rej} full-set rejections, {above} with interval above 0, {trig} would extend {by_area}, '
              f'cost {cost:.2f}x -> {cost_ext:.2f}x')
