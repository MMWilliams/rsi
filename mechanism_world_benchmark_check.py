"""The training-pool benchmark against the old one: atoms per family per world
and per-family split-half ceilings, for each seed."""
import json, sys
import numpy as np
from rsi.common import ROOT
from rsi.mechanism_worlds import Harness

OLD = ROOT / 'analysis/mechanism-world-benchmark-20261005.json'
NEW = ROOT / 'analysis/mechanism-world-benchmark-trained-20261010.json'


def rate(half):
    present, found = np.array(half['present']), np.array(half['found'])
    return np.where(present >= 10, found / np.maximum(present, 1), np.nan)


def main():
    h = Harness()
    fams = sorted(h.by_family); fam = np.array([fams.index(k.split(':')[0]) for k in h.key_names])
    old = json.loads(OLD.read_text()); new = json.loads(NEW.read_text())
    for seed in new:
        o, n = old[seed], new[seed]['halves']
        po = np.array(o[0]['present']) + np.array(o[1]['present'])
        pn = np.array(n[0]['present']) + np.array(n[1]['present'])
        print(f'seed {seed}: {len(new[seed]["pool"])} training triples')
        print('  family     atoms/world old  new | ceiling old  new  (n atoms)')
        for f, name in enumerate(fams):
            sel = fam == f
            line = f'  {name:10s} {po[sel].sum() / 1600:6.2f} {pn[sel].sum() / 1600:6.2f} |'
            for b in (o, n):
                a, c = rate(b[0]), rate(b[1])
                ok = sel & ~np.isnan(a) & ~np.isnan(c)
                line += f' {np.corrcoef(a[ok], c[ok])[0, 1]:6.2f}' if ok.sum() >= 6 else '    nan'
                line += f' ({int(ok.sum()):3d})'
            print(line)
        a, c = rate(n[0]), rate(n[1]); ok = ~np.isnan(a) & ~np.isnan(c)
        print(f'  overall ceiling new {np.corrcoef(a[ok], c[ok])[0, 1]:.3f} on {int(ok.sum())} atoms')


if __name__ == '__main__':
    sys.exit(main())
